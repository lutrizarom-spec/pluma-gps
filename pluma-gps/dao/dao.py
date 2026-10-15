import os


class Dao:
    """Clase base Data Access Object. Compatible SQLite y PostgreSQL."""

    def __init__(self, conexion):
        self.conexion = conexion
        self.cursor = conexion.cursor()

    @staticmethod
    def is_postgres() -> bool:
        return os.environ.get("DB_ENGINE", "sqlite").lower() == "postgres"

    @staticmethod
    def adapt_sql(sql: str) -> str:
        """Convierte placeholders ? de SQLite a %s de PostgreSQL."""
        if Dao.is_postgres():
            return sql.replace("?", "%s")
        return sql

    def ejecutar(self, sql: str, params: tuple = None):
        """Ejecuta SQL adaptando placeholders automáticamente."""
        self.cursor.execute(self.adapt_sql(sql), params or ())
        return self.cursor

    def crear_todas_las_tablas(self):
        """Crea todas las tablas en orden de dependencia FK."""
        from dao.user_dao import UserDao
        from dao.vehicle_dao import VehicleDao
        from dao.gps_device_dao import GpsDeviceDao
        from dao.geofence_dao import GeofenceDao
        from dao.telemetry_dao import TelemetryDao
        from dao.command_dao import CutEngineCommandDao

        from dao.alert_dao import AlertDao
        for cls in [UserDao, VehicleDao, GpsDeviceDao,
                    GeofenceDao, TelemetryDao, CutEngineCommandDao, AlertDao]:
            cls(self.conexion).crear_tabla()
