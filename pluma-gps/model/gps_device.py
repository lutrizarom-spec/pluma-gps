import uuid
from model.enums import HardwareLevel


class GpsDevice:
    def __init__(self, vehicle_id: str, imei: str,
                 hardware_model: str = "Suntech ST4315",
                 level: HardwareLevel = HardwareLevel.LEVEL_1_BASIC,
                 is_online: bool = False,
                 dashcam_connected: bool = True,
                 device_id: str = None):
        self.__device_id = device_id or str(uuid.uuid4())
        self.__vehicle_id = vehicle_id
        self.imei = imei  # usa setter
        self.__hardware_model = hardware_model or "Suntech ST4315"
        self.__level = level
        self.__is_online = is_online
        self.__dashcam_connected = dashcam_connected

    @property
    def device_id(self) -> str:
        return self.__device_id

    @property
    def vehicle_id(self) -> str:
        return self.__vehicle_id

    @property
    def imei(self) -> str:
        return self.__imei

    @imei.setter
    def imei(self, valor: str):
        valor = valor.strip()
        if not valor.isdigit() or len(valor) < 14 or len(valor) > 16:
            raise ValueError("IMEI debe ser numérico de 14-16 dígitos.")
        self.__imei = valor

    @property
    def hardware_model(self) -> str:
        return self.__hardware_model

    @property
    def level(self) -> HardwareLevel:
        return self.__level

    @property
    def is_online(self) -> bool:
        return self.__is_online

    @property
    def dashcam_connected(self) -> bool:
        return self.__dashcam_connected

    def set_online(self, online: bool):
        self.__is_online = online

    def process_telemetry(self, frame: dict) -> dict:
        if not self.__is_online:
            raise RuntimeError("Dispositivo offline, no puede procesar telemetría.")
        return {"device_id": self.__device_id, "frame": frame}

    def execute_relay_cut(self) -> bool:
        if not self.__is_online:
            return False
        return True

    def ping_heartbeat(self) -> bool:
        self.__is_online = True
        return True

    def __repr__(self):
        return f"GpsDevice({self.__imei}, {self.__hardware_model}, {self.__level.value})"
