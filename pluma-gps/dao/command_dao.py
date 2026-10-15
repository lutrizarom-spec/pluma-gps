from dao.dao import Dao


class CutEngineCommandDao(Dao):

    def crear_tabla(self):
        self.ejecutar("""
            CREATE TABLE IF NOT EXISTS cut_engine_commands (
                command_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                status TEXT NOT NULL,
                doors_locked INTEGER DEFAULT 0,
                windows_closed INTEGER DEFAULT 0,
                executed_at TEXT,
                speed_at_execution REAL,
                FOREIGN KEY (device_id) REFERENCES gps_devices (device_id)
            )
        """)
        self.conexion.commit()

    def insertar(self, command) -> str:
        self.ejecutar("""
            INSERT INTO cut_engine_commands (
                command_id, device_id, requested_at, status,
                doors_locked, windows_closed, executed_at, speed_at_execution
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (command.command_id, command.device_id,
              command.requested_at, command.status.value,
              int(command.doors_locked), int(command.windows_closed),
              command.executed_at, command.speed_at_execution))
        self.conexion.commit()
        return command.command_id

    def buscar_por_id(self, command_id: str):
        self.ejecutar(
            "SELECT command_id, device_id, requested_at, status, executed_at, speed_at_execution, doors_locked, windows_closed FROM cut_engine_commands WHERE command_id = ?",
            (command_id,))
        return self.cursor.fetchone()

    def actualizar_estado(self, command_id: str, status: str,
                          executed_at: str = None, speed_at_execution: float = None):
        self.ejecutar("""
            UPDATE cut_engine_commands
            SET status = ?, executed_at = ?, speed_at_execution = ?
            WHERE command_id = ?
        """, (status, executed_at, speed_at_execution, command_id))
        self.conexion.commit()

    def pendientes_por_device(self, device_id: str):
        self.ejecutar(
            "SELECT * FROM cut_engine_commands WHERE device_id = ? AND status = 'PENDING_SPEED_CHECK'",
            (device_id,))
        return self.cursor.fetchall()

    def listar(self):
        self.ejecutar(
            "SELECT command_id, device_id, requested_at, status, executed_at, speed_at_execution FROM cut_engine_commands")
        return self.cursor.fetchall()
