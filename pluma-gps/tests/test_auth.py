"""Tests de autenticación JWT: register, login, acceso protegido."""
import unittest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conectar import crear_conexion
from dao.dao import Dao
from api.app import app
from api.auth import decode_token, SECRET_KEY
import jwt as jwt_lib


class BaseAuthTest(unittest.TestCase):

    def setUp(self):
        _, self.db_path = tempfile.mkstemp(suffix=".db")
        from api import app as app_module
        app_module.DB_PATH = self.db_path
        conn = crear_conexion(self.db_path)
        Dao(conn).crear_todas_las_tablas()
        conn.close()
        self.client = app.test_client()
        self.client.testing = True

    def tearDown(self):
        import gc
        gc.collect()
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except PermissionError:
            pass

    def _register(self, rut="18.629.694-K", password="secret123",
                  email="auth@test.cl", plan="ENTERPRISE_FLEET"):
        return self.client.post("/api/auth/register", json={
            "rut": rut, "full_name": "Test User",
            "email": email, "password": password, "plan": plan,
        })

    def _login(self, rut="18.629.694-K", password="secret123"):
        return self.client.post("/api/auth/login", json={
            "rut": rut, "password": password,
        })


class TestRegister(BaseAuthTest):

    def test_register_ok(self):
        r = self._register()
        self.assertEqual(r.status_code, 201)
        data = r.get_json()
        self.assertIn("token", data)
        self.assertIn("user_id", data)
        self.assertEqual(data["rut"], "18.629.694-K")

    def test_register_rut_invalido_400(self):
        r = self._register(rut="12.345.678-0")
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.get_json())

    def test_register_password_corta_400(self):
        r = self._register(password="123")
        self.assertEqual(r.status_code, 400)
        self.assertIn("contraseña", r.get_json()["error"])

    def test_register_falta_password_400(self):
        r = self.client.post("/api/auth/register", json={
            "rut": "18.629.694-K", "full_name": "X",
            "email": "x@test.cl", "plan": "FREE_ADS",
        })
        self.assertEqual(r.status_code, 400)

    def test_register_rut_duplicado_400(self):
        self._register()
        r = self._register(email="otro@test.cl")
        self.assertEqual(r.status_code, 400)

    def test_register_token_contiene_payload(self):
        r = self._register()
        token = r.get_json()["token"]
        payload = decode_token(token)
        self.assertEqual(payload["rut"], "18.629.694-K")
        self.assertEqual(payload["plan"], "ENTERPRISE_FLEET")
        self.assertIn("user_id", payload)
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)


class TestLogin(BaseAuthTest):

    def setUp(self):
        super().setUp()
        self._register()

    def test_login_ok(self):
        r = self._login()
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("token", data)
        self.assertEqual(data["rut"], "18.629.694-K")
        self.assertEqual(data["plan"], "ENTERPRISE_FLEET")

    def test_login_password_incorrecto_401(self):
        r = self._login(password="wrongpass")
        self.assertEqual(r.status_code, 401)
        self.assertIn("Credenciales", r.get_json()["error"])

    def test_login_rut_inexistente_401(self):
        r = self._login(rut="12.345.678-5")
        self.assertEqual(r.status_code, 401)

    def test_login_falta_campo_400(self):
        r = self.client.post("/api/auth/login", json={
            "rut": "18.629.694-K",
        })
        self.assertEqual(r.status_code, 400)

    def test_login_sin_datos_400(self):
        r = self.client.post("/api/auth/login", json={})
        self.assertEqual(r.status_code, 400)

    def test_login_token_valido_despues_de_register(self):
        r_reg = self._register(rut="10.000.000-8", email="test2@test.cl", password="pass123")
        token_reg = r_reg.get_json()["token"]
        r_login = self._login(rut="10.000.000-8", password="pass123")
        token_login = r_login.get_json()["token"]
        # Ambos tokens deben ser decodificables
        p1 = decode_token(token_reg)
        p2 = decode_token(token_login)
        self.assertEqual(p1["user_id"], p2["user_id"])


