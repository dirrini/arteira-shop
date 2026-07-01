from pymongo import ReturnDocument
from flask import Blueprint, current_app, jsonify, make_response, request

from app.database import get_db
from app.security import auth_required, create_token, serialize_id, utcnow
from app.services.google_oauth import verify_google_id_token

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/google")
def google_login():
    body = request.get_json(silent=True) or {}
    credential = body.get("credential")
    if not credential:
        return jsonify({"error": "bad_request", "message": "Missing Google credential"}), 400

    profile = verify_google_id_token(credential, current_app.config["GOOGLE_CLIENT_ID"])
    if not profile["email_verified"]:
        return jsonify({"error": "email_not_verified", "message": "Google email is not verified"}), 403

    now = utcnow()
    user = get_db().users.find_one_and_update(
        {"google_sub": profile["google_sub"]},
        {
            "$set": {
                "email": profile["email"],
                "name": profile["name"],
                "picture": profile["picture"],
                "updated_at": now,
                "last_login_at": now,
            },
            "$setOnInsert": {"created_at": now, "roles": ["buyer"]},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    response = make_response(jsonify({"user": serialize_id(user)}))
    response.set_cookie(
        "session",
        create_token(user),
        httponly=True,
        secure=current_app.config["COOKIE_SECURE"],
        samesite=current_app.config["COOKIE_SAMESITE"],
        max_age=current_app.config["JWT_EXPIRES_SECONDS"],
    )
    return response


@auth_bp.get("/me")
@auth_required
def me():
    from flask import g

    user = get_db().users.find_one({"_id": g.user_id})
    seller = get_db().sellers.find_one({"user_id": g.user_id})
    payload = {"user": serialize_id(user), "seller": serialize_id(seller) if seller else None}
    return jsonify(payload)


@auth_bp.post("/logout")
def logout():
    response = make_response(jsonify({"ok": True}))
    response.delete_cookie("session")
    return response
