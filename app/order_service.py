import json
from pathlib import Path


class OrderService:
    """Handles customer-safe order lookups."""

    def __init__(self, data_path=None):
        self.data_path = (
            Path(data_path)
            if data_path
            else Path(__file__).resolve().parent.parent / "data" / "orders.json"
        )

        self._orders = self._read_orders()

    def _read_orders(self):
        with self.data_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return {
            item["order_id"].upper(): item
            for item in data.get("orders", [])
        }

    def get_order(self, order_id):
        """Return the complete internal record for an order."""
        if not order_id:
            return None

        key = order_id.strip().upper()
        return self._orders.get(key)

    def get_customer_details(self, order_id):
        """
        Return only information that can safely be shown
        to a customer.
        """
        order = self.get_order(order_id)

        if order is None:
            return None

        status = order.get("status")

        result = {
            "order_id": order.get("order_id"),
            "status": status,
            "carrier": order.get("carrier"),
            "tracking_number": order.get("tracking_number"),
            "estimated_delivery": order.get("estimated_delivery"),
            "message": order.get("customer_safe_message"),
        }

        # Cancelled orders should not expose stale shipping information.
        if status == "cancelled":
            result["carrier"] = None
            result["tracking_number"] = None
            result["estimated_delivery"] = None

        return result

    def lookup(self, order_id):
        """Perform a customer-facing order lookup."""

        if not order_id:
            return {
                "found": False,
                "message": "Please provide your order ID so I can check the order."
            }

        order = self.get_customer_details(order_id)

        if order is None:
            return {
                "found": False,
                "message": (
                    f"I couldn't find order {order_id.strip().upper()}. "
                    "Please check the order ID and try again."
                )
            }

        return {
            "found": True,
            "order": order
        }