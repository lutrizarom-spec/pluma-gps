import unittest
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conectar import crear_conexion
from dao.dao import Dao
from dao.user_dao import UserDao
from dao.vehicle_dao import VehicleDao
from dao.gps_device_dao import GpsDeviceDao
from dao.telemetry_dao import TelemetryDao
from dao.command_dao import CutEngineCommandDao

from model.enums import PlanSubscription, HardwareLevel
from model.user import User
from model.vehicle import Vehicle
from model.gps_device import GpsDevice
from model.telemetry_log import TelemetryLog
from model.cut_engine_command import CutEngineCommand

from api.app import app


class BaseApiTest(unittest.TestCase):

    def setUp(self):
        _, self.db_path = tempfile.mkstemp(suffix=".db")
        from api import app as app_module
        app_module.DB_PATH = self.db_path
        conn = crear_conexion(self.db_path)
        Dao(conn).crear_todas_las_tablas()
        conn.close()
        self.client = app.test_client()
        self.client.testing = True

        # Registrar usuario de auth para obtener token
        r = self.client.post("/api/auth/register", json={
            "rut": "18.629.694-K",
            "full_name": "Auth User",
            "email": "auth@test.cl",
            "password": "secret123",
            "plan": "ENTERPRISE_FLEET",
        })
        self.auth_token = r.get_json().get("token", "")
        self.auth_headers = {"Authorization": f"Bearer {self.auth_token}"}

    def tearDown(self):
        import gc
        gc.collect()
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except PermissionError:
            pass


class TestHealth(BaseApiTest):

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "ok")


# ==================== USERS ====================

class TestUsersApi(BaseApiTest):

    def test_create_user_ok(self):
        r = self.client.post("/api/users", json={
            "rut": "12.345.678-5",
            "full_name": "Juan Pérez",
            "email": "jp@test.cl",
            "plan": "PRO_MONTHLY",
        })
        self.assertEqual(r.status_code, 201)
        data = r.get_json()
        self.assertIn("user_id", data)

    def test_create_user_rut_invalido_400(self):
        r = self.client.post("/api/users", json={
            "rut": "12.345.678-0",
            "full_name": "X",
            "email": "x@test.cl",
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.get_json())

    def test_create_user_rut_vacio_400(self):
        r = self.client.post("/api/users", json={
            "rut": "",
            "full_name": "X",
            "email": "x@test.cl",
        })
        self.assertEqual(r.status_code, 400)

    def test_create_user_falta_campo_400(self):
        r = self.client.post("/api/users", json={
            "rut": "12.345.678-5",
        })
        self.assertEqual(r.status_code, 400)

    def test_create_user_rut_duplicado_400(self):
        self.client.post("/api/users", json={
            "rut": "12.345.678-5",
            "full_name": "Juan",
            "email": "j@test.cl",
        })
        r = self.client.post("/api/users", json={
            "rut": "12.345.678-5",
            "full_name": "Otro",
            "email": "o@test.cl",
        })
        self.assertEqual(r.status_code, 400)

    def test_get_user_ok(self):
        r = self.client.post("/api/users", json={
            "rut": "12.345.678-5", "full_name": "Juan", "email": "j@test.cl",
        })
        uid = r.get_json()["user_id"]
        r2 = self.client.get(f"/api/users/{uid}")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["rut"], "12.345.678-5")

    def test_get_user_404(self):
        r = self.client.get("/api/users/no-existe")
        self.assertEqual(r.status_code, 404)

    def test_list_users(self):
        self.client.post("/api/users", json={
            "rut": "12.345.678-5", "full_name": "A", "email": "a@test.cl",
        })
        r = self.client.get("/api/users")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.get_json()), 1)


# ==================== VEHICLES ====================

