from app.order_service import OrderService
from app.knowledge_base import KnowledgeBase
from app.source_policy import SourcePolicy


class CustomerAssistant:
    """Routes customer questions to the appropriate support capability."""

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

    def __init__(self):
        self.orders = OrderService()
        self.knowledge = KnowledgeBase()
        self.sources = SourcePolicy(self.knowledge)

    def _looks_like_order_request(self, message):
        words = set(message.lower().split())

        return bool(words & self.ORDER_WORDS)

    def _extract_order_id(self, message):
        import re

        match = re.search(
            r"\bORD-\d+\b",
            message.upper()
        )

        return match.group(0) if match else None

    def handle(self, message):
        """Process one customer message."""

        if not message or not message.strip():
            return {
                "type": "clarification",
                "message": "Please tell me how I can help."
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
                )
            }

        return self._handle_knowledge_request(message)

    def _handle_order(self, order_id):
        result = self.orders.lookup(order_id)

        if not result["found"]:
            return {
                "type": "order",
                "message": result["message"]
            }

        return {
            "type": "order",
            "order": result["order"]
        }

    def _handle_knowledge_request(self, message):
        sources = self.sources.trusted_results(
            message,
            limit=3
        )

        return {
            "type": "knowledge",
            "sources": sources
        }