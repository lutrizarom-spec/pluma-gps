from dao.dao import Dao


class TelemetryDao(Dao):

    def crear_tabla(self):
        self.ejecutar("""
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                point_wkt TEXT NOT NULL,
                speed_kmh REAL DEFAULT 0,
                heading REAL DEFAULT 0,
                acc_ignition INTEGER DEFAULT 0,
                main_battery REAL,
                backup_battery REAL,
                fuel_level REAL,
                odometer_km REAL DEFAULT 0,
                dashcam_recording INTEGER DEFAULT 0,
                FOREIGN KEY (device_id) REFERENCES gps_devices (device_id)
            )
        """)
        self.conexion.commit()

    def insertar(self, telemetry) -> int:
        self.ejecutar("""
            INSERT INTO telemetry_logs (
                device_id, recorded_at, point_wkt, speed_kmh, heading,
                acc_ignition, main_battery, backup_battery,
                fuel_level, odometer_km, dashcam_recording
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (telemetry.device_id, telemetry.recorded_at, telemetry.point_wkt,
              telemetry.speed_kmh, telemetry.heading,
              int(telemetry.acc_ignition), telemetry.main_battery,
              telemetry.backup_battery, telemetry.fuel_level,
              telemetry.odometer_km, int(telemetry.dashcam_recording)))
        self.conexion.commit()
        telemetry.telemetry_id = self.cursor.lastrowid
        return telemetry.telemetry_id

    def buscar_por_id(self, telemetry_id: int):
        self.ejecutar(
            "SELECT * FROM telemetry_logs WHERE telemetry_id = ?", (telemetry_id,))
        return self.cursor.fetchone()

    def listar(self):
        self.ejecutar(
            "SELECT * FROM telemetry_logs ORDER BY recorded_at DESC")
        return self.cursor.fetchall()

    def listar_por_device(self, device_id: str, limit: int = 100):
        self.ejecutar(
            "SELECT * FROM telemetry_logs WHERE device_id = ? ORDER BY recorded_at DESC LIMIT ?",
            (device_id, limit))
        return self.cursor.fetchall()

    def ultima_velocidad(self, device_id: str):
        self.ejecutar(
            "SELECT speed_kmh FROM telemetry_logs WHERE device_id = ? ORDER BY recorded_at DESC LIMIT 1",
            (device_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def ultimo_registro(self, device_id: str):
        self.ejecutar(
            "SELECT * FROM telemetry_logs WHERE device_id = ? ORDER BY recorded_at DESC LIMIT 1",
            (device_id,))
        return self.cursor.fetchone()
