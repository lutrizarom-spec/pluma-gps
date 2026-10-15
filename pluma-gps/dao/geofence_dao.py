from dao.dao import Dao


class GeofenceDao(Dao):

    def crear_tabla(self):
        self.ejecutar("""
            CREATE TABLE IF NOT EXISTS geofences (
                geofence_id TEXT PRIMARY KEY,
                vehicle_id TEXT NOT NULL,
                name TEXT NOT NULL,
                area_wkt TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (vehicle_id)
            )
        """)
        self.conexion.commit()

    def insertar(self, geofence) -> str:
        self.ejecutar("""
            INSERT INTO geofences (geofence_id, vehicle_id, name, area_wkt, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (geofence.geofence_id, geofence.vehicle_id,
              geofence.name, geofence.area_wkt, geofence.created_at))
        self.conexion.commit()
        return geofence.geofence_id

    def buscar_por_id(self, geofence_id: str):
        self.ejecutar(
            "SELECT geofence_id, vehicle_id, name, area_wkt, created_at FROM geofences WHERE geofence_id = ?",
            (geofence_id,))
        return self.cursor.fetchone()

    def listar(self):
        self.ejecutar(
            "SELECT geofence_id, vehicle_id, name, area_wkt, created_at FROM geofences")
        return self.cursor.fetchall()

    def listar_por_vehiculo(self, vehicle_id: str):
        self.ejecutar(
            "SELECT geofence_id, vehicle_id, name, area_wkt, created_at FROM geofences WHERE vehicle_id = ?",
            (vehicle_id,))
        return self.cursor.fetchall()