class TestVehiclesApi(BaseApiTest):

    def setUp(self):
        super().setUp()
        r = self.client.post("/api/users", json={
            "rut": "12.345.678-5", "full_name": "Juan", "email": "j@test.cl",
            "plan": "FREE_ADS",
        })
        self.user_id = r.get_json()["user_id"]

    def test_create_vehicle_ok(self):
        r = self.client.post(f"/api/users/{self.user_id}/vehicles", json={
            "license_plate": "ABCD12", "brand": "Toyota", "model": "Hilux",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201)
        self.assertIn("vehicle_id", r.get_json())

    def test_create_vehicle_patente_corta_400(self):
        r = self.client.post(f"/api/users/{self.user_id}/vehicles", json={
            "license_plate": "AB",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 400)

    def test_create_vehicle_user_404(self):
        r = self.client.post("/api/users/no-existe/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 404)

    def test_create_vehicle_plan_limit_400(self):
        self.client.post(f"/api/users/{self.user_id}/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        r = self.client.post(f"/api/users/{self.user_id}/vehicles", json={
            "license_plate": "EFGH34",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 400)
        self.assertIn("máximo", r.get_json()["error"])

    def test_create_vehicle_pro_plan_multiple(self):
        r = self.client.post("/api/users", json={
            "rut": "15.463.278-6", "full_name": "Pro", "email": "p@test.cl",
            "plan": "PRO_MONTHLY",
        })
        pro_id = r.get_json()["user_id"]
        for i in range(5):
            r = self.client.post(f"/api/users/{pro_id}/vehicles", json={
                "license_plate": f"PRO{i:04d}",
            }, headers=self.auth_headers)
            self.assertEqual(r.status_code, 201, f"Vehicle {i} failed")
        r = self.client.post(f"/api/users/{pro_id}/vehicles", json={
            "license_plate": "PRO0005",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 400)

    def test_get_vehicle_ok(self):
        r = self.client.post(f"/api/users/{self.user_id}/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        vid = r.get_json()["vehicle_id"]
        r2 = self.client.get(f"/api/vehicles/{vid}", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 200)

    def test_get_vehicle_404(self):
        r = self.client.get("/api/vehicles/no-existe", headers=self.auth_headers)
        self.assertEqual(r.status_code, 404)

    def test_list_vehicles(self):
        self.client.post(f"/api/users/{self.user_id}/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        r = self.client.get("/api/vehicles", headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.get_json()), 1)

    def test_list_vehicles_by_user(self):
        self.client.post(f"/api/users/{self.user_id}/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        r = self.client.get(f"/api/vehicles?user_id={self.user_id}", headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(len(data), 1)


# ==================== GPS DEVICES ====================

class TestGpsApi(BaseApiTest):

    def setUp(self):
        super().setUp()
        r = self.client.post("/api/users", json={
            "rut": "12.345.678-5", "full_name": "Juan", "email": "j@test.cl",
        })
        uid = r.get_json()["user_id"]
        r2 = self.client.post(f"/api/users/{uid}/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        self.vehicle_id = r2.get_json()["vehicle_id"]

    def test_assign_gps_ok(self):
        r = self.client.post(f"/api/vehicles/{self.vehicle_id}/gps", json={
            "imei": "123456789012345", "hardware_model": "Coban TK103",
            "level": "LEVEL_1_BASIC", "is_online": True,
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201)
        self.assertIn("device_id", r.get_json())

    def test_assign_gps_imei_corto_400(self):
        r = self.client.post(f"/api/vehicles/{self.vehicle_id}/gps", json={
            "imei": "123",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 400)

    def test_assign_gps_vehicle_404(self):
        r = self.client.post("/api/vehicles/no-existe/gps", json={
            "imei": "123456789012345",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 404)

    def test_get_gps_ok(self):
        r = self.client.post(f"/api/vehicles/{self.vehicle_id}/gps", json={
            "imei": "123456789012345", "is_online": True,
        }, headers=self.auth_headers)
        did = r.get_json()["device_id"]
        r2 = self.client.get(f"/api/gps-devices/{did}", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["imei"], "123456789012345")

    def test_get_gps_404(self):
        r = self.client.get("/api/gps-devices/no-existe", headers=self.auth_headers)
        self.assertEqual(r.status_code, 404)


# ==================== TELEMETRY ====================

class TestTelemetryApi(BaseApiTest):

    def setUp(self):
        super().setUp()
        r = self.client.post("/api/users", json={
            "rut": "12.345.678-5", "full_name": "Juan", "email": "j@test.cl",
        })
        uid = r.get_json()["user_id"]
        r2 = self.client.post(f"/api/users/{uid}/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        vid = r2.get_json()["vehicle_id"]
        r3 = self.client.post(f"/api/vehicles/{vid}/gps", json={
            "imei": "123456789012345", "is_online": True,
        }, headers=self.auth_headers)
        self.device_id = r3.get_json()["device_id"]

    def test_create_telemetry_ok(self):
        r = self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(-70.55 -33.45)",
            "speed_kmh": 15.0,
            "acc_ignition": True,
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201)
        self.assertIn("telemetry_id", r.get_json())

    def test_create_telemetry_device_404(self):
        r = self.client.post("/api/telemetry", json={
            "device_id": "no-existe",
            "point_wkt": "POINT(1 1)",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 404)

    def test_create_telemetry_wkt_invalido_400(self):
        r = self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "LINESTRING(1 2, 3 4)",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 400)

    def test_list_telemetry(self):
        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(-70.5 -33.4)",
            "speed_kmh": 45.0,
        }, headers=self.auth_headers)
        r = self.client.get(f"/api/telemetry?device_id={self.device_id}", headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.get_json()), 1)


# ==================== COMMANDS ====================

class TestCommandsApi(BaseApiTest):

    def setUp(self):
        super().setUp()
        r = self.client.post("/api/users", json={
            "rut": "12.345.678-5", "full_name": "Juan", "email": "j@test.cl",
        })
        uid = r.get_json()["user_id"]
        r2 = self.client.post(f"/api/users/{uid}/vehicles", json={
            "license_plate": "ABCD12",
        }, headers=self.auth_headers)
        vid = r2.get_json()["vehicle_id"]
        r3 = self.client.post(f"/api/vehicles/{vid}/gps", json={
            "imei": "123456789012345", "is_online": True,
        }, headers=self.auth_headers)
        self.device_id = r3.get_json()["device_id"]

    def test_create_command_ok(self):
        r = self.client.post("/api/commands", json={
            "device_id": self.device_id,
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201)
        data = r.get_json()
        self.assertEqual(data["status"], "PENDING_SPEED_CHECK")

    def test_create_command_device_404(self):
        r = self.client.post("/api/commands", json={
            "device_id": "no-existe",
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 404)

    def test_get_command_ok(self):
        r = self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        cid = r.get_json()["command_id"]
        r2 = self.client.get(f"/api/commands/{cid}", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 200)

    def test_get_command_404(self):
        r = self.client.get("/api/commands/no-existe", headers=self.auth_headers)
        self.assertEqual(r.status_code, 404)

    def test_execute_command_speed_safe_ok(self):
        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(1 1)",
            "speed_kmh": 15.0,
        }, headers=self.auth_headers)
        r = self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        cid = r.get_json()["command_id"]
        r2 = self.client.patch(f"/api/commands/{cid}/execute", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["status"], "EXECUTED")

    def test_execute_command_speed_excede_400(self):
        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(1 1)",
            "speed_kmh": 80.0,
        }, headers=self.auth_headers)
        r = self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        cid = r.get_json()["command_id"]
        r2 = self.client.patch(f"/api/commands/{cid}/execute", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 400)
        self.assertIn("excede", r2.get_json()["error"])

    def test_execute_command_no_telemetria_400(self):
        r = self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        cid = r.get_json()["command_id"]
        r2 = self.client.patch(f"/api/commands/{cid}/execute", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 400)

    def test_execute_command_ya_ejecutado_400(self):
        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(1 1)",
            "speed_kmh": 10.0,
        }, headers=self.auth_headers)
        r = self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        cid = r.get_json()["command_id"]
        self.client.patch(f"/api/commands/{cid}/execute", headers=self.auth_headers)
        r2 = self.client.patch(f"/api/commands/{cid}/execute", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 400)

    def test_cancel_command_ok(self):
        r = self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        cid = r.get_json()["command_id"]
        r2 = self.client.patch(f"/api/commands/{cid}/cancel", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["status"], "CANCELLED_SAFETY")

    def test_cancel_command_ya_ejecutado_400(self):
        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(1 1)",
            "speed_kmh": 10.0,
        }, headers=self.auth_headers)
        r = self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        cid = r.get_json()["command_id"]
        self.client.patch(f"/api/commands/{cid}/execute", headers=self.auth_headers)
        r2 = self.client.patch(f"/api/commands/{cid}/cancel", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 400)

    def test_cancel_command_404(self):
        r = self.client.patch("/api/commands/no-existe/cancel", headers=self.auth_headers)
        self.assertEqual(r.status_code, 404)

    def test_list_commands(self):
        self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        r = self.client.get("/api/commands", headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.get_json()), 1)

    def test_list_commands_by_device(self):
        self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        r = self.client.get(f"/api/commands?device_id={self.device_id}", headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.get_json()), 1)

    def test_list_commands_by_status(self):
        self.client.post("/api/commands", json={"device_id": self.device_id}, headers=self.auth_headers)
        r = self.client.get("/api/commands?status=PENDING_SPEED_CHECK", headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.get_json()), 1)


if __name__ == "__main__":
    unittest.main()
