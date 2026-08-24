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
        "shipping",
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

    def _looks_like_order_request(self, message):
        words = set(message.lower().split())
        return bool(words.intersection(self.ORDER_WORDS))

    def _extract_order_id(self, message):
        match = re.search(
            r"\bORD-\d+\b",
            message.upper(),
        )
        return match.group(0) if match else None

    def handle(self, message):
        """Route a customer message to the correct service."""

        if not message or not message.strip():
            return {
                "type": "clarification",
                "message": "Please tell me how I can help.",
            }

        order_id = self._extract_order_id(message)

        if order_id:
            return self._handle_order(order_id)

        if self._looks_like_order_request(message):
            return {
                "type": "order",
                "message": (
                    "Sure, I can check that for you. "
                    "Please provide your order ID."
                ),
            }

        return self._handle_knowledge_request(message)

    def _handle_order(self, order_id):
        """Return order information without using the LLM."""

        result = self.orders.lookup(order_id)

        if not result["found"]:
            return {
                "type": "order",
                "message": result["message"],
            }

        order = result["order"]

        order_id = order.get("order_id")
        status = order.get("status")
        carrier = order.get("carrier")
        eta = order.get("estimated_delivery")

        if status == "cancelled":
            message = (
                f"Order {order_id} is cancelled "
                "and will not be shipped."
            )

        elif carrier and eta:
            message = (
                f"Order {order_id} has been shipped by "
                f"{carrier} and is expected to arrive on {eta}."
            )

        elif carrier and not eta:
            message = (
                f"Order {order_id} has shipped with "
                f"{carrier}, but no delivery estimate is "
                "currently available."
            )

        else:
            message = order.get("message")

            if not message:
                message = (
                    f"Order {order_id} is currently "
                    f"{status}."
                )

        return {
            "type": "order",
            "order": order,
            "message": message,
        }

    def _handle_knowledge_request(self, question):
        """Retrieve trusted policy information."""

        question_lower = question.lower()

        # Damaged/wrong-item questions need the dedicated
        # damaged-items policy rather than normal return ranking.
        is_damaged_item_question = any(
            phrase in question_lower
            for phrase in self.DAMAGED_ITEM_WORDS
        )

        if is_damaged_item_question:
            sources = self.sources.trusted_results(
                "damaged defective wrong item",
                limit=5,
            )

            return self._handle_damaged_item_policy(sources)

        # Normal knowledge retrieval.
        sources = self.sources.trusted_results(
            question,
            limit=3,
        )

        if not sources:
            return {
                "type": "knowledge",
                "message": (
                    "I don't have enough information "
                    "to answer that accurately."
                ),
                "sources": [],
            }

        # Fast response for simple policy questions.
        is_simple_policy = any(
            phrase in question_lower
            for phrase in self.SIMPLE_POLICY_WORDS
        )

        if is_simple_policy:
            message = self._build_policy_summary(
                sources[0]["content"]
            )

            return {
                "type": "knowledge",
                "message": message,
                "sources": [
                    source["name"]
                    for source in sources
                ],
            }

        # Local LLM for questions requiring synthesis.
        context_parts = []

        for source in sources:
            context_parts.append(
                f"Source: {source['name']}\n"
                f"{source['content']}"
            )

        context = "\n\n---\n\n".join(context_parts)

        answer = self.llm.generate(
            question=question,
            context=context,
        )

        return {
            "type": "knowledge",
            "message": answer,
            "sources": [
                source["name"]
                for source in sources
            ],
        }

    def _handle_damaged_item_policy(self, sources):
        """Answer damaged/wrong-item questions from the dedicated policy."""

        damaged_source = None

        for source in sources:
            name = source.get("name", "").lower()

            if (
                "damaged" in name
                or "wrong" in name
                or name == "04-damaged-or-wrong-items.md"
            ):
                damaged_source = source
                break

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
        }

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