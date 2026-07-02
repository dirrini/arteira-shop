from flask import Blueprint, current_app, jsonify, make_response, request
from marshmallow import ValidationError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import get_db
from app.schemas.common import LoginSchema, RegisterSchema
from app.security import auth_required, create_token, serialize_id, serialize_user, utcnow
from app.services.google_oauth import verify_google_id_token

auth_bp = Blueprint("auth", __name__)


def _normalized_email(value):
    return value.strip().lower()


def _validation_error(error):
    return jsonify({"error": "validation_error", "message": "Check the submitted fields", "fields": error.messages}), 422


def _session_response(user, status=200):
    response = make_response(jsonify({"user": serialize_user(user)}), status)
    response.set_cookie(
        "session",
        create_token(user),
        httponly=True,
        secure=current_app.config["COOKIE_SECURE"],
        samesite=current_app.config["COOKIE_SAMESITE"],
        max_age=current_app.config["JWT_EXPIRES_SECONDS"],
    )
    return response


@auth_bp.post("/register")
def register():
    try:
        data = RegisterSchema().load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return _validation_error(error)

    now = utcnow()
    user = {
        "email": _normalized_email(data["email"]),
        "name": data["name"].strip(),
        "picture": "",
        "password_hash": generate_password_hash(data["password"]),
        "email_verified": False,
        "auth_providers": ["password"],
        "roles": ["buyer"],
        "created_at": now,
        "updated_at": now,
        "last_login_at": now,
    }
    try:
        result = get_db().users.insert_one(user)
    except DuplicateKeyError:
        return jsonify({"error": "email_in_use", "message": "Já existe uma conta com este e-mail."}), 409

    user["_id"] = result.inserted_id
    return _session_response(user, 201)


@auth_bp.post("/login")
def password_login():
    try:
        data = LoginSchema().load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return _validation_error(error)

    user = get_db().users.find_one({"email": _normalized_email(data["email"])})
    if not user or not user.get("password_hash") or not check_password_hash(user["password_hash"], data["password"]):
        return jsonify({"error": "invalid_credentials", "message": "E-mail ou senha inválidos."}), 401

    user = get_db().users.find_one_and_update(
        {"_id": user["_id"]},
        {"$set": {"last_login_at": utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    return _session_response(user)


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
    email = _normalized_email(profile["email"])
    db = get_db()
    user = db.users.find_one({"google_sub": profile["google_sub"]}) or db.users.find_one({"email": email})
    if user:
        user = db.users.find_one_and_update(
            {"_id": user["_id"]},
            {
                "$set": {
                    "google_sub": profile["google_sub"],
                    "email": email,
                    "name": profile["name"],
                    "picture": profile["picture"],
                    "email_verified": True,
                    "updated_at": now,
                    "last_login_at": now,
                },
                "$addToSet": {"auth_providers": "google"},
            },
            return_document=ReturnDocument.AFTER,
        )
    else:
        user = {
            "google_sub": profile["google_sub"],
            "email": email,
            "name": profile["name"],
            "picture": profile["picture"],
            "email_verified": True,
            "auth_providers": ["google"],
            "created_at": now,
            "updated_at": now,
            "last_login_at": now,
            "roles": ["buyer"],
        }
        result = db.users.insert_one(user)
        user["_id"] = result.inserted_id

    return _session_response(user)


@auth_bp.get("/me")
@auth_required
def me():
    from flask import g

    user = get_db().users.find_one({"_id": g.user_id})
    seller = get_db().sellers.find_one({"user_id": g.user_id})
    payload = {"user": serialize_user(user), "seller": serialize_id(seller) if seller else None}
    return jsonify(payload)


@auth_bp.post("/logout")
def logout():
    response = make_response(jsonify({"ok": True}))
    response.delete_cookie("session")
    return response
