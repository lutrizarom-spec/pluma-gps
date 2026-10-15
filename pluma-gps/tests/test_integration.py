"""Test de integración: flujo completo User→Vehicle→GPS→Telemetry→Command."""
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


class TestFlujoCompleto(unittest.TestCase):

    def setUp(self):
        _, self.path = tempfile.mkstemp(suffix=".db")
        self.conn = crear_conexion(self.path)
        Dao(self.conn).crear_todas_las_tablas()
        self.u_dao = UserDao(self.conn)
        self.v_dao = VehicleDao(self.conn)
        self.g_dao = GpsDeviceDao(self.conn)
        self.gf_dao = GeofenceDao(self.conn)
        self.t_dao = TelemetryDao(self.conn)
        self.c_dao = CutEngineCommandDao(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_flujo_completo(self):
        # 1. Crear usuario
        user = User(rut="12.345.678-5", full_name="Juan Pérez",
                    email="jp@test.cl", plan=PlanSubscription.PRO_MONTHLY)
        self.u_dao.insertar(user)

        # 2. Registrar vehículo
        self.assertTrue(user.register_vehicle(self.v_dao.contar_por_usuario(user.user_id)))
        veh = Vehicle(user_id=user.user_id, license_plate="ABCD12",
                      brand="Toyota", model="Hilux", manufacture_year=2024)
        self.v_dao.insertar(veh)

        # 3. Asignar GPS
        dev = GpsDevice(vehicle_id=veh.vehicle_id, imei="123456789012345",
                        hardware_model="Suntech ST4315", level=HardwareLevel.LEVEL_1_BASIC,
                        is_online=True)
        self.g_dao.insertar(dev)
        veh.assign_gps_device(dev)
        self.assertTrue(veh.get_active_status())

        # 4. Crear geocerca
        gf = Geofence(vehicle_id=veh.vehicle_id, name="Casa",
                      area_wkt="POLYGON((-70.6 -33.4, -70.5 -33.4, -70.5 -33.5, -70.6 -33.5, -70.6 -33.4))")
        self.gf_dao.insertar(gf)

        # 5. Registrar telemetría
        tele = TelemetryLog(device_id=dev.device_id, point_wkt="POINT(-70.55 -33.45)",
                            speed_kmh=15.0, heading=90.0, acc_ignition=True,
                            odometer_km=12500.0, dashcam_recording=True)
        self.t_dao.insertar(tele)

        # 6. Solicitar corte-corriente
        cmd = CutEngineCommand(device_id=dev.device_id)
        self.c_dao.insertar(cmd)
        self.assertEqual(cmd.status, CommandStatus.PENDING_SPEED_CHECK)

        # 7. Evaluar velocidad y ejecutar
        speed = self.t_dao.ultima_velocidad(dev.device_id)
        if CutEngineCommand.validate_safety_speed(speed):
            cmd.mark_as_executed(speed)
            self.c_dao.actualizar_estado(cmd.command_id, cmd.status.value,
                                       cmd.executed_at, cmd.speed_at_execution)

        row = self.c_dao.buscar_por_id(cmd.command_id)
        self.assertEqual(row[3], "EXECUTED")

        # 8. Validar geocerca
        self.assertTrue(gf.check_containment("POINT(-70.55 -33.45)"))

        # 9. Validar telemetría y dashcam
        self.assertTrue(tele.dashcam_recording)
        self.assertEqual(tele.odometer_km, 12500.0)

    def test_corte_rechazado_por_velocidad(self):
        """Velocidad > 20 km/h debe mantener PENDING_SPEED_CHECK."""
        user = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        self.u_dao.insertar(user)
        veh = Vehicle(user_id=user.user_id, license_plate="ABCD12")
        self.v_dao.insertar(veh)
        dev = GpsDevice(vehicle_id=veh.vehicle_id, imei="123456789012345", is_online=True)
        self.g_dao.insertar(dev)

        tele = TelemetryLog(device_id=dev.device_id, point_wkt="POINT(1 1)",
                            speed_kmh=80.0)
        self.t_dao.insertar(tele)

        cmd = CutEngineCommand(device_id=dev.device_id)
        self.c_dao.insertar(cmd)

        speed = self.t_dao.ultima_velocidad(dev.device_id)
        if not CutEngineCommand.validate_safety_speed(speed):
            # Mantiene pendiente
            pass
        else:
            cmd.mark_as_executed(speed)
            self.c_dao.actualizar_estado(cmd.command_id, cmd.status.value,
                                       cmd.executed_at, cmd.speed_at_execution)

        row = self.c_dao.buscar_por_id(cmd.command_id)
        self.assertEqual(row[3], "PENDING_SPEED_CHECK")

    def test_cancelacion_por_timeout(self):
        """Comando pendiente >24h se cancela."""
        user = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        self.u_dao.insertar(user)
        veh = Vehicle(user_id=user.user_id, license_plate="ABCD12")
        self.v_dao.insertar(veh)
        dev = GpsDevice(vehicle_id=veh.vehicle_id, imei="123456789012345")
        self.g_dao.insertar(dev)

        cmd = CutEngineCommand(device_id=dev.device_id)
        self.c_dao.insertar(cmd)

        # Simular timeout
        cmd.cancel_due_to_timeout()
        self.c_dao.actualizar_estado(cmd.command_id, cmd.status.value)

        row = self.c_dao.buscar_por_id(cmd.command_id)
        self.assertEqual(row[3], "CANCELLED_SAFETY")

    def test_integridad_referencial_completa(self):
        """Insertar en orden correcto y validar que todas las FKs existen."""
        user = User(rut="12.345.678-5", full_name="Juan", email="j@test.cl")
        self.u_dao.insertar(user)

        veh = Vehicle(user_id=user.user_id, license_plate="ABCD12")
        self.v_dao.insertar(veh)

        dev = GpsDevice(vehicle_id=veh.vehicle_id, imei="123456789012345")
        self.g_dao.insertar(dev)

        gf = Geofence(vehicle_id=veh.vehicle_id, name="X", area_wkt="POLYGON((1 1, 2 1, 2 2, 1 2, 1 1))")
        self.gf_dao.insertar(gf)

        tele = TelemetryLog(device_id=dev.device_id, point_wkt="POINT(1 1)")
        self.t_dao.insertar(tele)

        cmd = CutEngineCommand(device_id=dev.device_id)
        self.c_dao.insertar(cmd)

        # Contar registros
        self.assertEqual(len(self.u_dao.listar()), 1)
        self.assertEqual(len(self.v_dao.listar()), 1)
        self.assertEqual(len(self.g_dao.listar()), 1)
        self.assertEqual(len(self.gf_dao.listar_por_vehiculo(veh.vehicle_id)), 1)
        self.assertEqual(len(self.t_dao.listar_por_device(dev.device_id)), 1)
        self.assertEqual(len(self.c_dao.listar()), 1)


if __name__ == "__main__":
    unittest.main()
