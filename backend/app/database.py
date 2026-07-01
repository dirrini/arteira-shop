from flask import current_app, g
from pymongo import ASCENDING, DESCENDING, MongoClient, TEXT


def get_client():
    if "mongo_client" not in g:
        g.mongo_client = MongoClient(current_app.config["MONGO_URI"])
    return g.mongo_client


def get_db():
    return get_client()[current_app.config["MONGO_DB"]]


def close_mongo(error=None):
    client = g.pop("mongo_client", None)
    if client is not None:
        client.close()


def init_indexes(app):
    with app.app_context():
        db = get_db()
        db.users.create_index([("google_sub", ASCENDING)], unique=True)
        db.users.create_index([("email", ASCENDING)], unique=True)
        db.sellers.create_index([("user_id", ASCENDING)], unique=True)
        db.products.create_index(
            [("title", TEXT), ("description", TEXT), ("category", TEXT)],
            default_language="portuguese",
        )
        db.products.create_index([("seller_id", ASCENDING), ("status", ASCENDING)])
        db.products.create_index([("created_at", DESCENDING)])
        db.orders.create_index([("buyer_id", ASCENDING), ("created_at", DESCENDING)])
        db.orders.create_index([("seller_id", ASCENDING), ("created_at", DESCENDING)])
        db.orders.create_index([("payment.preference_id", ASCENDING)], sparse=True)
