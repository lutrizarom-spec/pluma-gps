import unittest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conectar import crear_conexion
from dao.dao import Dao
from dao.user_dao import UserDao
from dao.vehicle_dao import VehicleDao
from dao.gps_device_dao import GpsDeviceDao
from dao.geofence_dao import GeofenceDao
from dao.telemetry_dao import TelemetryDao
from dao.command_dao import CutEngineCommandDao

from model.enums import PlanSubscription, HardwareLevel, CommandStatus
from model.user import User
from model.vehicle import Vehicle
from model.gps_device import GpsDevice
from model.geofence import Geofence
from model.telemetry_log import TelemetryLog
from model.cut_engine_command import CutEngineCommand


class TestDaoBase(unittest.TestCase):

    def test_crear_todas_las_tablas(self):
        _, path = tempfile.mkstemp(suffix=".db")
        conn = crear_conexion(path)
        Dao(conn).crear_todas_las_tablas()
        tablas = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        esperadas = ["users", "vehicles", "gps_devices", "geofences", "telemetry_logs", "cut_engine_commands"]
        for t in esperadas:
            self.assertIn(t, tablas, f"Falta tabla: {t}")
        conn.close()


class TestUserDao(unittest.TestCase):

    def setUp(self):
        _, self.path = tempfile.mkstemp(suffix=".db")
        self.conn = crear_conexion(self.path)
        Dao(self.conn).crear_todas_las_tablas()
        self.dao = UserDao(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_insertar_y_buscar(self):
        u = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl",
                 plan=PlanSubscription.PRO_MONTHLY)
        uid = self.dao.insertar(u)
        row = self.dao.buscar_por_id(uid)
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "12.345.678-5")
        self.assertEqual(row[3], "j@test.cl")
        self.assertEqual(row[4], "PRO_MONTHLY")

    def test_rut_unique(self):
        u1 = User(rut="12.345.678-5", full_name="A", email="a@test.cl")
        self.dao.insertar(u1)
        u2 = User(rut="12.345.678-5", full_name="B", email="b@test.cl")
        with self.assertRaises(Exception):
            self.dao.insertar(u2)


class TestVehicleDao(unittest.TestCase):

    def setUp(self):
        _, self.path = tempfile.mkstemp(suffix=".db")
        self.conn = crear_conexion(self.path)
        Dao(self.conn).crear_todas_las_tablas()
        self.u_dao = UserDao(self.conn)
        self.v_dao = VehicleDao(self.conn)
        self.user = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        self.u_dao.insertar(self.user)

    def tearDown(self):
        self.conn.close()

    def test_insertar_y_buscar(self):
        v = Vehicle(user_id=self.user.user_id, license_plate="ABCD12",
                    brand="Toyota", model="Hilux", manufacture_year=2024)
        vid = self.v_dao.insertar(v)
        row = self.v_dao.buscar_por_id(vid)
        self.assertIsNotNone(row)
        self.assertEqual(row[2], "ABCD12")

    def test_buscar_por_patente(self):
        v = Vehicle(user_id=self.user.user_id, license_plate="XYZ999")
        self.v_dao.insertar(v)
        row = self.v_dao.buscar_por_patente("XYZ999")
        self.assertIsNotNone(row)

    def test_fk_usuario_inexistente(self):
        v = Vehicle(user_id="no-existe", license_plate="AAAA11")
        with self.assertRaises(Exception):
            self.v_dao.insertar(v)


class TestGpsDeviceDao(unittest.TestCase):

    def setUp(self):
        _, self.path = tempfile.mkstemp(suffix=".db")
        self.conn = crear_conexion(self.path)
        Dao(self.conn).crear_todas_las_tablas()
        u_dao = UserDao(self.conn)
        v_dao = VehicleDao(self.conn)
        self.g_dao = GpsDeviceDao(self.conn)
        user = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        u_dao.insertar(user)
        self.veh = Vehicle(user_id=user.user_id, license_plate="ABCD12")
        v_dao.insertar(self.veh)

    def tearDown(self):
        self.conn.close()

    def test_insertar_y_buscar(self):
        d = GpsDevice(vehicle_id=self.veh.vehicle_id, imei="123456789012345",
                      hardware_model="Suntech ST4315", level=HardwareLevel.LEVEL_2_ADVANCED)
        did = self.g_dao.insertar(d)
        row = self.g_dao.buscar_por_id(did)
        self.assertIsNotNone(row)
        self.assertEqual(row[2], "123456789012345")
        self.assertEqual(row[4], "LEVEL_2_ADVANCED")

    def test_imei_unique(self):
        d1 = GpsDevice(vehicle_id=self.veh.vehicle_id, imei="123456789012345")
        self.g_dao.insertar(d1)
        d2 = GpsDevice(vehicle_id=self.veh.vehicle_id, imei="123456789012345")
        with self.assertRaises(Exception):
            self.g_dao.insertar(d2)  # mismo IMEI + mismo vehicle_id (UNIQUE ambos)

    def test_actualizar_online(self):
        d = GpsDevice(vehicle_id=self.veh.vehicle_id, imei="123456789012345")
        self.g_dao.insertar(d)
        self.g_dao.actualizar_online(d.device_id, True)
        row = self.g_dao.buscar_por_id(d.device_id)
        self.assertEqual(row[5], 1)


