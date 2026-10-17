from dao.dao import Dao

_COLS = ("assignment_id, vehicle_id, user_id, start_time, end_time, "
         "is_replacement, authorized_by, created_at")
_OPEN_END = "9999-12-31T23:59:59"


class VehicleAssignmentDao(Dao):

    def crear_tabla(self):
        self.ejecutar("""
            CREATE TABLE IF NOT EXISTS vehicle_assignments (
                assignment_id TEXT PRIMARY KEY,
                vehicle_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                is_replacement INTEGER NOT NULL DEFAULT 0,
                authorized_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (vehicle_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (authorized_by) REFERENCES users (user_id)
            )
        """)
        self.conexion.commit()

    def insertar(self, assignment) -> str:
        self.ejecutar("""
            INSERT INTO vehicle_assignments
                (assignment_id, vehicle_id, user_id, start_time, end_time,
                 is_replacement, authorized_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (assignment.assignment_id, assignment.vehicle_id,
              assignment.user_id, assignment.start_time, assignment.end_time,
              int(assignment.is_replacement), assignment.authorized_by,
              assignment.created_at))
        self.conexion.commit()
        return assignment.assignment_id

    def buscar_por_id(self, assignment_id: str):
        self.ejecutar(
            f"SELECT {_COLS} FROM vehicle_assignments WHERE assignment_id = ?",
            (assignment_id,))
        return self.cursor.fetchone()

    def listar(self):
        self.ejecutar(
            f"SELECT {_COLS} FROM vehicle_assignments ORDER BY start_time")
        return self.cursor.fetchall()

    def listar_por_vehiculo(self, vehicle_id: str):
        self.ejecutar(
            f"SELECT {_COLS} FROM vehicle_assignments WHERE vehicle_id = ? "
            "ORDER BY start_time", (vehicle_id,))
        return self.cursor.fetchall()

    def listar_por_conductor(self, user_id: str):
        self.ejecutar(
            f"SELECT {_COLS} FROM vehicle_assignments WHERE user_id = ? "
            "ORDER BY start_time", (user_id,))
        return self.cursor.fetchall()

    def listar_reemplazos(self):
        self.ejecutar(
            f"SELECT {_COLS} FROM vehicle_assignments WHERE is_replacement = 1 "
            "ORDER BY start_time")
        return self.cursor.fetchall()

    def buscar_activa_por_vehiculo(self, vehicle_id: str, momento: str):
        self.ejecutar(
            f"SELECT {_COLS} FROM vehicle_assignments "
            "WHERE vehicle_id = ? AND start_time <= ? "
            "AND COALESCE(end_time, ?) > ? "
            "ORDER BY start_time DESC",
            (vehicle_id, momento, _OPEN_END, momento))
        return self.cursor.fetchone()

    def buscar_activa_por_conductor(self, user_id: str, momento: str):
        self.ejecutar(
            f"SELECT {_COLS} FROM vehicle_assignments "
            "WHERE user_id = ? AND start_time <= ? "
            "AND COALESCE(end_time, ?) > ? "
            "ORDER BY start_time DESC",
            (user_id, momento, _OPEN_END, momento))
        return self.cursor.fetchone()

    def buscar_solapamiento(self, vehicle_id: str, start: str, end: str = None):
        self.ejecutar(
            f"SELECT {_COLS} FROM vehicle_assignments "
            "WHERE vehicle_id = ? AND start_time < COALESCE(?, ?) "
            "AND COALESCE(end_time, ?) > ?",
            (vehicle_id, end, _OPEN_END, _OPEN_END, start))
        return self.cursor.fetchall()

    def cerrar(self, assignment_id: str, end_time: str):
        self.ejecutar(
            "UPDATE vehicle_assignments SET end_time = ? WHERE assignment_id = ?",
            (end_time, assignment_id))
        self.conexion.commit()

    def eliminar(self, assignment_id: str):
        self.ejecutar(
            "DELETE FROM vehicle_assignments WHERE assignment_id = ?",
            (assignment_id,))
        self.conexion.commit()
