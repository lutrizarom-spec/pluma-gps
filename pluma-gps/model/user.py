import re
import uuid
import bcrypt
from model.enums import PlanSubscription


class User:
    def __init__(self, rut: str, full_name: str, email: str,
                 plan: PlanSubscription = PlanSubscription.FREE_ADS,
                 user_id: str = None, is_active: bool = True,
                 password_hash: str = None):
        self.__user_id = user_id or str(uuid.uuid4())
        self.rut = rut
        self.__full_name = full_name
        self.__email = email
        self.__plan = plan
        self.__is_active = is_active
        self.__password_hash = password_hash

    @property
    def user_id(self) -> str:
        return self.__user_id

    @property
    def full_name(self) -> str:
        return self.__full_name

    @property
    def email(self) -> str:
        return self.__email

    @property
    def plan(self) -> PlanSubscription:
        return self.__plan

    @property
    def is_active(self) -> bool:
        return self.__is_active

    def set_active(self, active: bool):
        self.__is_active = active

    # --- password hashing (bcrypt via passlib) ---
    def set_password(self, plain: str):
        if not plain or len(plain) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")
        self.__password_hash = bcrypt.hashpw(
            plain.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def verify_password(self, plain: str) -> bool:
        if not self.__password_hash:
            return False
        try:
            return bcrypt.checkpw(
                plain.encode('utf-8'),
                self.__password_hash.encode('utf-8')
            )
        except Exception:
            return False

    @property
    def password_hash(self):
        return self.__password_hash

    @password_hash.setter
    def password_hash(self, val):
        self.__password_hash = val

    # --- rut con validación módulo 11 ---
    @property
    def rut(self) -> str:
        return self.__rut

    @rut.setter
    def rut(self, valor: str):
        if not self.validate_chilean_rut(valor):
            raise ValueError(f"RUT inválido: {valor}")
        self.__rut = valor

    @staticmethod
    def validate_chilean_rut(rut: str) -> bool:
        if not rut:
            return False
        rut = rut.strip().replace(".", "").replace("-", "")
        if len(rut) < 2:
            return False
        cuerpo, dv = rut[:-1], rut[-1].upper()
        if not cuerpo.isdigit():
            return False
        suma, mul = 0, 2
        for d in reversed(cuerpo):
            suma += int(d) * mul
            mul = mul + 1 if mul < 7 else 2
        esperado = 11 - (suma % 11)
        esperado = {11: "0", 10: "K"}.get(esperado, str(esperado))
        return esperado == dv

    def register_vehicle(self, current_vehicle_count: int) -> bool:
        max_v = self.__plan.max_vehicles
        if max_v != -1 and current_vehicle_count >= max_v:
            raise ValueError(f"Plan {self.__plan.value} permite máximo {max_v} vehículo(s).")
        return True

    def __repr__(self):
        return f"User({self.__rut}, {self.__full_name}, {self.__plan.value})"
