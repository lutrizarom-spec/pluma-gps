from datetime import datetime, timezone


class TelemetryLog:
    def __init__(self, device_id: str, point_wkt: str,
                 speed_kmh: float = 0.0, heading: float = 0.0,
                 acc_ignition: bool = False,
                 main_battery: float = None,
                 backup_battery: float = None,
                 fuel_level: float = None,
                 odometer_km: float = 0.0,
                 dashcam_recording: bool = False,
                 recorded_at: str = None,
                 telemetry_id: int = None):
        self.__telemetry_id = telemetry_id
        self.__device_id = device_id
        self.point_wkt = point_wkt  # usa setter
        self.__speed_kmh = speed_kmh
        self.__heading = heading
        self.__acc_ignition = acc_ignition
        self.__main_battery = main_battery
        self.__backup_battery = backup_battery
        self.__fuel_level = fuel_level
        self.__odometer_km = odometer_km
        self.__dashcam_recording = dashcam_recording
        self.__recorded_at = recorded_at or datetime.now(timezone.utc).isoformat()

    @property
    def telemetry_id(self):
        return self.__telemetry_id

    @telemetry_id.setter
    def telemetry_id(self, val):
        self.__telemetry_id = val

    @property
    def device_id(self) -> str:
        return self.__device_id

    @property
    def point_wkt(self) -> str:
        return self.__point_wkt

    @point_wkt.setter
    def point_wkt(self, valor: str):
        v = valor.strip().upper()
        if not v.startswith("POINT"):
            raise ValueError("point_wkt debe ser un POINT WKT.")
        self.__point_wkt = valor.strip()

    @property
    def speed_kmh(self) -> float:
        return self.__speed_kmh

    @property
    def heading(self) -> float:
        return self.__heading

    @property
    def acc_ignition(self) -> bool:
        return self.__acc_ignition

    @property
    def main_battery(self):
        return self.__main_battery

    @property
    def backup_battery(self):
        return self.__backup_battery

    @property
    def fuel_level(self):
        return self.__fuel_level

    @property
    def odometer_km(self) -> float:
        return self.__odometer_km

    @property
    def dashcam_recording(self) -> bool:
        return self.__dashcam_recording

    @property
    def recorded_at(self) -> str:
        return self.__recorded_at

    def __repr__(self):
        return f"TelemetryLog(device={self.__device_id}, speed={self.__speed_kmh}km/h, odo={self.__odometer_km}km)"
