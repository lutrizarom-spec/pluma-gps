import uuid
from datetime import datetime, timezone
from model.enums import CommandStatus


class CutEngineCommand:
    SAFETY_SPEED_LIMIT = 20.0  # km/h

    def __init__(self, device_id: str,
                 status: CommandStatus = CommandStatus.PENDING_SPEED_CHECK,
                 doors_locked: bool = False,
                 windows_closed: bool = False,
                 requested_at: str = None,
                 executed_at: str = None,
                 speed_at_execution: float = None,
                 command_id: str = None):
        self.__command_id = command_id or str(uuid.uuid4())
        self.__device_id = device_id
        self.__status = status
        self.__doors_locked = doors_locked
        self.__windows_closed = windows_closed
        self.__requested_at = requested_at or datetime.now(timezone.utc).isoformat()
        self.__executed_at = executed_at
        self.__speed_at_execution = speed_at_execution

    @property
    def command_id(self) -> str:
        return self.__command_id

    @property
    def device_id(self) -> str:
        return self.__device_id

    @property
    def status(self) -> CommandStatus:
        return self.__status

    @property
    def doors_locked(self) -> bool:
        return self.__doors_locked

    @property
    def windows_closed(self) -> bool:
        return self.__windows_closed

    @property
    def requested_at(self) -> str:
        return self.__requested_at

    @property
    def executed_at(self):
        return self.__executed_at

    @property
    def speed_at_execution(self):
        return self.__speed_at_execution

    def activate_anti_theft_lock(self):
        """Activa el sensor/actuador de cierre perimetral (puertas y ventanas)."""
        self.__doors_locked = True
        self.__windows_closed = True

    @staticmethod
    def validate_safety_speed(speed_kmh: float) -> bool:
        """Retorna True si la velocidad es segura (≤ 20 km/h) conforme a la ley chilena."""
        return speed_kmh <= CutEngineCommand.SAFETY_SPEED_LIMIT

    def mark_as_executed(self, speed_kmh: float):
        if not self.validate_safety_speed(speed_kmh):
            raise ValueError(
                f"Velocidad {speed_kmh} km/h excede límite seguro "
                f"de {self.SAFETY_SPEED_LIMIT} km/h."
            )
        self.__status = CommandStatus.EXECUTED
        self.__executed_at = datetime.now(timezone.utc).isoformat()
        self.__speed_at_execution = speed_kmh

    def cancel_due_to_timeout(self):
        self.__status = CommandStatus.CANCELLED_SAFETY

    def __repr__(self):
        return f"CutEngineCommand({self.__status.value}, doors_locked={self.__doors_locked})"
