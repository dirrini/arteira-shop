from flask import Blueprint, jsonify

from app.database import get_db

health_bp = Blueprint("health", __name__)


@health_bp.get("")
def health():
    get_db().command("ping")
    return jsonify({"status": "ok"})
