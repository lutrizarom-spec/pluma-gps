import os
import sys
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_socketio import SocketIO
from flask import request
from api.auth import decode_token
import jwt as jwt_lib

socketio = SocketIO(cors_allowed_origins="*")

# Connected clients: sid -> user_id
_clients = {}


@socketio.on("connect")
def handle_connect(auth=None):
    token = None
    # flask-socketio passes auth dict or query string
    if auth and isinstance(auth, dict):
        token = auth.get("token")
    if not token:
        token = request.args.get("token")
    if not token:
        # Try Authorization header
        hdr = request.headers.get("Authorization", "")
        if hdr.startswith("Bearer "):
            token = hdr[7:]
    if not token:
        return False  # reject

    try:
        payload = decode_token(token)
        from flask_socketio import join_room
        _clients[request.sid] = payload["user_id"]
        join_room("telemetry")
        return True
    except (jwt_lib.ExpiredSignatureError, jwt_lib.InvalidTokenError):
        return False  # reject


@socketio.on("disconnect")
def handle_disconnect():
    _clients.pop(request.sid, None)


def broadcast_telemetry(data: dict):
    """Emit telemetry to all connected clients in 'telemetry' room."""
    socketio.emit("telemetry_update", data, room="telemetry")


def get_client_count() -> int:
    return len(_clients)
