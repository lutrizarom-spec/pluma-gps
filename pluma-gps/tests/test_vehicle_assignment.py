import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conectar import crear_conexion
from dao.dao import Dao
from dao.user_dao import UserDao
from dao.vehicle_dao import VehicleDao
from dao.work_schedule_dao import VehicleAssignmentDao

from model.enums import PlanSubscription
from model.user import User
from model.vehicle import Vehicle
from model.work_schedule import VehicleAssignment


class TestVehicleAssignmentDao(unittest.TestCase):

    def setUp(self):
        _, self.path = tempfile.mkstemp(suffix=".db")
        self.conn = crear_conexion(self.path)
        Dao(self.conn).crear_todas_las_tablas()
        self.dao = VehicleAssignmentDao(self.conn)

        self.titular = User(rut="12.345.678-5", full_name="Titular",
                            email="titular@test.cl",
                            plan=PlanSubscription.PRO_MONTHLY)
        self.reemplazo = User(rut="11.111.111-1", full_name="Reemplazo",
                              email="reemplazo@test.cl",
                              plan=PlanSubscription.PRO_MONTHLY)
        UserDao(self.conn).insertar(self.titular)
        UserDao(self.conn).insertar(self.reemplazo)

        self.vehiculo = Vehicle(user_id=self.titular.user_id,
                                license_plate="AAAA11")
        VehicleDao(self.conn).insertar(self.vehiculo)

    def tearDown(self):
        self.conn.close()

    def test_insertar_y_buscar(self):
        a = VehicleAssignment(
            vehicle_id=self.vehiculo.vehicle_id, user_id=self.titular.user_id,
            start_time="2026-10-01T08:00:00", end_time="2026-10-31T19:00:00",
            authorized_by=self.titular.user_id)
        aid = self.dao.insertar(a)
        row = self.dao.buscar_por_id(aid)
        self.assertIsNotNone(row)
        self.assertEqual(row[0], aid)
        self.assertEqual(row[1], self.vehiculo.vehicle_id)
        self.assertEqual(row[2], self.titular.user_id)
        self.assertEqual(row[5], 0)  # is_replacement por defecto

    def test_solapamiento(self):
        self.dao.insertar(VehicleAssignment(
            vehicle_id=self.vehiculo.vehicle_id, user_id=self.titular.user_id,
            start_time="2026-10-01T08:00:00", end_time="2026-10-31T19:00:00",
            authorized_by=self.titular.user_id))

        choques = self.dao.buscar_solapamiento(
            self.vehiculo.vehicle_id, "2026-10-15T00:00:00", "2026-10-20T00:00:00")
        self.assertEqual(len(choques), 1)

        libre = self.dao.buscar_solapamiento(
            self.vehiculo.vehicle_id, "2026-11-01T00:00:00", "2026-11-10T00:00:00")
        self.assertEqual(libre, [])

    def test_conductor_activo_por_reemplazo(self):
        self.dao.insertar(VehicleAssignment(
            vehicle_id=self.vehiculo.vehicle_id, user_id=self.titular.user_id,
            start_time="2026-10-01T08:00:00", end_time="2026-10-31T19:00:00",
            authorized_by=self.titular.user_id))
        reap = VehicleAssignment(
            vehicle_id=self.vehiculo.vehicle_id, user_id=self.reemplazo.user_id,
            start_time="2026-10-17T08:00:00", end_time="2026-10-17T12:00:00",
            is_replacement=True, authorized_by=self.titular.user_id)
        self.dao.insertar(reap)

        momento = "2026-10-17T09:00:00"
        activo = self.dao.buscar_activa_por_conductor(self.reemplazo.user_id, momento)
        self.assertIsNotNone(activo)
        self.assertEqual(activo[0], reap.assignment_id)
        self.assertEqual(activo[5], 1)

        reemplazos = self.dao.listar_reemplazos()
        self.assertEqual(len(reemplazos), 1)
        self.assertEqual(reemplazos[0][0], reap.assignment_id)

    def test_cerrar_vigencia(self):
        a = VehicleAssignment(
            vehicle_id=self.vehiculo.vehicle_id, user_id=self.titular.user_id,
            start_time="2026-10-01T08:00:00", authorized_by=self.titular.user_id)
        self.dao.insertar(a)
        self.assertIsNone(self.dao.buscar_por_id(a.assignment_id)[4])  # end_time abierto

        self.dao.cerrar(a.assignment_id, "2026-10-10T19:00:00")
        self.assertEqual(self.dao.buscar_por_id(a.assignment_id)[4],
                         "2026-10-10T19:00:00")


class TestVehicleAssignmentModel(unittest.TestCase):

    def test_is_active(self):
        a = VehicleAssignment(vehicle_id="v1", user_id="u1",
                              start_time="2026-10-01T00:00:00",
                              end_time="2026-10-31T00:00:00")
        self.assertTrue(a.is_active("2026-10-15T00:00:00"))
        self.assertFalse(a.is_active("2026-11-15T00:00:00"))

    def test_overlaps(self):
        a = VehicleAssignment(vehicle_id="v1", user_id="u1",
                              start_time="2026-10-01T00:00:00",
                              end_time="2026-10-31T00:00:00")
        self.assertTrue(a.overlaps("2026-10-15T00:00:00", "2026-10-20T00:00:00"))
        self.assertFalse(a.overlaps("2026-11-01T00:00:00", "2026-11-10T00:00:00"))


if __name__ == "__main__":
    unittest.main()
