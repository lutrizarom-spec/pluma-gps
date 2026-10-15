from dao.dao import Dao


class UserDao(Dao):

    def crear_tabla(self):
        if self.is_postgres():
            self.ejecutar("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    rut TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    subscription_plan TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    password_hash TEXT
                )
            """)
        else:
            self.ejecutar("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    rut TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    subscription_plan TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    password_hash TEXT
                )
            """)
        self.conexion.commit()

    def insertar(self, user) -> str:
        self.ejecutar("""
            INSERT INTO users (user_id, rut, full_name, email, subscription_plan, is_active, password_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user.user_id, user.rut, user.full_name, user.email,
              user.plan.value, int(user.is_active), user.password_hash))
        self.conexion.commit()
        return user.user_id

    def buscar_por_id(self, user_id: str):
        self.ejecutar(
            "SELECT user_id, rut, full_name, email, subscription_plan, is_active, password_hash FROM users WHERE user_id = ?",
            (user_id,))
        return self.cursor.fetchone()

    def buscar_por_rut(self, rut: str):
        self.ejecutar(
            "SELECT user_id, rut, full_name, email, subscription_plan, is_active, password_hash FROM users WHERE rut = ?",
            (rut,))
        return self.cursor.fetchone()

    def contar_vehiculos(self, user_id: str) -> int:
        self.ejecutar(
            "SELECT COUNT(*) FROM vehicles WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()[0]

    def listar(self):
        self.ejecutar(
            "SELECT user_id, rut, full_name, email, subscription_plan, is_active FROM users")
        return self.cursor.fetchall()