class TestProteccionEndpoints(BaseAuthTest):

    def setUp(self):
        super().setUp()
        # Registrar usuario auth y obtener token
        r = self._register()
        self.valid_token = r.get_json()["token"]
        self.auth_headers = {"Authorization": f"Bearer {self.valid_token}"}
        # Crear usuario de negocio (sin password, via endpoint público)
        r2 = self.client.post("/api/users", json={
            "rut": "12.345.678-5", "full_name": "Juan", "email": "j@test.cl",
        })
        self.user_id = r2.get_json()["user_id"]

    def test_vehicles_sin_token_401(self):
        r = self.client.get("/api/vehicles")
        self.assertEqual(r.status_code, 401)

    def test_vehicles_token_invalido_401(self):
        r = self.client.get("/api/vehicles",
                            headers={"Authorization": "Bearer token-falso"})
        self.assertEqual(r.status_code, 401)

    def test_vehicles_sin_bearer_401(self):
        r = self.client.get("/api/vehicles",
                            headers={"Authorization": self.valid_token})
        self.assertEqual(r.status_code, 401)

    def test_vehicles_con_token_ok(self):
        r = self.client.get("/api/vehicles", headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)

    def test_telemetry_sin_token_401(self):
        r = self.client.get("/api/telemetry")
        self.assertEqual(r.status_code, 401)

    def test_commands_sin_token_401(self):
        r = self.client.get("/api/commands")
        self.assertEqual(r.status_code, 401)

    def test_commands_con_token_ok(self):
        r = self.client.get("/api/commands", headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)

    def test_create_vehicle_sin_token_401(self):
        r = self.client.post(f"/api/users/{self.user_id}/vehicles", json={
            "license_plate": "ABCD12",
        })
        self.assertEqual(r.status_code, 401)

    def test_create_vehicle_con_token_ok(self):
        r = self.client.post(f"/api/users/{self.user_id}/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201)

    def test_health_publico_sin_token_200(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)

    def test_users_publico_sin_token_200(self):
        r = self.client.get("/api/users")
        self.assertEqual(r.status_code, 200)

    def test_token_expirado_401(self):
        # Crear token expirado manualmente
        import datetime as dt
        payload = {
            "user_id": "fake",
            "rut": "18.629.694-K",
            "plan": "ENTERPRISE_FLEET",
            "iat": dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=25),
            "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
        }
        expired_token = jwt_lib.encode(payload, SECRET_KEY, algorithm="HS256")
        r = self.client.get("/api/vehicles",
                            headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(r.status_code, 401)
        self.assertIn("expirado", r.get_json()["error"])


class TestPasswordHashing(unittest.TestCase):

    def test_hash_y_verify(self):
        from model.user import User
        from model.enums import PlanSubscription
        u = User(rut="18.629.694-K", full_name="Test", email="t@test.cl")
        u.set_password("mypass123")
        self.assertNotEqual(u.password_hash, "mypass123")
        self.assertTrue(u.verify_password("mypass123"))
        self.assertFalse(u.verify_password("wrongpass"))

    def test_password_corta_error(self):
        from model.user import User
        u = User(rut="18.629.694-K", full_name="Test", email="t@test.cl")
        with self.assertRaises(ValueError):
            u.set_password("123")

    def test_verify_sin_hash(self):
        from model.user import User
        u = User(rut="18.629.694-K", full_name="Test", email="t@test.cl")
        self.assertFalse(u.verify_password("anything"))

    def test_hashes_son_diferentes(self):
        from model.user import User
        u1 = User(rut="18.629.694-K", full_name="A", email="a@test.cl")
        u1.set_password("mypass123")
        u2 = User(rut="10.000.000-8", full_name="B", email="b@test.cl")
        u2.set_password("mypass123")
        # bcrypt usa salt aleatorio → hashes diferentes
        self.assertNotEqual(u1.password_hash, u2.password_hash)
        self.assertTrue(u1.verify_password("mypass123"))
        self.assertTrue(u2.verify_password("mypass123"))


if __name__ == "__main__":
    unittest.main()
