import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model.enums import PlanSubscription, HardwareLevel, CommandStatus
from model.user import User
from model.vehicle import Vehicle
from model.gps_device import GpsDevice
from model.geofence import Geofence
from model.telemetry_log import TelemetryLog
from model.cut_engine_command import CutEngineCommand


class TestEnums(unittest.TestCase):

    def test_plan_values(self):
        self.assertEqual(PlanSubscription.FREE_ADS.value, "FREE_ADS")
        self.assertEqual(PlanSubscription.PRO_MONTHLY.value, "PRO_MONTHLY")
        self.assertEqual(PlanSubscription.ENTERPRISE_FLEET.value, "ENTERPRISE_FLEET")

    def test_plan_max_vehicles(self):
        self.assertEqual(PlanSubscription.FREE_ADS.max_vehicles, 1)
        self.assertEqual(PlanSubscription.PRO_MONTHLY.max_vehicles, 5)
        self.assertEqual(PlanSubscription.ENTERPRISE_FLEET.max_vehicles, -1)

    def test_hardware_levels(self):
        self.assertEqual(len(HardwareLevel), 3)

    def test_command_status(self):
        self.assertEqual(len(CommandStatus), 3)


class TestUser(unittest.TestCase):

    def test_crear_user_valido(self):
        u = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        self.assertEqual(u.rut, "12.345.678-5")
        self.assertEqual(u.plan, PlanSubscription.FREE_ADS)
        self.assertTrue(u.is_active)

    def test_rut_invalido(self):
        with self.assertRaises(ValueError):
            User(rut="12.345.678-0", full_name="X", email="x@test.cl")

    def test_rut_vacio(self):
        with self.assertRaises(ValueError):
            User(rut="", full_name="X", email="x@test.cl")

    def test_rut_k(self):
        u = User(rut="18.629.694-K", full_name="Test", email="k@test.cl")
        self.assertEqual(u.rut, "18.629.694-K")

    def test_plan_pro(self):
        u = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl",
                 plan=PlanSubscription.PRO_MONTHLY)
        self.assertEqual(u.plan.max_vehicles, 5)

    def test_register_vehicle_limit(self):
        u = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl",
                 plan=PlanSubscription.FREE_ADS)
        self.assertTrue(u.register_vehicle(0))
        with self.assertRaises(ValueError):
            u.register_vehicle(1)

    def test_user_id_autogenerado(self):
        u = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        self.assertEqual(len(u.user_id), 36)  # UUID


class TestVehicle(unittest.TestCase):

    def test_crear_vehicle(self):
        v = Vehicle(user_id="uid-123", license_plate="ABCD12")
        self.assertEqual(v.license_plate, "ABCD12")
        self.assertEqual(v.user_id, "uid-123")

    def test_patente_corta(self):
        with self.assertRaises(ValueError):
            Vehicle(user_id="u1", license_plate="AB")

    def test_patente_mayuscula(self):
        v = Vehicle(user_id="u1", license_plate="abc123")
        self.assertEqual(v.license_plate, "ABC123")

    def test_assign_gps(self):
        v = Vehicle(user_id="u1", license_plate="ABCD12")
        dev = GpsDevice(vehicle_id=v.vehicle_id, imei="123456789012345")
        v.assign_gps_device(dev)
        self.assertIsNotNone(v.gps_device)

    def test_assign_gps_doble(self):
        v = Vehicle(user_id="u1", license_plate="ABCD12")
        dev = GpsDevice(vehicle_id=v.vehicle_id, imei="123456789012345")
        v.assign_gps_device(dev)
        with self.assertRaises(ValueError):
            v.assign_gps_device(GpsDevice(vehicle_id=v.vehicle_id, imei="999999999999999"))

    def test_get_active_status_sin_gps(self):
        v = Vehicle(user_id="u1", license_plate="ABCD12")
        self.assertFalse(v.get_active_status())


class TestGpsDevice(unittest.TestCase):

    def test_crear_device(self):
        d = GpsDevice(vehicle_id="v1", imei="123456789012345")
        self.assertEqual(d.imei, "123456789012345")
        self.assertEqual(d.level, HardwareLevel.LEVEL_1_BASIC)
        self.assertFalse(d.is_online)

    def test_imei_corto(self):
        with self.assertRaises(ValueError):
            GpsDevice(vehicle_id="v1", imei="123")

    def test_imei_no_numerico(self):
        with self.assertRaises(ValueError):
            GpsDevice(vehicle_id="v1", imei="ABCDEFGHIJKLMN")

    def test_process_telemetry_offline(self):
        d = GpsDevice(vehicle_id="v1", imei="123456789012345")
        with self.assertRaises(RuntimeError):
            d.process_telemetry({})

    def test_process_telemetry_online(self):
        d = GpsDevice(vehicle_id="v1", imei="123456789012345", is_online=True)
        r = d.process_telemetry({"speed": 50})
        self.assertIn("device_id", r)

    def test_ping_heartbeat(self):
        d = GpsDevice(vehicle_id="v1", imei="123456789012345")
        self.assertFalse(d.is_online)
        self.assertTrue(d.ping_heartbeat())
        self.assertTrue(d.is_online)

    def test_execute_relay_cut_online(self):
        d = GpsDevice(vehicle_id="v1", imei="123456789012345", is_online=True)
        self.assertTrue(d.execute_relay_cut())

    def test_execute_relay_cut_offline(self):
        d = GpsDevice(vehicle_id="v1", imei="123456789012345")
        self.assertFalse(d.execute_relay_cut())


