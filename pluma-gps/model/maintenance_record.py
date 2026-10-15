import uuid
from datetime import datetime, timezone


class MaintenanceRecord:
    """Gestiona el historial de mantenimiento preventivo y correctivo según odómetro."""

    def __init__(self, vehicle_id: str,
                 maintenance_type: str,
                 odometer_km: float,
                 service_date: str = None,
                 cost: float = 0.0,
                 notes: str = "",
                 record_id: str = None):
        self.__record_id = record_id or str(uuid.uuid4())
        self.__vehicle_id = vehicle_id
        self.__maintenance_type = maintenance_type  # ej: "oil_change", "brake_fluid", "coolant", "tires", "spare_parts"
        self.__odometer_km = odometer_km
        self.__service_date = service_date or datetime.now(timezone.utc).date().isoformat()
        self.__cost = cost
        self.__notes = notes

    @property
    def record_id(self) -> str:
        return self.__record_id

    @property
    def vehicle_id(self) -> str:
        return self.__vehicle_id

    @property
    def maintenance_type(self) -> str:
        return self.__maintenance_type

    @property
    def odometer_km(self) -> float:
        return self.__odometer_km

    @property
    def service_date(self) -> str:
        return self.__service_date

    @property
    def cost(self) -> float:
        return self.__cost

    @property
    def notes(self) -> str:
        return self.__notes

    def __repr__(self):
        return f"MaintenanceRecord({self.__vehicle_id}, {self.__maintenance_type}, {self.__odometer_km}km)"
