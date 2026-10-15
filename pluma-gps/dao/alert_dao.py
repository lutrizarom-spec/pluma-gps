from dao.dao import Dao


class AlertDao(Dao):

    def crear_tabla(self):
        self.ejecutar("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (device_id) REFERENCES gps_devices (device_id)
            )
        """)
        self.conexion.commit()

    def insertar(self, alert) -> str:
        self.ejecutar("""
            INSERT INTO alerts (alert_id, device_id, type, message, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (alert.alert_id, alert.device_id, alert.type.value,
              alert.message, alert.status.value, alert.created_at))
        self.conexion.commit()
        return alert.alert_id

    def buscar_por_id(self, alert_id: str):
        self.ejecutar(
            "SELECT alert_id, device_id, type, message, status, created_at FROM alerts WHERE alert_id = ?",
            (alert_id,))
        return self.cursor.fetchone()

    def acknowledge(self, alert_id: str):
        self.ejecutar(
            "UPDATE alerts SET status = 'ACKNOWLEDGED' WHERE alert_id = ?",
            (alert_id,))
        self.conexion.commit()

    def listar(self, device_id: str = None, status: str = None, alert_type: str = None):
        sql = "SELECT alert_id, device_id, type, message, status, created_at FROM alerts WHERE 1=1"
        params = []
        if device_id:
            sql += " AND device_id = ?"
            params.append(device_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if alert_type:
            sql += " AND type = ?"
            params.append(alert_type)
        sql += " ORDER BY created_at DESC"
        self.ejecutar(sql, tuple(params))
        return self.cursor.fetchall()
