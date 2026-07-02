from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError
from pymongo import ReturnDocument

from app.database import get_db
from app.schemas.common import ProductSchema
from app.security import auth_required, object_id, serialize_id, utcnow

products_bp = Blueprint("products", __name__)
product_schema = ProductSchema()


def product_response(product):
    product = serialize_id(product)
    return product


@products_bp.get("")
def list_products():
    db = get_db()
    query = {"status": "published", "inventory": {"$gt": 0}}
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    if search:
        query["$text"] = {"$search": search}
    if category:
        query["category"] = category
    limit = min(int(request.args.get("limit", 24)), 60)
    cursor = db.products.find(query).sort("created_at", -1).limit(limit)
    products = [product_response(product) for product in cursor]
    return jsonify({"products": products})


@products_bp.get("/<product_id>")
def get_product(product_id):
    oid = object_id(product_id)
    if not oid:
        return jsonify({"error": "not_found", "message": "Product not found"}), 404
    product = get_db().products.find_one({"_id": oid, "status": "published"})
    if not product:
        return jsonify({"error": "not_found", "message": "Product not found"}), 404
    seller = get_db().sellers.find_one({"_id": product["seller_id"]})
    return jsonify({"product": product_response(product), "seller": serialize_id(seller)})


@products_bp.post("")
@auth_required
def create_product():
    db = get_db()
    seller = db.sellers.find_one({"user_id": g.user_id, "status": "active"})
    if not seller:
        return jsonify({"error": "seller_required", "message": "Create a seller profile before publishing"}), 403
    try:
        data = product_schema.load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return jsonify({"error": "validation_error", "message": "Revise os campos do produto.", "fields": error.messages}), 422

    now = utcnow()
    product = {
        **data,
        "seller_id": seller["_id"],
        "status": "published",
        "created_at": now,
        "updated_at": now,
    }
    result = db.products.insert_one(product)
    product["_id"] = result.inserted_id
    return jsonify({"product": product_response(product)}), 201


@products_bp.get("/mine")
@auth_required
def my_products():
    seller = get_db().sellers.find_one({"user_id": g.user_id})
    if not seller:
        return jsonify({"products": []})
    products = [product_response(product) for product in get_db().products.find({"seller_id": seller["_id"]}).sort("created_at", -1)]
    return jsonify({"products": products})


@products_bp.patch("/<product_id>")
@auth_required
def update_product(product_id):
    oid = object_id(product_id)
    if not oid:
        return jsonify({"error": "not_found", "message": "Product not found"}), 404
    seller = get_db().sellers.find_one({"user_id": g.user_id})
    if not seller:
        return jsonify({"error": "seller_required", "message": "Seller profile required"}), 403
    try:
        data = product_schema.load(request.get_json(silent=True) or {}, partial=True)
    except ValidationError as error:
        return jsonify({"error": "validation_error", "message": "Revise os campos do produto.", "fields": error.messages}), 422
    product = get_db().products.find_one_and_update(
        {"_id": oid, "seller_id": seller["_id"]},
        {"$set": {**data, "updated_at": utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    if not product:
        return jsonify({"error": "not_found", "message": "Product not found"}), 404
    return jsonify({"product": product_response(product)})