class TestGeofenceDao(unittest.TestCase):

    def setUp(self):
        _, self.path = tempfile.mkstemp(suffix=".db")
        self.conn = crear_conexion(self.path)
        Dao(self.conn).crear_todas_las_tablas()
        u_dao = UserDao(self.conn)
        v_dao = VehicleDao(self.conn)
        self.gf_dao = GeofenceDao(self.conn)
        user = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        u_dao.insertar(user)
        self.veh = Vehicle(user_id=user.user_id, license_plate="ABCD12")
        v_dao.insertar(self.veh)

    def tearDown(self):
        self.conn.close()

    def test_insertar_y_buscar(self):
        gf = Geofence(vehicle_id=self.veh.vehicle_id, name="Casa",
                      area_wkt="POLYGON((-70.6 -33.4, -70.5 -33.4, -70.5 -33.5, -70.6 -33.5, -70.6 -33.4))")
        gfid = self.gf_dao.insertar(gf)
        row = self.gf_dao.buscar_por_id(gfid)
        self.assertIsNotNone(row)
        self.assertEqual(row[2], "Casa")

    def test_listar_por_vehiculo(self):
        gf = Geofence(vehicle_id=self.veh.vehicle_id, name="Casa", area_wkt="POLYGON((1 1, 2 1, 2 2, 1 2, 1 1))")
        self.gf_dao.insertar(gf)
        rows = self.gf_dao.listar_por_vehiculo(self.veh.vehicle_id)
        self.assertEqual(len(rows), 1)


class TestTelemetryDao(unittest.TestCase):

    def setUp(self):
        _, self.path = tempfile.mkstemp(suffix=".db")
        self.conn = crear_conexion(self.path)
        Dao(self.conn).crear_todas_las_tablas()
        u_dao = UserDao(self.conn)
        v_dao = VehicleDao(self.conn)
        g_dao = GpsDeviceDao(self.conn)
        self.t_dao = TelemetryDao(self.conn)
        user = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        u_dao.insertar(user)
        veh = Vehicle(user_id=user.user_id, license_plate="ABCD12")
        v_dao.insertar(veh)
        self.dev = GpsDevice(vehicle_id=veh.vehicle_id, imei="123456789012345")
        g_dao.insertar(self.dev)

    def tearDown(self):
        self.conn.close()

    def test_insertar_y_buscar(self):
        t = TelemetryLog(device_id=self.dev.device_id, point_wkt="POINT(-70.5 -33.4)",
                         speed_kmh=15.0, acc_ignition=True)
        tid = self.t_dao.insertar(t)
        self.assertIsNotNone(tid)
        row = self.t_dao.buscar_por_id(tid)
        self.assertIsNotNone(row)

    def test_ultima_velocidad(self):
        t1 = TelemetryLog(device_id=self.dev.device_id, point_wkt="POINT(1 1)", speed_kmh=30.0)
        self.t_dao.insertar(t1)
        t2 = TelemetryLog(device_id=self.dev.device_id, point_wkt="POINT(1 1)", speed_kmh=15.0)
        self.t_dao.insertar(t2)
        speed = self.t_dao.ultima_velocidad(self.dev.device_id)
        self.assertIsNotNone(speed)

    def test_listar_por_device(self):
        t = TelemetryLog(device_id=self.dev.device_id, point_wkt="POINT(1 1)", speed_kmh=10.0)
        self.t_dao.insertar(t)
        rows = self.t_dao.listar_por_device(self.dev.device_id)
        self.assertEqual(len(rows), 1)


class TestCommandDao(unittest.TestCase):

    def setUp(self):
        _, self.path = tempfile.mkstemp(suffix=".db")
        self.conn = crear_conexion(self.path)
        Dao(self.conn).crear_todas_las_tablas()
        u_dao = UserDao(self.conn)
        v_dao = VehicleDao(self.conn)
        g_dao = GpsDeviceDao(self.conn)
        self.c_dao = CutEngineCommandDao(self.conn)
        user = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        u_dao.insertar(user)
        veh = Vehicle(user_id=user.user_id, license_plate="ABCD12")
        v_dao.insertar(veh)
        self.dev = GpsDevice(vehicle_id=veh.vehicle_id, imei="123456789012345")
        g_dao.insertar(self.dev)

    def tearDown(self):
        self.conn.close()

    def test_insertar_y_buscar(self):
        c = CutEngineCommand(device_id=self.dev.device_id)
        cid = self.c_dao.insertar(c)
        row = self.c_dao.buscar_por_id(cid)
        self.assertIsNotNone(row)
        self.assertEqual(row[3], "PENDING_SPEED_CHECK")

    def test_actualizar_estado(self):
        c = CutEngineCommand(device_id=self.dev.device_id)
        cid = self.c_dao.insertar(c)
        self.c_dao.actualizar_estado(cid, "EXECUTED", "2026-10-01T00:00:00Z", 15.0)
        row = self.c_dao.buscar_por_id(cid)
        self.assertEqual(row[3], "EXECUTED")
        self.assertEqual(row[5], 15.0)

    def test_pendientes_por_device(self):
        c = CutEngineCommand(device_id=self.dev.device_id)
        self.c_dao.insertar(c)
        rows = self.c_dao.pendientes_por_device(self.dev.device_id)
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
