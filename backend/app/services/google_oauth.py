from google.auth.transport import requests
from google.oauth2 import id_token


def verify_google_id_token(token, client_id):
    payload = id_token.verify_oauth2_token(token, requests.Request(), client_id)
    return {
        "google_sub": payload["sub"],
        "email": payload["email"],
        "name": payload.get("name", payload["email"].split("@")[0]),
        "picture": payload.get("picture", ""),
        "email_verified": payload.get("email_verified", False),
    }
