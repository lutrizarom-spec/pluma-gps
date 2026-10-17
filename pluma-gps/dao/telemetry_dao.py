from dao.dao import Dao


class TelemetryDao(Dao):

    def crear_tabla(self):
        if self.is_postgres():
            self.ejecutar("""
                CREATE TABLE IF NOT EXISTS telemetry_logs (
                    telemetry_id SERIAL PRIMARY KEY,
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
                    vehicle_id TEXT,
                    speed_limit REAL,
                    zone_type TEXT,
                    FOREIGN KEY (device_id) REFERENCES gps_devices (device_id)
                )
            """)
        else:
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
                    vehicle_id TEXT,
                    speed_limit REAL,
                    zone_type TEXT,
                    FOREIGN KEY (device_id) REFERENCES gps_devices (device_id)
                )
            """)
        self.ejecutar("""
            CREATE INDEX IF NOT EXISTS ix_telemetry_vehicle_recorded
            ON telemetry_logs (vehicle_id, recorded_at)
        """)
        self.conexion.commit()

    def insertar(self, telemetry) -> int:
        cols = (telemetry.device_id, telemetry.recorded_at, telemetry.point_wkt,
                telemetry.speed_kmh, telemetry.heading,
                int(telemetry.acc_ignition), telemetry.main_battery,
                telemetry.backup_battery, telemetry.fuel_level,
                telemetry.odometer_km, int(telemetry.dashcam_recording),
                telemetry.vehicle_id, telemetry.speed_limit,
                telemetry.zone_type.value if telemetry.zone_type else None)
        if self.is_postgres():
            self.ejecutar("""
                INSERT INTO telemetry_logs (
                    device_id, recorded_at, point_wkt, speed_kmh, heading,
                    acc_ignition, main_battery, backup_battery,
                    fuel_level, odometer_km, dashcam_recording,
                    vehicle_id, speed_limit, zone_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING telemetry_id
            """, cols)
            telemetry.telemetry_id = self.cursor.fetchone()[0]
        else:
            self.ejecutar("""
                INSERT INTO telemetry_logs (
                    device_id, recorded_at, point_wkt, speed_kmh, heading,
                    acc_ignition, main_battery, backup_battery,
                    fuel_level, odometer_km, dashcam_recording,
                    vehicle_id, speed_limit, zone_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, cols)
            telemetry.telemetry_id = self.cursor.lastrowid
        self.conexion.commit()
        return telemetry.telemetry_id

    def registrar_lectura(self, telemetry) -> int:
        """Registra una lectura resolviendo vehicle_id desde el dispositivo."""
        if telemetry.vehicle_id is None:
            self.ejecutar(
                "SELECT vehicle_id FROM gps_devices WHERE device_id = ?",
                (telemetry.device_id,))
            row = self.cursor.fetchone()
            if row:
                telemetry.vehicle_id = row[0]
        return self.insertar(telemetry)

    def historial_excesos(self, license_plate: str,
                          desde: str = None, hasta: str = None):
        """Lecturas donde speed_kmh supera speed_limit, filtradas por patente
        y, opcionalmente, por rango de fechas (ISO, inclusivo)."""
        sql = """
            SELECT t.telemetry_id, t.device_id, t.vehicle_id, t.recorded_at,
                   t.speed_kmh, t.speed_limit, t.zone_type
            FROM telemetry_logs t
            JOIN gps_devices d ON d.device_id = t.device_id
            JOIN vehicles v ON v.vehicle_id = COALESCE(t.vehicle_id, d.vehicle_id)
            WHERE UPPER(v.license_plate) = ?
              AND t.speed_limit IS NOT NULL
              AND t.speed_kmh > t.speed_limit
        """
        params = [license_plate.strip().upper()]
        if desde:
            sql += " AND t.recorded_at >= ?"
            params.append(desde)
        if hasta:
            sql += " AND t.recorded_at <= ?"
            params.append(hasta)
        sql += " ORDER BY t.recorded_at DESC"
        self.ejecutar(sql, tuple(params))
        return self.cursor.fetchall()

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
