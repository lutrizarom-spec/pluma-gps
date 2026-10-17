import uuid
from datetime import datetime, timezone


class WorkSchedule:
    """Gestiona horarios laborales y corte automático del sistema eléctrico fuera de jornada."""

    def __init__(self, vehicle_id: str,
                 start_time: str = "08:00",
                 end_time: str = "19:00",
                 auto_cutoff_enabled: bool = True,
                 schedule_id: str = None):
        self.__schedule_id = schedule_id or str(uuid.uuid4())
        self.__vehicle_id = vehicle_id
        self.__start_time = start_time
        self.__end_time = end_time
        self.__auto_cutoff_enabled = auto_cutoff_enabled

    @property
    def schedule_id(self) -> str:
        return self.__schedule_id

    @property
    def vehicle_id(self) -> str:
        return self.__vehicle_id

    @property
    def start_time(self) -> str:
        return self.__start_time

    @property
    def end_time(self) -> str:
        return self.__end_time

    @property
    def auto_cutoff_enabled(self) -> bool:
        return self.__auto_cutoff_enabled

    def is_within_schedule(self, current_time: str) -> bool:
        """Determina si la hora actual (formato HH:MM) se encuentra dentro de la jornada laboral."""
        return self.__start_time <= current_time <= self.__end_time

    def should_activate_electrical_cutoff(self, current_time: str) -> bool:
        """Determina si debe cortarse el sistema eléctrico por encontrarse fuera de horario."""
        if not self.__auto_cutoff_enabled:
            return False
        return not self.is_within_schedule(current_time)

    def __repr__(self):
        return f"WorkSchedule({self.__vehicle_id}, {self.__start_time}-{self.__end_time})"


class VehicleAssignment:
    """Asigna un vehículo (patente) a un conductor en un rango de vigencia."""

    _OPEN_END = "9999-12-31T23:59:59"

    def __init__(self, vehicle_id: str, user_id: str, start_time: str,
                 end_time: str = None, is_replacement: bool = False,
                 authorized_by: str = "", created_at: str = None,
                 assignment_id: str = None):
        self.__assignment_id = assignment_id or str(uuid.uuid4())
        self.__vehicle_id = vehicle_id
        self.__user_id = user_id
        self.__start_time = start_time
        self.__end_time = end_time
        self.__is_replacement = bool(is_replacement)
        self.__authorized_by = authorized_by
        self.__created_at = created_at or datetime.now(timezone.utc).isoformat()

    @property
    def assignment_id(self) -> str:
        return self.__assignment_id

    @property
    def vehicle_id(self) -> str:
        return self.__vehicle_id

    @property
    def user_id(self) -> str:
        return self.__user_id

    @property
    def start_time(self) -> str:
        return self.__start_time

    @property
    def end_time(self) -> str:
        return self.__end_time

    @property
    def is_replacement(self) -> bool:
        return self.__is_replacement

    @property
    def authorized_by(self) -> str:
        return self.__authorized_by

    @property
    def created_at(self) -> str:
        return self.__created_at

    def is_active(self, moment: str = None) -> bool:
        """True si el momento (ISO) cae dentro de [start_time, end_time)."""
        moment = moment or datetime.now(timezone.utc).isoformat()
        if moment < self.__start_time:
            return False
        return self.__end_time is None or moment < self.__end_time

    def overlaps(self, start: str, end: str = None) -> bool:
        """Detecta solapamiento con otro rango de vigencia."""
        other_end = end or self._OPEN_END
        my_end = self.__end_time or self._OPEN_END
        return self.__start_time < other_end and start < my_end

    def __repr__(self):
        return (f"VehicleAssignment({self.__vehicle_id} -> {self.__user_id}, "
                f"{self.__start_time}..{self.__end_time or 'abierto'})")
