from flask import Flask, jsonify
from flask_cors import CORS

from app.config import Config
from app.database import close_mongo, init_indexes
from app.routes.auth import auth_bp
from app.routes.health import health_bp
from app.routes.orders import orders_bp
from app.routes.payments import payments_bp
from app.routes.products import products_bp
from app.routes.sellers import sellers_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
    )

    init_indexes(app)
    app.teardown_appcontext(close_mongo)

    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(sellers_bp, url_prefix="/api/sellers")
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(orders_bp, url_prefix="/api/orders")
    app.register_blueprint(payments_bp, url_prefix="/api/payments")

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "bad_request", "message": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "not_found", "message": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "server_error", "message": "Unexpected server error"}), 500

    return app
