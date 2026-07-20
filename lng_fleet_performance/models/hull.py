from dataclasses import dataclass
from typing import Optional


@dataclass
class HullPerformance:
    vessel_id: int
    record_date: str
    hull_id: Optional[int] = None
    speed_kn: float = 0
    shaft_power_kw: float = 0
    wind_speed_kn: float = 0
    wind_direction_deg: float = 0
    current_speed_kn: float = 0
    current_direction_deg: float = 0
    sea_state: int = 0
    water_temp_k: float = 0
    water_depth_m: float = 0
    displacement_mt: float = 0
    draft_fwd_m: float = 0
    draft_aft_m: float = 0
    trim_m: float = 0
    reference_power_kw: float = 0
    power_deviation_pct: float = 0
    friction_coeff_delta: float = 0
    equivalent_roughness_mm: float = 0
    fouling_level: str = "clean"
    qpc_trending: float = 0.85
    hull_cleaning_due: int = 0

    def save(self, db):
        cur = db.execute(
            """INSERT INTO hull_performance
               (vessel_id, record_date, speed_kn, shaft_power_kw,
                wind_speed_kn, wind_direction_deg, current_speed_kn,
                current_direction_deg, sea_state, water_temp_k, water_depth_m,
                displacement_mt, draft_fwd_m, draft_aft_m, trim_m,
                reference_power_kw, power_deviation_pct, friction_coeff_delta,
                equivalent_roughness_mm, fouling_level, qpc_trending,
                hull_cleaning_due)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.vessel_id, self.record_date, self.speed_kn,
             self.shaft_power_kw, self.wind_speed_kn, self.wind_direction_deg,
             self.current_speed_kn, self.current_direction_deg, self.sea_state,
             self.water_temp_k, self.water_depth_m, self.displacement_mt,
             self.draft_fwd_m, self.draft_aft_m, self.trim_m,
             self.reference_power_kw, self.power_deviation_pct,
             self.friction_coeff_delta, self.equivalent_roughness_mm,
             self.fouling_level, self.qpc_trending, self.hull_cleaning_due),
        )
        self.hull_id = cur.lastrowid
        return self.hull_id

    @classmethod
    def list_by_vessel(cls, db, vessel_id: int, limit: int = 100) -> list["HullPerformance"]:
        rows = db.fetchall(
            """SELECT * FROM hull_performance WHERE vessel_id=?
               ORDER BY record_date DESC LIMIT ?""",
            (vessel_id, limit),
        )
        return [cls(
            hull_id=r["hull_id"], vessel_id=r["vessel_id"],
            record_date=r["record_date"], speed_kn=r["speed_kn"] or 0,
            shaft_power_kw=r["shaft_power_kw"] or 0,
            wind_speed_kn=r["wind_speed_kn"] or 0,
            wind_direction_deg=r["wind_direction_deg"] or 0,
            current_speed_kn=r["current_speed_kn"] or 0,
            current_direction_deg=r["current_direction_deg"] or 0,
            sea_state=r["sea_state"] or 0,
            water_temp_k=r["water_temp_k"] or 0,
            water_depth_m=r["water_depth_m"] or 0,
            displacement_mt=r["displacement_mt"] or 0,
            draft_fwd_m=r["draft_fwd_m"] or 0,
            draft_aft_m=r["draft_aft_m"] or 0,
            trim_m=r["trim_m"] or 0,
            reference_power_kw=r["reference_power_kw"] or 0,
            power_deviation_pct=r["power_deviation_pct"] or 0,
            friction_coeff_delta=r["friction_coeff_delta"] or 0,
            equivalent_roughness_mm=r["equivalent_roughness_mm"] or 0,
            fouling_level=r["fouling_level"] or "clean",
            qpc_trending=r["qpc_trending"] or 0.85,
            hull_cleaning_due=r["hull_cleaning_due"] or 0,
        ) for r in rows]
