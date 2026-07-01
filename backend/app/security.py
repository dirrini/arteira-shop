from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from bson import ObjectId
from flask import current_app, g, jsonify, request


def utcnow():
    return datetime.now(timezone.utc)


def object_id(value):
    if not ObjectId.is_valid(value):
        return None
    return ObjectId(value)


def serialize_id(document):
    if not document:
        return document
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    for key in ("user_id", "seller_id", "buyer_id", "product_id"):
        if key in document and isinstance(document[key], ObjectId):
            document[key] = str(document[key])
    return document


def create_token(user):
    now = utcnow()
    payload = {
        "sub": str(user["_id"]),
        "iss": current_app.config["JWT_ISSUER"],
        "aud": current_app.config["JWT_AUDIENCE"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=current_app.config["JWT_EXPIRES_SECONDS"])).timestamp()),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def decode_token(token):
    return jwt.decode(
        token,
        current_app.config["JWT_SECRET"],
        algorithms=["HS256"],
        audience=current_app.config["JWT_AUDIENCE"],
        issuer=current_app.config["JWT_ISSUER"],
    )


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("session")
        auth_header = request.headers.get("Authorization", "")
        if not token and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return jsonify({"error": "unauthorized", "message": "Login required"}), 401
        try:
            claims = decode_token(token)
        except jwt.PyJWTError:
            return jsonify({"error": "unauthorized", "message": "Invalid session"}), 401
        g.user_id = object_id(claims["sub"])
        return fn(*args, **kwargs)

    return wrapper
