from app.order_service import OrderService


def test_existing_order():
    service = OrderService()

    result = service.lookup("ORD-1007")

    assert result["found"] is True
    assert result["order"]["status"] == "shipped"
    assert result["order"]["carrier"] == "UPS"
    assert result["order"]["estimated_delivery"] == "2026-08-22"


def test_order_id_is_case_insensitive():
    service = OrderService()

    result = service.lookup("ord-1007")

    assert result["found"] is True
    assert result["order"]["order_id"] == "ORD-1007"


def test_unknown_order():
    service = OrderService()

    result = service.lookup("ORD-9999")

    assert result["found"] is False


def test_missing_order_id():
    service = OrderService()

    result = service.lookup("")

    assert result["found"] is False


def test_cancelled_order_hides_stale_shipping_data():
    service = OrderService()

    result = service.lookup("ORD-1004")

    assert result["found"] is True
    assert result["order"]["status"] == "cancelled"
    assert result["order"]["carrier"] is None
    assert result["order"]["tracking_number"] is None
    assert result["order"]["estimated_delivery"] is None


def test_order_without_eta_does_not_invent_one():
    service = OrderService()

    result = service.lookup("ORD-1011")

    assert result["found"] is True
    assert result["order"]["carrier"] == "Canada Post"
    assert result["order"]["estimated_delivery"] is None


def test_private_information_is_not_returned():
    service = OrderService()

    result = service.lookup("ORD-1007")

    order = result["order"]

    assert "customer" not in order
    assert "internal" not in order
    assert "risk_score" not in order
    assert "warehouse_note" not in order