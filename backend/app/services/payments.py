import hashlib
import hmac

import mercadopago
from flask import current_app


def _sdk():
    return mercadopago.SDK(current_app.config["MERCADO_PAGO_ACCESS_TOKEN"])


def create_checkout_preference(order, product, seller, buyer):
    amount = order["total_cents"] / 100
    preference = {
        "items": [
            {
                "id": str(product["_id"]),
                "title": product["title"],
                "description": product["description"][:250],
                "quantity": order["quantity"],
                "currency_id": "BRL",
                "unit_price": product["price_cents"] / 100,
            }
        ],
        "payer": {"email": buyer["email"], "name": buyer.get("name", "")},
        "external_reference": str(order["_id"]),
        "statement_descriptor": "ARTEIRA",
        "back_urls": {
            "success": f"{current_app.config['WEB_BASE_URL']}/orders/{order['_id']}?payment=success",
            "failure": f"{current_app.config['WEB_BASE_URL']}/orders/{order['_id']}?payment=failure",
            "pending": f"{current_app.config['WEB_BASE_URL']}/orders/{order['_id']}?payment=pending",
        },
        "auto_return": "approved",
        "notification_url": f"{current_app.config['API_BASE_URL']}/api/payments/mercadopago/webhook",
        "metadata": {
            "order_id": str(order["_id"]),
            "seller_id": str(seller["_id"]),
            "buyer_id": str(buyer["_id"]),
        },
    }
    return _sdk().preference().create(preference)["response"]


def get_payment(payment_id):
    return _sdk().payment().get(payment_id)["response"]


def verify_webhook_signature(signature_header, request_id, data_id):
    secret = current_app.config["MERCADO_PAGO_WEBHOOK_SECRET"]
    if not secret:
        return True
    if not signature_header or not request_id or not data_id:
        return False
    parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    received = parts.get("v1")
    timestamp = parts.get("ts")
    if not received or not timestamp:
        return False
    manifest = f"id:{data_id};request-id:{request_id};ts:{timestamp};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)
