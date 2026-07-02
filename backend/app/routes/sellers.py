from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError
from pymongo import ReturnDocument

from app.database import get_db
from app.schemas.common import SellerSchema
from app.security import auth_required, serialize_id, utcnow

sellers_bp = Blueprint("sellers", __name__)
seller_schema = SellerSchema()


@sellers_bp.post("/me")
@auth_required
def upsert_seller():
    try:
        data = seller_schema.load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return jsonify({"error": "validation_error", "message": "Revise os campos do perfil de vendedor.", "fields": error.messages}), 422

    now = utcnow()
    db = get_db()
    seller = db.sellers.find_one_and_update(
        {"user_id": g.user_id},
        {
            "$set": {**data, "updated_at": now, "status": "active"},
            "$setOnInsert": {"user_id": g.user_id, "created_at": now, "rating": 0, "sales_count": 0},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    db.users.update_one({"_id": g.user_id}, {"$addToSet": {"roles": "seller"}})
    return jsonify({"seller": serialize_id(seller)})


@sellers_bp.get("/me")
@auth_required
def get_my_seller_profile():
    seller = get_db().sellers.find_one({"user_id": g.user_id})
    if not seller:
        return jsonify({"seller": None})
    return jsonify({"seller": serialize_id(seller)})