class TestGeofence(unittest.TestCase):

    POLYGON = "POLYGON((-70.6 -33.4, -70.5 -33.4, -70.5 -33.5, -70.6 -33.5, -70.6 -33.4))"

    def test_crear_geofence(self):
        gf = Geofence(vehicle_id="v1", name="Casa", area_wkt=self.POLYGON)
        self.assertEqual(gf.name, "Casa")
        self.assertTrue(gf.area_wkt.startswith("POLYGON"))

    def test_wkt_invalido(self):
        with self.assertRaises(ValueError):
            Geofence(vehicle_id="v1", name="X", area_wkt="LINESTRING(1 2, 3 4)")

    def test_containment_dentro(self):
        gf = Geofence(vehicle_id="v1", name="Casa", area_wkt=self.POLYGON)
        self.assertTrue(gf.check_containment("POINT(-70.55 -33.45)"))

    def test_containment_fuera(self):
        gf = Geofence(vehicle_id="v1", name="Casa", area_wkt=self.POLYGON)
        self.assertFalse(gf.check_containment("POINT(-70.0 -33.0)"))


class TestTelemetryLog(unittest.TestCase):

    def test_crear_telemetry(self):
        t = TelemetryLog(device_id="d1", point_wkt="POINT(-70.5 -33.4)",
                         speed_kmh=45.5, acc_ignition=True)
        self.assertEqual(t.speed_kmh, 45.5)
        self.assertTrue(t.acc_ignition)

    def test_wkt_invalido(self):
        with self.assertRaises(ValueError):
            TelemetryLog(device_id="d1", point_wkt="POLYGON(())")

    def test_evaluate_brake_fluid_ok(self):
        t = TelemetryLog(device_id="d1", point_wkt="POINT(1 1)",
                         brake_fluid_alert=False)
        self.assertFalse(t.evaluate_brake_fluid())

    def test_evaluate_brake_fluid_alert(self):
        t = TelemetryLog(device_id="d1", point_wkt="POINT(1 1)",
                         brake_fluid_alert=True)
        self.assertTrue(t.evaluate_brake_fluid())

    def test_recorded_at_autogenerado(self):
        t = TelemetryLog(device_id="d1", point_wkt="POINT(1 1)")
        self.assertIsNotNone(t.recorded_at)


class TestCutEngineCommand(unittest.TestCase):

    def test_crear_command(self):
        c = CutEngineCommand(device_id="d1")
        self.assertEqual(c.status, CommandStatus.PENDING_SPEED_CHECK)
        self.assertIsNone(c.executed_at)

    def test_validate_safety_speed_ok(self):
        self.assertTrue(CutEngineCommand.validate_safety_speed(15.0))
        self.assertTrue(CutEngineCommand.validate_safety_speed(20.0))

    def test_validate_safety_speed_excede(self):
        self.assertFalse(CutEngineCommand.validate_safety_speed(25.0))
        self.assertFalse(CutEngineCommand.validate_safety_speed(100.0))

    def test_mark_as_executed_ok(self):
        c = CutEngineCommand(device_id="d1")
        c.mark_as_executed(18.5)
        self.assertEqual(c.status, CommandStatus.EXECUTED)
        self.assertEqual(c.speed_at_execution, 18.5)
        self.assertIsNotNone(c.executed_at)

    def test_mark_as_executed_excede(self):
        c = CutEngineCommand(device_id="d1")
        with self.assertRaises(ValueError):
            c.mark_as_executed(50.0)
        self.assertEqual(c.status, CommandStatus.PENDING_SPEED_CHECK)

    def test_cancel_due_to_timeout(self):
        c = CutEngineCommand(device_id="d1")
        c.cancel_due_to_timeout()
        self.assertEqual(c.status, CommandStatus.CANCELLED_SAFETY)

    def test_command_id_autogenerado(self):
        c = CutEngineCommand(device_id="d1")
        self.assertEqual(len(c.command_id), 36)


if __name__ == "__main__":
    unittest.main()
