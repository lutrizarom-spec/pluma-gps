from dao.dao import Dao


class GpsDeviceDao(Dao):

    def crear_tabla(self):
        self.ejecutar("""
            CREATE TABLE IF NOT EXISTS gps_devices (
                device_id TEXT PRIMARY KEY,
                vehicle_id TEXT NOT NULL UNIQUE,
                imei TEXT NOT NULL UNIQUE,
                hardware_model TEXT,
                hardware_level TEXT NOT NULL,
                is_online INTEGER DEFAULT 0,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (vehicle_id)
            )
        """)
        self.conexion.commit()

    def insertar(self, device) -> str:
        self.ejecutar("""
            INSERT INTO gps_devices (device_id, vehicle_id, imei, hardware_model, hardware_level, is_online)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (device.device_id, device.vehicle_id, device.imei,
              device.hardware_model, device.level.value,
              int(device.is_online)))
        self.conexion.commit()
        return device.device_id

    def buscar_por_id(self, device_id: str):
        self.ejecutar(
            "SELECT device_id, vehicle_id, imei, hardware_model, hardware_level, is_online FROM gps_devices WHERE device_id = ?",
            (device_id,))
        return self.cursor.fetchone()

    def buscar_por_imei(self, imei: str):
        self.ejecutar(
            "SELECT device_id, vehicle_id, imei, hardware_model, hardware_level, is_online FROM gps_devices WHERE imei = ?",
            (imei,))
        return self.cursor.fetchone()

    def actualizar_online(self, device_id: str, is_online: bool):
        self.ejecutar(
            "UPDATE gps_devices SET is_online = ? WHERE device_id = ?",
            (int(is_online), device_id))
        self.conexion.commit()

    def listar(self):
        self.ejecutar(
            "SELECT device_id, vehicle_id, imei, hardware_model, hardware_level, is_online FROM gps_devices")
        return self.cursor.fetchall()
