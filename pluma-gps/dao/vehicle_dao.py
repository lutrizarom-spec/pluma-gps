from dao.dao import Dao


class VehicleDao(Dao):

    def crear_tabla(self):
        self.ejecutar("""
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                license_plate TEXT NOT NULL,
                brand TEXT,
                model TEXT,
                manufacture_year INTEGER,
                engine_type TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        self.conexion.commit()

    def insertar(self, vehicle) -> str:
        self.ejecutar("""
            INSERT INTO vehicles (vehicle_id, user_id, license_plate, brand, model, manufacture_year, engine_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (vehicle.vehicle_id, vehicle.user_id, vehicle.license_plate,
              vehicle.brand, vehicle.model, vehicle.manufacture_year,
              vehicle.engine_type))
        self.conexion.commit()
        return vehicle.vehicle_id

    def buscar_por_id(self, vehicle_id: str):
        self.ejecutar(
            "SELECT vehicle_id, user_id, license_plate, brand, model, manufacture_year, engine_type FROM vehicles WHERE vehicle_id = ?",
            (vehicle_id,))
        return self.cursor.fetchone()

    def buscar_por_patente(self, license_plate: str):
        self.ejecutar(
            "SELECT vehicle_id, user_id, license_plate, brand, model, manufacture_year, engine_type FROM vehicles WHERE license_plate = ?",
            (license_plate,))
        return self.cursor.fetchone()

    def contar_por_usuario(self, user_id: str) -> int:
        self.ejecutar(
            "SELECT COUNT(*) FROM vehicles WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()[0]

    def listar(self):
        self.ejecutar(
            "SELECT vehicle_id, user_id, license_plate, brand, model, manufacture_year, engine_type FROM vehicles")
        return self.cursor.fetchall()
