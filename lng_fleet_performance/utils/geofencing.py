import math
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ECAZone:
    zone_id: int = 0
    zone_name: str = ""
    zone_type: str = ""
    sox_limit_pct: float = 0.10
    nox_tier: str = ""
    effective_date: str = ""
    status: str = "active"
    boundary_polygon: list[tuple[float, float]] = field(default_factory=list)

    def save(self, db):
        poly_json = json.dumps(self.boundary_polygon) if self.boundary_polygon else ""
        cur = db.execute(
            """INSERT OR REPLACE INTO eca_zones
               (zone_name, zone_type, sox_limit_pct, nox_tier, effective_date,
                boundary_polygon, status)
               VALUES (?,?,?,?,?,?,?)""",
            (self.zone_name, self.zone_type, self.sox_limit_pct,
             self.nox_tier, self.effective_date, poly_json, self.status),
        )
        self.zone_id = cur.lastrowid
        return self.zone_id


PREDEFINED_ECA_ZONES = [
    ECAZone(zone_name="Baltic Sea SECA", zone_type="SOx+NOx",
            sox_limit_pct=0.10, nox_tier="Tier III",
            effective_date="2010-01-01",
            boundary_polygon=[(54.0, 12.0), (66.0, 12.0), (66.0, 30.0),
                              (59.0, 28.0), (55.0, 21.0), (54.0, 12.0)]),
    ECAZone(zone_name="North Sea SECA", zone_type="SOx+NOx",
            sox_limit_pct=0.10, nox_tier="Tier III",
            effective_date="2010-01-01",
            boundary_polygon=[(51.0, -4.0), (62.0, -4.0), (62.0, 10.0),
                              (57.0, 7.0), (53.0, 5.0), (51.0, -4.0)]),
    ECAZone(zone_name="North American ECA", zone_type="SOx+NOx",
            sox_limit_pct=0.10, nox_tier="Tier III",
            effective_date="2012-01-01",
            boundary_polygon=[(24.0, -82.0), (48.0, -82.0), (48.0, -55.0),
                              (40.0, -55.0), (30.0, -65.0), (24.0, -82.0)]),
    ECAZone(zone_name="US Caribbean Sea ECA", zone_type="SOx+NOx",
            sox_limit_pct=0.10, nox_tier="Tier III",
            effective_date="2014-01-01",
            boundary_polygon=[(9.0, -72.0), (22.0, -72.0), (22.0, -59.0),
                              (9.0, -59.0), (9.0, -72.0)]),
    ECAZone(zone_name="Mediterranean Sea ECA (SOx)", zone_type="SOx",
            sox_limit_pct=0.10, nox_tier="",
            effective_date="2025-05-01",
            boundary_polygon=[(30.0, -6.0), (46.0, -6.0), (46.0, 37.0),
                              (30.0, 37.0), (30.0, -6.0)]),
    ECAZone(zone_name="Mediterranean Sea ECA (NOx Tier III)", zone_type="NOx",
            sox_limit_pct=0.10, nox_tier="Tier III",
            effective_date="2028-01-01",
            boundary_polygon=[(30.0, -6.0), (46.0, -6.0), (46.0, 37.0),
                              (30.0, 37.0), (30.0, -6.0)]),
    ECAZone(zone_name="Norwegian ECA", zone_type="SOx+NOx",
            sox_limit_pct=0.10, nox_tier="Tier III",
            effective_date="2010-01-01",
            boundary_polygon=[(58.0, 4.0), (71.0, 4.0), (71.0, 32.0),
                              (58.0, 32.0), (58.0, 4.0)]),
    ECAZone(zone_name="Red Sea ECA", zone_type="SOx",
            sox_limit_pct=0.10, nox_tier="",
            effective_date="2025-05-01",
            boundary_polygon=[(12.0, 32.0), (30.0, 32.0), (30.0, 44.0),
                              (12.0, 44.0), (12.0, 32.0)]),
    ECAZone(zone_name="China DECA", zone_type="SOx+NOx",
            sox_limit_pct=0.50, nox_tier="Tier III",
            effective_date="2022-01-01",
            boundary_polygon=[(18.0, 108.0), (41.0, 108.0), (41.0, 123.0),
                              (18.0, 123.0), (18.0, 108.0)]),
    ECAZone(zone_name="Turkey Marmara ECA", zone_type="SOx",
            sox_limit_pct=0.10, nox_tier="",
            effective_date="2025-06-01",
            boundary_polygon=[(40.0, 26.0), (42.0, 26.0), (42.0, 30.0),
                              (40.0, 30.0), (40.0, 26.0)]),
    ECAZone(zone_name="California CARB", zone_type="SOx+NOx",
            sox_limit_pct=0.10, nox_tier="Tier III",
            effective_date="2014-01-01",
            boundary_polygon=[(32.0, -124.0), (49.0, -124.0), (49.0, -117.0),
                              (32.0, -117.0), (32.0, -124.0)]),
]


class ECAFencing:
    def __init__(self, db=None):
        self.db = db
        self.zones = self._load_zones()

    def _load_zones(self) -> list[ECAZone]:
        if self.db:
            rows = self.db.fetchall("SELECT * FROM eca_zones WHERE status='active'")
            zones = []
            for r in rows:
                poly_str = r["boundary_polygon"] or "[]"
                try:
                    poly = json.loads(poly_str)
                except (json.JSONDecodeError, TypeError):
                    poly = []
                zones.append(ECAZone(
                    zone_id=r["zone_id"], zone_name=r["zone_name"],
                    zone_type=r["zone_type"], sox_limit_pct=r["sox_limit_pct"],
                    nox_tier=r["nox_tier"] or "",
                    effective_date=r["effective_date"] or "",
                    boundary_polygon=poly,
                ))
            return zones if zones else PREDEFINED_ECA_ZONES
        return PREDEFINED_ECA_ZONES

    @staticmethod
    def point_in_polygon(lat: float, lon: float,
                         polygon: list[tuple[float, float]]) -> bool:
        if len(polygon) < 3:
            return False
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            yi, xi = polygon[i]
            yj, xj = polygon[j]
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def check_position(self, lat: float, lon: float) -> dict:
        in_eca_zones = []
        for zone in self.zones:
            if zone.boundary_polygon and self.point_in_polygon(lat, lon, zone.boundary_polygon):
                in_eca_zones.append({
                    "zone_name": zone.zone_name,
                    "sox_limit_pct": zone.sox_limit_pct,
                    "nox_tier": zone.nox_tier,
                    "zone_type": zone.zone_type,
                })
        return {
            "in_eca": len(in_eca_zones) > 0,
            "zones": in_eca_zones,
            "sox_compliant_fuel": "ULSFO" if in_eca_zones else "VLSFO",
            "requires_nox_tier3": any(z["nox_tier"] == "Tier III" for z in in_eca_zones),
        }

    def distance_to_eca(self, lat: float, lon: float) -> list[dict]:
        distances = []
        for zone in self.zones:
            min_dist = float('inf')
            if zone.boundary_polygon:
                for p_lat, p_lon in zone.boundary_polygon:
                    d = haversine_nm(lat, lon, p_lat, p_lon)
                    min_dist = min(min_dist, d)
            distances.append({
                "zone_name": zone.zone_name,
                "distance_nm": round(min_dist, 1),
                "in_zone": min_dist < 1,
            })
        return sorted(distances, key=lambda x: x["distance_nm"])


def haversine_nm(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 0.539957
