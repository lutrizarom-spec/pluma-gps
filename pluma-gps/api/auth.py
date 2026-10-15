import os
import sys
from functools import wraps
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt
from flask import request, jsonify, g

APP_ENV = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "development")).lower()
_DEV_SECRET = "pluma-gps-dev-secret-key-2026-change-in-production"

SECRET_KEY = os.environ.get("JWT_SECRET")
if not SECRET_KEY:
    if APP_ENV == "production":
        raise RuntimeError(
            "JWT_SECRET no definido. Es obligatorio cuando APP_ENV=production; "
            "no se permite el secreto por defecto de desarrollo."
        )
    SECRET_KEY = _DEV_SECRET

ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def generate_token(user_id: str, rut: str, plan: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "rut": rut,
        "plan": plan,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(
        token, SECRET_KEY, algorithms=[ALGORITHM],
        options={"require": ["exp", "iat", "user_id", "rut", "plan"]},
    )


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token no proporcionado. Use: Authorization: Bearer <token>"}), 401
        token = auth_header[7:]
        try:
            payload = decode_token(token)
            g.user_id = payload["user_id"]
            g.rut = payload["rut"]
            g.plan = payload["plan"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated
