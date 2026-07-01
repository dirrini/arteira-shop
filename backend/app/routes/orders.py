from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError
from pymongo import ReturnDocument

from app.database import get_db
from app.schemas.common import CheckoutSchema
from app.security import auth_required, object_id, serialize_id, utcnow
from app.services.payments import create_checkout_preference

orders_bp = Blueprint("orders", __name__)
checkout_schema = CheckoutSchema()


def serialize_order(order):
    order = serialize_id(order)
    return order


@orders_bp.post("/checkout")
@auth_required
def checkout():
    try:
        data = checkout_schema.load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return jsonify({"error": "validation_error", "fields": error.messages}), 422

    product_id = object_id(data["product_id"])
    if not product_id:
        return jsonify({"error": "not_found", "message": "Product not found"}), 404

    db = get_db()
    product = db.products.find_one({"_id": product_id, "status": "published"})
    if not product:
        return jsonify({"error": "not_found", "message": "Product not found"}), 404
    if product["inventory"] < data["quantity"]:
        return jsonify({"error": "out_of_stock", "message": "Requested quantity is unavailable"}), 409
    seller = db.sellers.find_one({"_id": product["seller_id"], "status": "active"})
    buyer = db.users.find_one({"_id": g.user_id})
    if seller["user_id"] == g.user_id:
        return jsonify({"error": "invalid_order", "message": "Sellers cannot buy their own products"}), 409

    now = utcnow()
    order = {
        "buyer_id": g.user_id,
        "seller_id": seller["_id"],
        "product_id": product["_id"],
        "product_snapshot": {
            "title": product["title"],
            "price_cents": product["price_cents"],
            "image": product.get("images", [""])[0] if product.get("images") else "",
        },
        "quantity": data["quantity"],
        "subtotal_cents": product["price_cents"] * data["quantity"],
        "shipping_cents": 0,
        "total_cents": product["price_cents"] * data["quantity"],
        "currency": "BRL",
        "status": "pending_payment",
        "payment": {"provider": "mercadopago", "status": "pending"},
        "created_at": now,
        "updated_at": now,
    }
    result = db.orders.insert_one(order)
    order["_id"] = result.inserted_id

    preference = create_checkout_preference(order, product, seller, buyer)
    order = db.orders.find_one_and_update(
        {"_id": order["_id"]},
        {
            "$set": {
                "payment.preference_id": preference["id"],
                "payment.checkout_url": preference.get("init_point"),
                "payment.sandbox_checkout_url": preference.get("sandbox_init_point"),
                "updated_at": utcnow(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return jsonify({"order": serialize_order(order), "checkout_url": preference.get("init_point")})


@orders_bp.get("")
@auth_required
def list_orders():
    db = get_db()
    seller = db.sellers.find_one({"user_id": g.user_id})
    query = {"buyer_id": g.user_id}
    if request.args.get("role") == "seller" and seller:
        query = {"seller_id": seller["_id"]}
    orders = [serialize_order(order) for order in db.orders.find(query).sort("created_at", -1).limit(50)]
    return jsonify({"orders": orders})


@orders_bp.get("/<order_id>")
@auth_required
def get_order(order_id):
    oid = object_id(order_id)
    if not oid:
        return jsonify({"error": "not_found", "message": "Order not found"}), 404
    db = get_db()
    seller = db.sellers.find_one({"user_id": g.user_id})
    allowed = [{"buyer_id": g.user_id}]
    if seller:
        allowed.append({"seller_id": seller["_id"]})
    order = db.orders.find_one({"_id": oid, "$or": allowed})
    if not order:
        return jsonify({"error": "not_found", "message": "Order not found"}), 404
    return jsonify({"order": serialize_order(order)})
