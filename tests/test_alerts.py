"""Tests: Alert entity, AlertDao, overspeed/geofence detection, API endpoints, WebSocket broadcast."""
import unittest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conectar import crear_conexion
from dao.dao import Dao
from dao.alert_dao import AlertDao
from dao.user_dao import UserDao
from dao.vehicle_dao import VehicleDao
from dao.gps_device_dao import GpsDeviceDao
from dao.geofence_dao import GeofenceDao
from model.alert import Alert, AlertType, AlertStatus
from model.enums import PlanSubscription, HardwareLevel
from model.user import User
from model.vehicle import Vehicle
from model.gps_device import GpsDevice
from model.geofence import Geofence
from api.app import app
from api.auth import generate_token


class TestAlertModel(unittest.TestCase):

    def test_create_alert(self):
        a = Alert(device_id="d1", alert_type=AlertType.OVERSPEED,
                  message="Exceso: 120 km/h")
        self.assertEqual(a.type, AlertType.OVERSPEED)
        self.assertEqual(a.status, AlertStatus.ACTIVE)
        self.assertEqual(len(a.alert_id), 36)

    def test_acknowledge(self):
        a = Alert(device_id="d1", alert_type=AlertType.OVERSPEED, message="X")
        a.acknowledge()
        self.assertEqual(a.status, AlertStatus.ACKNOWLEDGED)

    def test_acknowledge_doble_error(self):
        a = Alert(device_id="d1", alert_type=AlertType.OVERSPEED, message="X")
        a.acknowledge()
        with self.assertRaises(ValueError):
            a.acknowledge()

    def test_evaluate_overspeed_detected(self):
        a = Alert.evaluate_overspeed("d1", 150.0)
        self.assertIsNotNone(a)
        self.assertEqual(a.type, AlertType.OVERSPEED)
        self.assertIn("150.0", a.message)

    def test_evaluate_overspeed_ok(self):
        a = Alert.evaluate_overspeed("d1", 80.0)
        self.assertIsNone(a)

    def test_evaluate_overspeed_custom_limit(self):
        a = Alert.evaluate_overspeed("d1", 55.0, limit=50.0)
        self.assertIsNotNone(a)

    def test_evaluate_geofence_exit(self):
        gf = Geofence(vehicle_id="v1", name="Casa",
                      area_wkt="POLYGON((-70.6 -33.4, -70.5 -33.4, -70.5 -33.5, -70.6 -33.5, -70.6 -33.4))")
        alerts = Alert.evaluate_geofence("d1", "v1", "POINT(-70.0 -33.0)",
                                         [{"geofence": gf, "was_inside": True}])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, AlertType.GEOFENCE_EXIT)

    def test_evaluate_geofence_enter(self):
        gf = Geofence(vehicle_id="v1", name="Casa",
                      area_wkt="POLYGON((-70.6 -33.4, -70.5 -33.4, -70.5 -33.5, -70.6 -33.5, -70.6 -33.4))")
        alerts = Alert.evaluate_geofence("d1", "v1", "POINT(-70.55 -33.45)",
                                         [{"geofence": gf, "was_inside": False}])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, AlertType.GEOFENCE_ENTER)

    def test_evaluate_geofence_no_change(self):
        gf = Geofence(vehicle_id="v1", name="Casa",
                      area_wkt="POLYGON((-70.6 -33.4, -70.5 -33.4, -70.5 -33.5, -70.6 -33.5, -70.6 -33.4))")
        alerts = Alert.evaluate_geofence("d1", "v1", "POINT(-70.55 -33.45)",
                                         [{"geofence": gf, "was_inside": True}])
        self.assertEqual(len(alerts), 0)

    def test_evaluate_geofence_no_prev(self):
        gf = Geofence(vehicle_id="v1", name="Casa",
                      area_wkt="POLYGON((1 1, 2 1, 2 2, 1 2, 1 1))")
        alerts = Alert.evaluate_geofence("d1", "v1", "POINT(1.5 1.5)",
                                         [{"geofence": gf}])
        self.assertEqual(len(alerts), 0)


