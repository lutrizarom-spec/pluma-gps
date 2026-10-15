import uuid


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
