"""Pruebas de seguridad (JWT/WebSockets) y de estrés (fan-out, concurrencia, throughput).

Cubre:
- JWT: algoritmos no permitidos (alg=none), firma manipulada, secreto incorrecto,
  expiración, formato inválido y claims requeridos ausentes.
- WebSocket: rechazo sin token / token inválido / expirado / firma incorrecta /
  sin claims, aceptación por query string, header y auth, y limpieza de clientes.
- Estrés: muchas conexiones WS, fan-out de broadcast, carga secuencial y
  concurrente de endpoints protegidos, throughput de encode/decode JWT.
"""
import base64
import datetime as dt
import gc
import json
import os
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jwt as jwt_lib

from conectar import crear_conexion
from dao.dao import Dao
from api.app import app, socketio
from api.auth import SECRET_KEY, decode_token

DEFAULT_RUT = "18.629.694-K"


def _b64url(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class BaseSecTest(unittest.TestCase):

    def setUp(self):
        _, self.db_path = tempfile.mkstemp(suffix=".db")
        from api import app as app_module
        app_module.DB_PATH = self.db_path
        conn = crear_conexion(self.db_path)
        Dao(conn).crear_todas_las_tablas()
        conn.close()

        from api.ws import _clients
        _clients.clear()

        self.client = app.test_client()
        self.client.testing = True
        r = self.client.post("/api/auth/register", json={
            "rut": DEFAULT_RUT,
            "full_name": "Sec User",
            "email": "sec@test.cl",
            "password": "secret123",
            "plan": "ENTERPRISE_FLEET",
        })
        self.token = r.get_json()["token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
        self._ws_clients = []

    def tearDown(self):
        for c in self._ws_clients:
            try:
                c.disconnect()
            except Exception:
                pass
        gc.collect()
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except PermissionError:
            pass

    def _ws(self, **kwargs):
        c = socketio.test_client(app, **kwargs)
        self._ws_clients.append(c)
        return c

    def _exp_payload(self, **overrides):
        now = dt.datetime.now(dt.timezone.utc)
        payload = {
            "user_id": "u-1",
            "rut": DEFAULT_RUT,
            "plan": "ENTERPRISE_FLEET",
            "iat": now,
            "exp": now + dt.timedelta(hours=1),
        }
        payload.update(overrides)
        return payload


class TestJwtSecurity(BaseSecTest):

    def _get_with(self, token):
        return self.client.get("/api/vehicles",
                               headers={"Authorization": f"Bearer {token}"})

    def test_alg_none_rechazado(self):
        token = jwt_lib.encode(self._exp_payload(), key="", algorithm="none")
        self.assertEqual(self._get_with(token).status_code, 401)

    def test_firma_manipulada_rechazada(self):
        header, _, signature = self.token.split(".")
        forged = _b64url({"user_id": "root", "rut": DEFAULT_RUT,
                          "plan": "ENTERPRISE_FLEET", "iat": 1, "exp": 9999999999})
        self.assertEqual(self._get_with(f"{header}.{forged}.{signature}").status_code, 401)

    def test_secreto_incorrecto_rechazado(self):
        token = jwt_lib.encode(self._exp_payload(), "otro-secreto", algorithm="HS256")
        self.assertEqual(self._get_with(token).status_code, 401)

    def test_token_expirado_rechazado(self):
        now = dt.datetime.now(dt.timezone.utc)
        token = jwt_lib.encode(self._exp_payload(
            iat=now - dt.timedelta(hours=25),
            exp=now - dt.timedelta(hours=1),
        ), SECRET_KEY, algorithm="HS256")
        r = self._get_with(token)
        self.assertEqual(r.status_code, 401)
        self.assertIn("expirado", r.get_json()["error"])

    def test_formatos_invalidos_rechazados(self):
        for bad in ["", "no-es-un-jwt", "a.b.c", "abc.def.ghi.jkl"]:
            self.assertEqual(self._get_with(bad).status_code, 401,
                             f"Token inválido aceptado: {bad!r}")

    def test_claim_user_id_ausente_rechazado(self):
        payload = self._exp_payload()
        del payload["user_id"]
        token = jwt_lib.encode(payload, SECRET_KEY, algorithm="HS256")
        self.assertEqual(self._get_with(token).status_code, 401)

    def test_claim_plan_ausente_rechazado(self):
        payload = self._exp_payload()
        del payload["plan"]
        token = jwt_lib.encode(payload, SECRET_KEY, algorithm="HS256")
        self.assertEqual(self._get_with(token).status_code, 401)

    def test_claim_exp_ausente_rechazado(self):
        payload = self._exp_payload()
        del payload["exp"]
        token = jwt_lib.encode(payload, SECRET_KEY, algorithm="HS256")
        self.assertEqual(self._get_with(token).status_code, 401)

    def test_token_valido_aceptado(self):
        self.assertEqual(self._get_with(self.token).status_code, 200)


class TestWebSocketSecurity(BaseSecTest):

    def test_sin_token_rechazado(self):
        self.assertFalse(self._ws().is_connected())

    def test_token_invalido_rechazado(self):
        self.assertFalse(self._ws(auth={"token": "token-falso"}).is_connected())

    def test_token_firma_incorrecta_rechazado(self):
        forged = jwt_lib.encode(self._exp_payload(), "otro-secreto", algorithm="HS256")
        self.assertFalse(self._ws(auth={"token": forged}).is_connected())

    def test_token_expirado_rechazado(self):
        now = dt.datetime.now(dt.timezone.utc)
        expired = jwt_lib.encode(self._exp_payload(
            iat=now - dt.timedelta(hours=25),
            exp=now - dt.timedelta(hours=1),
        ), SECRET_KEY, algorithm="HS256")
        self.assertFalse(self._ws(auth={"token": expired}).is_connected())

    def test_token_sin_claim_user_id_rechazado(self):
        payload = self._exp_payload()
        del payload["user_id"]
        token = jwt_lib.encode(payload, SECRET_KEY, algorithm="HS256")
        self.assertFalse(self._ws(auth={"token": token}).is_connected())

    def test_token_valido_aceptado(self):
        self.assertTrue(self._ws(auth={"token": self.token}).is_connected())

    def test_token_por_query_string_aceptado(self):
        self.assertTrue(self._ws(query_string=f"token={self.token}").is_connected())

    def test_token_por_header_aceptado(self):
        c = self._ws(headers={"Authorization": f"Bearer {self.token}"})
        self.assertTrue(c.is_connected())

    def test_desconexion_limpia_registro(self):
        from api.ws import get_client_count
        c = self._ws(auth={"token": self.token})
        self.assertEqual(get_client_count(), 1)
        c.disconnect()
        self.assertEqual(get_client_count(), 0)


class TestStress(BaseSecTest):

    def test_conexiones_ws_masivas(self):
        n = 30
        clients = [self._ws(auth={"token": self.token}) for _ in range(n)]
        self.assertTrue(all(c.is_connected() for c in clients))

        from api.ws import get_client_count
        self.assertEqual(get_client_count(), n)

        for c in clients:
            c.disconnect()
        self.assertEqual(get_client_count(), 0)

    def test_broadcast_a_muchos_clientes(self):
        n = 20
        clients = [self._ws(auth={"token": self.token}) for _ in range(n)]
        for c in clients:
            c.get_received()

        r = self.client.post("/api/telemetry", json={
            "device_id": self._device_id(),
            "point_wkt": "POINT(-70.5 -33.4)",
            "speed_kmh": 33.0,
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201)

        recibidos = [c.get_received() for c in clients]
        for i, msgs in enumerate(recibidos):
            self.assertTrue(any(m["name"] == "telemetry_update" for m in msgs),
                            f"Cliente {i} no recibió broadcast")

    def test_carga_secuencial_endpoint_protegido(self):
        for _ in range(50):
            self.assertEqual(
                self.client.get("/api/vehicles", headers=self.auth_headers).status_code, 200)

    def test_carga_concurrente_tokens_invalidos(self):
        def hit(_):
            c = app.test_client()
            c.testing = True
            return c.get("/api/vehicles",
                         headers={"Authorization": "Bearer token-falso"}).status_code

        with ThreadPoolExecutor(max_workers=8) as pool:
            codes = list(pool.map(hit, range(64)))
        self.assertTrue(all(code == 401 for code in codes))

    def test_throughput_jwt_encode_decode(self):
        n = 500
        inicio = time.perf_counter()
        for i in range(n):
            token = jwt_lib.encode(self._exp_payload(user_id=f"u-{i}"), SECRET_KEY,
                                   algorithm="HS256")
            payload = decode_token(token)
            self.assertEqual(payload["user_id"], f"u-{i}")
        duracion = time.perf_counter() - inicio
        self.assertLess(duracion, 5.0, f"{n} encode/decode tardaron {duracion:.2f}s")

    def _device_id(self):
        r2 = self.client.post("/api/users", json={
            "rut": "12.345.678-5", "full_name": "Juan", "email": "j@test.cl",
        })
        uid = r2.get_json()["user_id"]
        r3 = self.client.post(f"/api/users/{uid}/vehicles",
                              json={"license_plate": "ABCD12"}, headers=self.auth_headers)
        vid = r3.get_json()["vehicle_id"]
        r4 = self.client.post(f"/api/vehicles/{vid}/gps",
                              json={"imei": "123456789012345", "is_online": True},
                              headers=self.auth_headers)
        return r4.get_json()["device_id"]


if __name__ == "__main__":
    unittest.main()