class TestAlertDao(unittest.TestCase):

    def setUp(self):
        _, self.path = tempfile.mkstemp(suffix=".db")
        self.conn = crear_conexion(self.path)
        Dao(self.conn).crear_todas_las_tablas()
        # Setup FK chain
        u_dao = UserDao(self.conn)
        v_dao = VehicleDao(self.conn)
        g_dao = GpsDeviceDao(self.conn)
        user = User(rut="18.629.694-K", full_name="T", email="t@test.cl")
        u_dao.insertar(user)
        veh = Vehicle(user_id=user.user_id, license_plate="ABCD12")
        v_dao.insertar(veh)
        dev = GpsDevice(vehicle_id=veh.vehicle_id, imei="123456789012345")
        g_dao.insertar(dev)
        self.device_id = dev.device_id
        self.dao = AlertDao(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_insertar_y_buscar(self):
        a = Alert(device_id=self.device_id, alert_type=AlertType.OVERSPEED,
                  message="Exceso")
        aid = self.dao.insertar(a)
        row = self.dao.buscar_por_id(aid)
        self.assertIsNotNone(row)
        self.assertEqual(row[2], "OVERSPEED")

    def test_listar_filtro_status(self):
        a1 = Alert(device_id=self.device_id, alert_type=AlertType.OVERSPEED, message="A1")
        self.dao.insertar(a1)
        rows = self.dao.listar(status="ACTIVE")
        self.assertGreaterEqual(len(rows), 1)

    def test_acknowledge(self):
        a = Alert(device_id=self.device_id, alert_type=AlertType.OVERSPEED, message="A")
        aid = self.dao.insertar(a)
        self.dao.acknowledge(aid)
        row = self.dao.buscar_por_id(aid)
        self.assertEqual(row[4], "ACKNOWLEDGED")


class BaseApiAlertTest(unittest.TestCase):

    def setUp(self):
        _, self.db_path = tempfile.mkstemp(suffix=".db")
        from api import app as app_module
        app_module.DB_PATH = self.db_path
        conn = crear_conexion(self.db_path)
        Dao(conn).crear_todas_las_tablas()
        conn.close()
        self.client = app.test_client()
        self.client.testing = True

        # Auth user
        r = self.client.post("/api/auth/register", json={
            "rut": "18.629.694-K", "full_name": "Auth", "email": "auth@test.cl",
            "password": "secret123", "plan": "ENTERPRISE_FLEET",
        })
        self.auth_token = r.get_json()["token"]
        self.auth_headers = {"Authorization": f"Bearer {self.auth_token}"}

        # Business user + vehicle + gps
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
        self.vehicle_id = vid

    def tearDown(self):
        import gc
        gc.collect()
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except PermissionError:
            pass


class TestAlertsApi(BaseApiAlertTest):

    def test_overspeed_creates_alert(self):
        r = self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(-70.5 -33.4)",
            "speed_kmh": 150.0,
        }, headers=self.auth_headers)
        self.assertEqual(r.status_code, 201)

        r2 = self.client.get("/api/alerts", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 200)
        alerts = r2.get_json()
        overspeed = [a for a in alerts if a["type"] == "OVERSPEED"]
        self.assertGreaterEqual(len(overspeed), 1)

    def test_no_overspeed_no_alert(self):
        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(-70.5 -33.4)",
            "speed_kmh": 50.0,
        }, headers=self.auth_headers)
        r = self.client.get("/api/alerts?type=OVERSPEED", headers=self.auth_headers)
        self.assertEqual(len(r.get_json()), 0)

    def test_list_alerts_filter_device(self):
        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(1 1)", "speed_kmh": 120.0,
        }, headers=self.auth_headers)
        r = self.client.get(f"/api/alerts?device_id={self.device_id}", headers=self.auth_headers)
        self.assertGreaterEqual(len(r.get_json()), 1)

    def test_ack_alert_ok(self):
        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(1 1)", "speed_kmh": 120.0,
        }, headers=self.auth_headers)
        r = self.client.get("/api/alerts?status=ACTIVE", headers=self.auth_headers)
        aid = r.get_json()[0]["alert_id"]
        r2 = self.client.patch(f"/api/alerts/{aid}/ack", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["status"], "ACKNOWLEDGED")

    def test_ack_alert_404(self):
        r = self.client.patch("/api/alerts/no-existe/ack", headers=self.auth_headers)
        self.assertEqual(r.status_code, 404)

    def test_ack_alert_already_400(self):
        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(1 1)", "speed_kmh": 120.0,
        }, headers=self.auth_headers)
        r = self.client.get("/api/alerts?status=ACTIVE", headers=self.auth_headers)
        aid = r.get_json()[0]["alert_id"]
        self.client.patch(f"/api/alerts/{aid}/ack", headers=self.auth_headers)
        r2 = self.client.patch(f"/api/alerts/{aid}/ack", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 400)

    def test_alerts_sin_token_401(self):
        r = self.client.get("/api/alerts")
        self.assertEqual(r.status_code, 401)


class TestAlertWebSocket(BaseApiAlertTest):

    def test_overspeed_broadcast_ws(self):
        from api.ws import socketio
        sio = socketio.test_client(app, auth={"token": self.auth_token})
        sio.get_received()

        self.client.post("/api/telemetry", json={
            "device_id": self.device_id,
            "point_wkt": "POINT(1 1)", "speed_kmh": 150.0,
        }, headers=self.auth_headers)

        received = sio.get_received()
        # At least telemetry_update + alert_update
        events = [m["name"] for m in received]
        self.assertIn("telemetry_update", events)
        self.assertIn("alert_update", events)

        alert_msgs = [m for m in received if m["name"] == "alert_update"]
        self.assertGreaterEqual(len(alert_msgs), 1)
        self.assertEqual(alert_msgs[0]["args"][0]["type"], "OVERSPEED")
        sio.disconnect()


if __name__ == "__main__":
    unittest.main()
