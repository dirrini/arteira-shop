import os

from dotenv import load_dotenv

load_dotenv()


def _csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    ENV = os.getenv("FLASK_ENV", "production")
    SECRET_KEY = os.environ["SECRET_KEY"]
    JWT_SECRET = os.environ["JWT_SECRET"]
    JWT_ISSUER = os.getenv("JWT_ISSUER", "arteira-api")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "arteira-web")
    JWT_EXPIRES_SECONDS = int(os.getenv("JWT_EXPIRES_SECONDS", "604800"))

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "craft_marketplace")

    CORS_ORIGINS = _csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))
    WEB_BASE_URL = os.getenv("WEB_BASE_URL", "http://localhost:5173")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")

    GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
    MERCADO_PAGO_ACCESS_TOKEN = os.environ["MERCADO_PAGO_ACCESS_TOKEN"]
    MERCADO_PAGO_WEBHOOK_SECRET = os.getenv("MERCADO_PAGO_WEBHOOK_SECRET", "")

    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
