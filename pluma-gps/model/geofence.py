import uuid
from datetime import datetime, timezone


class Geofence:
    def __init__(self, vehicle_id: str, name: str,
                 area_wkt: str, geofence_id: str = None,
                 created_at: str = None):
        self.__geofence_id = geofence_id or str(uuid.uuid4())
        self.__vehicle_id = vehicle_id
        self.__name = name
        self.area_wkt = area_wkt  # usa setter
        self.__created_at = created_at or datetime.now(timezone.utc).isoformat()

    @property
    def geofence_id(self) -> str:
        return self.__geofence_id

    @property
    def vehicle_id(self) -> str:
        return self.__vehicle_id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def area_wkt(self) -> str:
        return self.__area_wkt

    @area_wkt.setter
    def area_wkt(self, valor: str):
        v = valor.strip().upper()
        if not v.startswith("POLYGON"):
            raise ValueError("area_wkt debe ser un POLYGON WKT.")
        self.__area_wkt = valor.strip()

    @property
    def created_at(self) -> str:
        return self.__created_at

    def check_containment(self, point_wkt: str) -> bool:
        """Nivel 1: bounding box simplificado desde WKT."""
        coords = self._extract_coords(self.__area_wkt)
        if not coords:
            return False
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        px, py = self._extract_point(point_wkt)
        if px is None:
            return False
        return min_lon <= px <= max_lon and min_lat <= py <= max_lat

    @staticmethod
    def _extract_coords(wkt: str) -> list:
        import re
        m = re.findall(r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)', wkt)
        return [(float(a), float(b)) for a, b in m]

    @staticmethod
    def _extract_point(wkt: str) -> tuple:
        import re
        m = re.search(r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)', wkt)
        if m:
            return float(m.group(1)), float(m.group(2))
        return None, None

    def __repr__(self):
        return f"Geofence({self.__name})"
