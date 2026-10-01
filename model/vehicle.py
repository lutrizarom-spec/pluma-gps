import uuid


class Vehicle:
    def __init__(self, user_id: str, license_plate: str,
                 brand: str = "", model: str = "",
                 manufacture_year: int = 0, engine_type: str = "",
                 vehicle_id: str = None):
        self.__vehicle_id = vehicle_id or str(uuid.uuid4())
        self.__user_id = user_id
        self.license_plate = license_plate  # usa setter
        self.__brand = brand
        self.__model = model
        self.__manufacture_year = manufacture_year
        self.__engine_type = engine_type
        self.__gps_device = None

    @property
    def vehicle_id(self) -> str:
        return self.__vehicle_id

    @property
    def user_id(self) -> str:
        return self.__user_id

    @property
    def license_plate(self) -> str:
        return self.__license_plate

    @license_plate.setter
    def license_plate(self, valor: str):
        valor = valor.strip().upper()
        if len(valor) < 6 or len(valor) > 10:
            raise ValueError("Patente debe tener entre 6 y 10 caracteres.")
        self.__license_plate = valor

    @property
    def brand(self) -> str:
        return self.__brand

    @property
    def model(self) -> str:
        return self.__model

    @property
    def manufacture_year(self) -> int:
        return self.__manufacture_year

    @property
    def engine_type(self) -> str:
        return self.__engine_type

    def assign_gps_device(self, gps_device):
        if self.__gps_device is not None:
            raise ValueError("El vehículo ya tiene un GPS asignado.")
        self.__gps_device = gps_device
        return True

    def get_active_status(self) -> bool:
        if self.__gps_device is None:
            return False
        return self.__gps_device.is_online

    @property
    def gps_device(self):
        return self.__gps_device

    def __repr__(self):
        return f"Vehicle({self.__license_plate}, {self.__brand} {self.__model})"
