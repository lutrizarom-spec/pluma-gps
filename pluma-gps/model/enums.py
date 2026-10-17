from enum import Enum


class PlanSubscription(Enum):
    FREE_ADS = "FREE_ADS"
    PRO_MONTHLY = "PRO_MONTHLY"
    ENTERPRISE_FLEET = "ENTERPRISE_FLEET"

    @property
    def max_vehicles(self) -> int:
        return {
            PlanSubscription.FREE_ADS: 1,
            PlanSubscription.PRO_MONTHLY: 5,
            PlanSubscription.ENTERPRISE_FLEET: -1,  # ilimitado
        }[self]


class HardwareLevel(Enum):
    LEVEL_1_BASIC = "LEVEL_1_BASIC"
    LEVEL_2_ADVANCED = "LEVEL_2_ADVANCED"
    LEVEL_3_CANBUS = "LEVEL_3_CANBUS"


class ZoneType(Enum):
    URBANA = "URBANA"
    CARRETERA = "CARRETERA"

    @property
    def speed_limit(self) -> int:
        return {
            ZoneType.URBANA: 80,
            ZoneType.CARRETERA: 120,
        }[self]


class CommandStatus(Enum):
    PENDING_SPEED_CHECK = "PENDING_SPEED_CHECK"
    EXECUTED = "EXECUTED"
    CANCELLED_SAFETY = "CANCELLED_SAFETY"
