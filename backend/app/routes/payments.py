from flask import Blueprint, jsonify, request
from pymongo import ReturnDocument

from app.database import get_db
from app.security import object_id, utcnow
from app.services.payments import get_payment, verify_webhook_signature

payments_bp = Blueprint("payments", __name__)


@payments_bp.post("/mercadopago/webhook")
def mercadopago_webhook():
    payload = request.get_json(silent=True) or {}
    data_id = str((payload.get("data") or {}).get("id") or request.args.get("data.id") or "")
    request_id = request.headers.get("x-request-id")
    signature = request.headers.get("x-signature")
    if not verify_webhook_signature(signature, request_id, data_id):
        return jsonify({"error": "invalid_signature"}), 401

    topic = payload.get("type") or request.args.get("type")
    if topic != "payment" or not data_id:
        return jsonify({"ok": True})

    payment = get_payment(data_id)
    order_id = object_id(payment.get("external_reference", ""))
    if not order_id:
        return jsonify({"ok": True})

    status = payment.get("status", "pending")
    order_status = {
        "approved": "paid",
        "pending": "pending_payment",
        "in_process": "pending_payment",
        "rejected": "payment_failed",
        "cancelled": "cancelled",
        "refunded": "refunded",
        "charged_back": "charged_back",
    }.get(status, "pending_payment")

    db = get_db()
    order = db.orders.find_one_and_update(
        {"_id": order_id},
        {
            "$set": {
                "status": order_status,
                "payment.status": status,
                "payment.provider_payment_id": str(payment.get("id")),
                "payment.detail": payment.get("status_detail"),
                "updated_at": utcnow(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if order and order_status == "paid" and not order.get("inventory_committed_at"):
        db.products.update_one(
            {"_id": order["product_id"], "inventory": {"$gte": order["quantity"]}},
            {"$inc": {"inventory": -order["quantity"]}, "$set": {"updated_at": utcnow()}},
        )
        db.orders.update_one({"_id": order["_id"]}, {"$set": {"inventory_committed_at": utcnow()}})
        db.sellers.update_one({"_id": order["seller_id"]}, {"$inc": {"sales_count": order["quantity"]}})

    return jsonify({"ok": True})
