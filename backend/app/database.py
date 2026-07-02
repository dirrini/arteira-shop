from flask import current_app, g
from pymongo import ASCENDING, DESCENDING, MongoClient, TEXT
from pymongo.errors import OperationFailure


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
        google_index = db.users.index_information().get("google_sub_1")
        if google_index and not google_index.get("sparse"):
            try:
                db.users.drop_index("google_sub_1")
            except OperationFailure as error:
                if error.code != 27:
                    raise
        db.users.create_index([("google_sub", ASCENDING)], unique=True, sparse=True)
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
