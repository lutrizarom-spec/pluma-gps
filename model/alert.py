import uuid
from datetime import datetime, timezone
from enum import Enum


class AlertType(Enum):
    GEOFENCE_EXIT = "GEOFENCE_EXIT"
    GEOFENCE_ENTER = "GEOFENCE_ENTER"
    OVERSPEED = "OVERSPEED"


class AlertStatus(Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class Alert:
    OVERSPEED_DEFAULT_LIMIT = 100.0  # km/h

    def __init__(self, device_id: str, alert_type: AlertType,
                 message: str, status: AlertStatus = AlertStatus.ACTIVE,
                 alert_id: str = None, created_at: str = None):
        self.__alert_id = alert_id or str(uuid.uuid4())
        self.__device_id = device_id
        self.__type = alert_type
        self.__message = message
        self.__status = status
        self.__created_at = created_at or datetime.now(timezone.utc).isoformat()

    @property
    def alert_id(self) -> str:
        return self.__alert_id

    @property
    def device_id(self) -> str:
        return self.__device_id

    @property
    def type(self) -> AlertType:
        return self.__type

    @property
    def message(self) -> str:
        return self.__message

    @property
    def status(self) -> AlertStatus:
        return self.__status

    @property
    def created_at(self) -> str:
        return self.__created_at

    def acknowledge(self):
        if self.__status == AlertStatus.ACKNOWLEDGED:
            raise ValueError("Alerta ya está ACKNOWLEDGED.")
        self.__status = AlertStatus.ACKNOWLEDGED

    @staticmethod
    def evaluate_overspeed(device_id: str, speed_kmh: float,
                           limit: float = None) -> "Alert":
        lim = limit or Alert.OVERSPEED_DEFAULT_LIMIT
        if speed_kmh > lim:
            return Alert(
                device_id=device_id,
                alert_type=AlertType.OVERSPEED,
                message=f"Exceso de velocidad: {speed_kmh} km/h (límite: {lim} km/h)",
            )
        return None

    @staticmethod
    def evaluate_geofence(device_id: str, vehicle_id: str,
                          point_wkt: str, geofences: list,
                          was_inside: bool = None) -> list:
        alerts = []
        for gf in geofences:
            is_inside = gf["geofence"].check_containment(point_wkt)
            prev = gf.get("was_inside", was_inside)
            if prev is not None:
                if prev and not is_inside:
                    alerts.append(Alert(
                        device_id=device_id,
                        alert_type=AlertType.GEOFENCE_EXIT,
                        message=f"Vehículo salió de geocerca '{gf['geofence'].name}'",
                    ))
                elif not prev and is_inside:
                    alerts.append(Alert(
                        device_id=device_id,
                        alert_type=AlertType.GEOFENCE_ENTER,
                        message=f"Vehículo entró a geocerca '{gf['geofence'].name}'",
                    ))
        return alerts

    def __repr__(self):
        return f"Alert({self.__type.value}, {self.__status.value})"
