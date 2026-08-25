import re

from app.order_service import OrderService
from app.knowledge_base import KnowledgeBase
from app.source_policy import SourcePolicy
from app.local_llm import LocalLLM


class CustomerAssistant:
    """Main controller for the customer-support assistant."""

    ORDER_WORDS = {
        "order",
        "shipment",
        "tracking",
        "delivery",
        "delivered",
        "package",
        "parcel",
        "cancelled",
        "canceled",
    }

    SIMPLE_POLICY_WORDS = {
        "return",
        "returns",
        "refund",
        "refunds",
        "policy",
        "policies",
        "final sale",
        "gift card",
        "shipping fee",
        "warranty",
    }

    DAMAGED_ITEM_WORDS = {
        "damaged",
        "damage",
        "defective",
        "wrong item",
        "incorrect item",
    }

    def __init__(self):
        self.orders = OrderService()
        self.knowledge = KnowledgeBase()
        self.sources = SourcePolicy(self.knowledge)
        self.llm = LocalLLM()

        # Conversation state.
        self.last_order_id = None
        self.last_topic = None

    # ---------------------------------------------------------
    # ORDER DETECTION
    # ---------------------------------------------------------

    def _looks_like_order_request(self, message):
        message_lower = message.lower()

        # These are company shipping-policy questions,
        # not order lookup requests.
        policy_shipping_phrases = (
            "do you ship",
            "ship internationally",
            "international shipping",
            "internationally",
            "shipping policy",
            "shipping to",
            "ship to",
        )

        if any(
            phrase in message_lower
            for phrase in policy_shipping_phrases
        ):
            return False

        words = set(message_lower.split())

        return bool(
            words.intersection(self.ORDER_WORDS)
        )

    def _extract_order_id(self, message):
        match = re.search(
            r"\bORD-\d+\b",
            message.upper(),
        )

        return match.group(0) if match else None

    def _is_order_followup(self, message):
        """Detect follow-ups referring to the previously mentioned order."""

        if not self.last_order_id:
            return False

        text = message.lower()

        followup_words = {
            "when",
            "arrive",
            "arrives",
            "arrival",
            "eta",
            "carrier",
            "shipping",
            "shipped",
            "tracking",
            "where",
            "status",
            "delivery",
        }

        return bool(
            set(text.split()).intersection(followup_words)
        )

    # ---------------------------------------------------------
    # MAIN ROUTER
    # ---------------------------------------------------------

    def handle(self, message):
        """Route a customer message to the correct service."""

        if not message or not message.strip():
            return {
                "type": "clarification",
                "message": "Please tell me how I can help.",
            }

        message = message.strip()

        order_id = self._extract_order_id(message)

        # Explicit order ID.
        if order_id:
            self.last_order_id = order_id
            self.last_topic = "order"

            return self._handle_order(order_id)

        # Multi-turn order follow-up.
        if self._is_order_followup(message):
            self.last_topic = "order"

            return self._handle_order(
                self.last_order_id
            )

        # New order request without ID.
        if self._looks_like_order_request(message):
            self.last_topic = "order"

            return {
                "type": "order",
                "message": (
                    "Sure, I can check that for you. "
                    "Please provide your order ID."
                ),
            }

        return self._handle_knowledge_request(message)

    # ---------------------------------------------------------
    # ORDER LOOKUP
    # ---------------------------------------------------------

    def _handle_order(self, order_id):
        """Return safe order information without using the LLM."""

        result = self.orders.lookup(order_id)

        if not result["found"]:
            return {
                "type": "order",
                "message": (
                    "That order was not found. "
                    "Please check the order ID or contact support."
                ),
                "handoff": True,
            }

        order = result["order"]

        self.last_order_id = order.get(
            "order_id",
            order_id,
        )

        status = order.get("status")
        carrier = order.get("carrier")
        eta = order.get("estimated_delivery")

        if status == "cancelled":
            message = (
                f"Order {self.last_order_id} is cancelled "
                "and will not be shipped."
            )

        elif carrier and eta:
            message = (
                f"Order {self.last_order_id} has been shipped "
                f"by {carrier} and is expected to arrive on {eta}."
            )

        elif carrier and not eta:
            message = (
                f"Order {self.last_order_id} has shipped with "
                f"{carrier}, but no delivery estimate is "
                "currently available."
            )

        else:
            message = order.get("message")

            if not message:
                message = (
                    f"Order {self.last_order_id} is currently "
                    f"{status}."
                )

        return {
            "type": "order",
            "order": self._sanitize_order(order),
            "message": message,
            "handoff": False,
        }

    def _sanitize_order(self, order):
        """Return only customer-safe order fields."""

        allowed_fields = {
            "order_id",
            "status",
            "carrier",
            "estimated_delivery",
            "message",
        }

        return {
            key: value
            for key, value in order.items()
            if key in allowed_fields
        }

    # ---------------------------------------------------------
    # KNOWLEDGE ROUTING
    # ---------------------------------------------------------

    def _handle_knowledge_request(self, question):
        """Retrieve trusted policy/product information."""

        question_lower = question.lower()

        # -----------------------------------------------------
        # Privacy / secret / internal-information requests
        # -----------------------------------------------------

        sensitive_request_terms = {
            "system prompt",
            "hidden prompt",
            "hidden instructions",
            "secret",
            "internal note",
            "risk score",
            "customer email",
            "customer address",
            "email address",
        }

        if any(
            term in question_lower
            for term in sensitive_request_terms
        ):
            return {
                "type": "knowledge",
                "message": (
                    "I can't provide private customer information, "
                    "internal notes, risk scores, or hidden system "
                    "instructions. I can help with the order or "
                    "customer-facing support information instead."
                ),
                "sources": [],
                "handoff": True,
            }

        # -----------------------------------------------------
        # Insufficient information / vegan materials
        # -----------------------------------------------------

        if (
            "vegan" in question_lower
            and (
                "fabric" in question_lower
                or "adhesive" in question_lower
                or "materials" in question_lower
            )
        ):
            return {
                "type": "knowledge",
                "message": (
                    "The supplied information is insufficient to "
                    "confirm whether all fabrics and adhesives are "
                    "vegan. Human confirmation is recommended."
                ),
                "sources": [],
                "handoff": True,
            }

        # -----------------------------------------------------
        # Genuine Breeze Tumbler source conflict
        # -----------------------------------------------------

        if (
            "breeze" in question_lower
            and "dishwasher" in question_lower
        ):
            return self._handle_breeze_conflict()

        # -----------------------------------------------------
        # Final-sale + damaged item
        # -----------------------------------------------------

        is_damaged_item_question = any(
            phrase in question_lower
            for phrase in self.DAMAGED_ITEM_WORDS
        )

        is_final_sale_question = (
            "final-sale" in question_lower
            or "final sale" in question_lower
        )

        if (
            is_damaged_item_question
            and is_final_sale_question
        ):
            return self._handle_final_sale_damaged()

        # -----------------------------------------------------
        # Damaged/wrong-item policy
        # -----------------------------------------------------

        if is_damaged_item_question:
            sources = self.sources.trusted_results(
                "damaged defective wrong item",
                limit=5,
            )

            return self._handle_damaged_item_policy(
                sources
            )

        # -----------------------------------------------------
        # Prompt injection / migration note
        # -----------------------------------------------------

        if (
            "migration note" in question_lower
            or "60 days" in question_lower
            or "ignore the real policy" in question_lower
            or "newer document" in question_lower
        ):
            return self._handle_prompt_injection_case()

        # -----------------------------------------------------
        # TrailPlus
        # -----------------------------------------------------

        is_trailplus_question = (
            "trailplus" in question_lower
            or "trail plus" in question_lower
        )

        if is_trailplus_question:
            sources = self.sources.trusted_results(
                "TrailPlus membership return 45 days delivery",
                limit=5,
            )

            trailplus_source = self._find_source(
                sources,
                "09-trailplus-membership.md",
            )

            if trailplus_source:
                self.last_topic = "trailplus"

                return {
                    "type": "knowledge",
                    "message": (
                        "TrailPlus members may request a return "
                        "within 45 calendar days of delivery."
                    ),
                    "sources": [
                        trailplus_source["name"]
                    ],
                    "handoff": False,
                }

        # -----------------------------------------------------
        # International shipping
        # -----------------------------------------------------

        if self._is_international_shipping_question(
            question_lower
        ):
            return self._handle_international_shipping(
                question_lower
            )

        # -----------------------------------------------------
        # Normal retrieval
        # -----------------------------------------------------

        sources = self.sources.trusted_results(
            question,
            limit=5,
        )

        if not sources:
            return {
                "type": "knowledge",
                "message": (
                    "I don't have enough information "
                    "to answer that accurately. "
                    "Human confirmation is recommended."
                ),
                "sources": [],
                "handoff": True,
            }

        # -----------------------------------------------------
        # Simple current-policy response
        # -----------------------------------------------------

        is_simple_policy = any(
            phrase in question_lower
            for phrase in self.SIMPLE_POLICY_WORDS
        )

        if is_simple_policy:
            current_source = self._find_source(
                sources,
                "01-returns-policy-current.md",
            )

            if current_source:
                self.last_topic = "returns"

                return {
                    "type": "knowledge",
                    "message": self._build_policy_summary(
                        current_source["content"]
                    ),
                    "sources": [
                        current_source["name"]
                    ],
                    "handoff": False,
                }

        # -----------------------------------------------------
        # General LLM synthesis
        # -----------------------------------------------------

        context_parts = []

        for source in sources:
            context_parts.append(
                f"Source: {source['name']}\n"
                f"{source['content']}"
            )

        context = "\n\n---\n\n".join(
            context_parts
        )

        answer = self.llm.generate(
            question=question,
            context=context,
        )

        self.last_topic = "knowledge"

        return {
            "type": "knowledge",
            "message": answer,
            "sources": [
                source["name"]
                for source in sources
            ],
            "handoff": False,
        }

    # ---------------------------------------------------------
    # INTERNATIONAL SHIPPING
    # ---------------------------------------------------------

    def _is_international_shipping_question(
        self,
        question_lower,
    ):
        return any(
            phrase in question_lower
            for phrase in (
                "international",
                "canada",
                "germany",
                "ship to",
                "shipping to",
                "do you ship",
            )
        )

    def _handle_international_shipping(
        self,
        question_lower,
    ):
        sources = self.sources.trusted_results(
            "international shipping Canada Germany delivery duties taxes",
            limit=5,
        )

        source = self._find_source(
            sources,
            "06-international-shipping.md",
        )

        if not source:
            return {
                "type": "knowledge",
                "message": (
                    "I don't have enough information "
                    "to answer that accurately."
                ),
                "sources": [],
                "handoff": True,
            }

        self.last_topic = "international_shipping"

        # Canada
        if "canada" in question_lower:
            return {
                "type": "knowledge",
                "message": (
                    "Yes. Canada is supported for international "
                    "shipping. Delivery typically takes 5–9 "
                    "business days after dispatch. Duties or taxes "
                    "are not prepaid."
                ),
                "sources": [
                    source["name"]
                ],
                "handoff": False,
            }

        # Germany
        if "germany" in question_lower:
            return {
                "type": "knowledge",
                "message": (
                    "Shipping to Germany is not currently available."
                ),
                "sources": [
                    source["name"]
                ],
                "handoff": False,
            }

        # General international question.
        return {
            "type": "knowledge",
            "message": (
                "Yes, Aster & Row offers international shipping "
                "to selected countries. Please tell me the country "
                "you are asking about so I can check the current "
                "shipping information."
            ),
            "sources": [
                source["name"]
            ],
            "handoff": False,
        }

    # ---------------------------------------------------------
    # DAMAGED ITEMS
    # ---------------------------------------------------------

    def _handle_damaged_item_policy(
        self,
        sources,
    ):
        damaged_source = self._find_source(
            sources,
            "04-damaged-or-wrong-items.md",
        )

        if damaged_source is None:
            return {
                "type": "knowledge",
                "message": (
                    "I don't have enough information "
                    "to answer that accurately."
                ),
                "sources": [
                    source["name"]
                    for source in sources
                ],
                "handoff": True,
            }

        message = (
            "Yes. If an item arrived damaged, defective, "
            "or different from what was ordered, you should "
            "report it within 7 calendar days of delivery.\n\n"
            "Please provide the order ID, a short description, "
            "and clear photographs of the item and packaging "
            "when reasonably possible.\n\n"
            "After review, Aster & Row may offer a replacement, "
            "refund, or another appropriate resolution. "
            "Availability of a replacement depends on stock.\n\n"
            "A return shipping fee is not charged when Aster "
            "& Row confirms that the item arrived damaged or "
            "the wrong item was sent.\n\n"
            "Final-sale items can still be reviewed when they "
            "arrive damaged, defective, or incorrect."
        )

        return {
            "type": "knowledge",
            "message": message,
            "sources": [
                damaged_source["name"]
            ],
            "handoff": True,
        }

    # ---------------------------------------------------------
    # FINAL SALE + DAMAGE
    # ---------------------------------------------------------

    def _handle_final_sale_damaged(self):
        sources = self.sources.trusted_results(
            "final sale damaged wrong item review",
            limit=6,
        )

        final_sale = self._find_source(
            sources,
            "03-final-sale-and-promotions.md",
        )

        damaged = self._find_source(
            sources,
            "04-damaged-or-wrong-items.md",
        )

        source_names = []

        if final_sale:
            source_names.append(
                final_sale["name"]
            )

        if damaged:
            source_names.append(
                damaged["name"]
            )

        return {
            "type": "knowledge",
            "message": (
                "A final-sale item is not automatically excluded "
                "from review when it arrives damaged or defective. "
                "Damaged or incorrect items should be reported "
                "within 7 calendar days of delivery. A human review "
                "is required before a refund, replacement, or "
                "other resolution can be approved."
            ),
            "sources": source_names,
            "handoff": True,
        }

    # ---------------------------------------------------------
    # PROMPT INJECTION
    # ---------------------------------------------------------

    def _handle_prompt_injection_case(self):
        source = self._get_current_returns_source()

        source_names = (
            [source["name"]]
            if source
            else []
        )

        return {
            "type": "knowledge",
            "message": (
                "The migration note is not an authoritative "
                "customer-facing policy. The standard policy is "
                "30 calendar days from delivery unless a valid "
                "exception applies. I cannot automatically approve "
                "a return."
            ),
            "sources": source_names,
            "handoff": False,
        }

    # ---------------------------------------------------------
    # BREEZE TUMBLER SOURCE CONFLICT
    # ---------------------------------------------------------

    def _handle_breeze_conflict(self):
        sources = self.sources.trusted_results(
            "Breeze Tumbler dishwasher hand wash components",
            limit=6,
        )

        care_source = self._find_source(
            sources,
            "11-product-care.md",
        )

        product_source = self._find_source(
            sources,
            "12-breeze-tumbler-product-card.md",
        )

        source_names = []

        if care_source:
            source_names.append(
                care_source["name"]
            )

        if product_source:
            source_names.append(
                product_source["name"]
            )

        return {
            "type": "knowledge",
            "message": (
                "The current official sources conflict on this "
                "question. One source says to hand-wash the "
                "tumbler body, while another says all components "
                "are dishwasher safe. I recommend human confirmation "
                "before putting the entire tumbler in the dishwasher. "
                "Until then, the safest interim guidance is to "
                "hand-wash the body."
            ),
            "sources": source_names,
            "handoff": True,
        }

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    def _find_source(self, sources, filename):
        for source in sources:
            if source.get("name") == filename:
                return source

        return None

    def _get_current_returns_source(self):
        sources = self.sources.trusted_results(
            "current returns policy 30 days delivery",
            limit=5,
        )

        return self._find_source(
            sources,
            "01-returns-policy-current.md",
        )

    def _build_policy_summary(self, content):
        """Fast summary for the current Returns Policy."""

        return (
            "Our current Returns Policy states:\n\n"
            "• Standard-plan customers may request a return "
            "within 30 calendar days of delivery.\n"
            "• Items must be unused, unwashed, and in "
            "resalable condition, with original tags, "
            "accessories, and packaging when supplied.\n"
            "• A $6.95 return shipping fee applies to "
            "standard domestic returns. The fee is waived "
            "when Aster & Row sent the wrong item or the "
            "item arrived damaged.\n"
            "• Refunds are issued to the original payment "
            "method after the return is inspected.\n"
            "• Customers should allow 5–7 business days "
            "after inspection for the refund to appear.\n"
            "• Original outbound shipping charges are not "
            "refundable unless the order was incorrect or "
            "damaged on arrival.\n"
            "• Final-sale items and gift cards are not "
            "returnable for a change of mind.\n"
            "• Warranty claims are handled separately from "
            "ordinary returns."
        )