"""Tests WebSocket: conexión con token, rechazo sin token, broadcast de telemetría."""
import unittest
import os
import sys
import tempfile
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conectar import crear_conexion
from dao.dao import Dao
from api.app import app, socketio
from api.auth import generate_token
from api.ws import _clients


class BaseWsTest(unittest.TestCase):

    def setUp(self):
        _, self.db_path = tempfile.mkstemp(suffix=".db")
        from api import app as app_module
        app_module.DB_PATH = self.db_path
        conn = crear_conexion(self.db_path)
        Dao(conn).crear_todas_las_tablas()
        conn.close()

        # Registrar usuario y obtener token
        from api import app as app_module
        self.client = app.test_client()
        self.client.testing = True

        r = self.client.post("/api/auth/register", json={
            "rut": "18.629.694-K",
            "full_name": "WS User",
            "email": "ws@test.cl",
            "password": "secret123",
            "plan": "ENTERPRISE_FLEET",
        })
        self.token = r.get_json()["token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

        # Setup vehicle + gps
        r2 = self.client.post("/api/users", json={
            "rut": "12.345.678-5", "full_name": "Juan", "email": "j@test.cl",
        })
        uid = r2.get_json()["user_id"]
        r3 = self.client.post(f"/api/users/{uid}/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        vid = r3.get_json()["vehicle_id"]
        r4 = self.client.post(f"/api/vehicles/{vid}/gps", json={
            "imei": "123456789012345", "is_online": True,
        }, headers=self.auth_headers)
        self.device_id = r4.get_json()["device_id"]

        # SocketIO test client
        self.sio_client = socketio.test_client(app, auth={"token": self.token})

    def tearDown(self):
        self.sio_client.disconnect()
        import gc
        gc.collect()
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except PermissionError:
            pass


class TestWsConnection(BaseWsTest):

    def test_conexion_token_valido(self):
        """Cliente con token válido se conecta exitosamente."""
        # Si llegó aquí sin excepción, la conexión fue exitosa
        self.assertTrue(self.sio_client.is_connected())

    def test_rechazo_sin_token(self):
        """Cliente sin token debe ser rechazado."""
        bad_client = socketio.test_client(app)
        self.assertFalse(bad_client.is_connected())

    def test_rechazo_token_invalido(self):
        """Cliente con token inválido debe ser rechazado."""
        bad_client = socketio.test_client(app, auth={"token": "token-falso"})
        self.assertFalse(bad_client.is_connected())

    def test_rechazo_token_expirado(self):
        """Cliente con token expirado debe ser rechazado."""
        import datetime as dt
        import jwt as jwt_lib
        from api.auth import SECRET_KEY
        payload = {
            "user_id": "fake",
            "rut": "18.629.694-K",
            "plan": "ENTERPRISE_FLEET",
            "iat": dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=25),
            "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
        }
        expired = jwt_lib.encode(payload, SECRET_KEY, algorithm="HS256")
        bad_client = socketio.test_client(app, auth={"token": expired})
        self.assertFalse(bad_client.is_connected())


class TestWsBroadcast(BaseWsTest):

    def test_broadcast_al_post_telemetria(self):
        """POST /api/telemetry debe emitir broadcast por WebSocket."""
        self.sio_client.get_received()

        r = self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(-70.55 -33.45)",
            "speed_kmh": 25.0,
            "acc_ignition": True,
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201)

        received = self.sio_client.get_received()
        self.assertTrue(len(received) > 0, "No se recibió broadcast")

        msg = received[0]
        self.assertEqual(msg["name"], "telemetry_update")
        data = msg["args"][0]
        self.assertEqual(data["device_id"], self.device_id)
        self.assertEqual(data["speed_kmh"], 25.0)
        self.assertIn("point_wkt", data)

    def test_broadcast_multiple_telemetrias(self):
        """Múltiples POST deben generar múltiples broadcasts."""
        self.sio_client.get_received()

        for i in range(3):
            self.client.post("/api/telemetry", json={
                "device_id": self.device_id,
                "point_wkt": f"POINT(-70.{i} -33.{i})",
                "speed_kmh": float(i * 10),
            }, headers=self.auth_headers)

        received = self.sio_client.get_received()
        self.assertGreaterEqual(len(received), 3)

    def test_broadcast_contiene_campos_clave(self):
        """El broadcast debe incluir device_id, speed, point_wkt, acc_ignition."""
        self.sio_client.get_received()

        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(-70.5 -33.4)",
            "speed_kmh": 15.0,
            "heading": 90.0,
            "acc_ignition": True,
            "odometer_km": 12500.0,
            "dashcam_recording": True,
        }, headers=self.auth_headers)

        received = self.sio_client.get_received()
        self.assertTrue(len(received) > 0)
        data = received[0]["args"][0]
        for campo in ["telemetry_id", "device_id", "point_wkt", "speed_kmh",
                      "heading", "acc_ignition", "odometer_km", "dashcam_recording"]:
            self.assertIn(campo, data, f"Falta campo {campo} en broadcast")


class TestWsMultipleClients(BaseWsTest):

    def test_multiples_clientes_reciben_broadcast(self):
        """Dos clientes conectados deben recibir el mismo broadcast."""
        client2 = socketio.test_client(app, auth={"token": self.token})
        self.assertTrue(client2.is_connected())

        # Limpiar buffers
        self.sio_client.get_received()
        client2.get_received()

        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(-70.5 -33.4)",
            "speed_kmh": 42.0,
        }, headers=self.auth_headers)

        rec1 = self.sio_client.get_received()
        rec2 = client2.get_received()

        self.assertGreaterEqual(len(rec1), 1)
        self.assertGreaterEqual(len(rec2), 1)
        self.assertEqual(rec1[0]["args"][0]["speed_kmh"], 42.0)
        self.assertEqual(rec2[0]["args"][0]["speed_kmh"], 42.0)

        client2.disconnect()


if __name__ == "__main__":
    unittest.main()
