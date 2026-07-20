from dataclasses import dataclass
from typing import Optional


@dataclass
class CargoRecord:
    voyage_id: int
    tank_id: int
    record_timestamp: str
    cargo_id: Optional[int] = None
    cargo_level_pct: float = 0
    cargo_volume_m3: float = 0
    cargo_mass_mt: float = 0
    cargo_temperature_k: float = 111.0
    cargo_pressure_bar: float = 1.0
    cargo_composition_methane: float = 0.87
    cargo_composition_ethane: float = 0.08
    cargo_composition_propane: float = 0.03
    cargo_composition_butane: float = 0.01
    cargo_composition_nitrogen: float = 0.01
    bog_generation_rate_kg_h: float = 0
    tank_top_temp_k: float = 0
    tank_mid_temp_k: float = 0
    tank_bottom_temp_k: float = 0
    stratification_index: float = 0
    rollover_risk_level: str = "low"

    def save(self, db):
        cur = db.execute(
            """INSERT INTO cargo_records
               (voyage_id, tank_id, record_timestamp, cargo_level_pct,
                cargo_volume_m3, cargo_mass_mt, cargo_temperature_k, cargo_pressure_bar,
                cargo_composition_methane, cargo_composition_ethane,
                cargo_composition_propane, cargo_composition_butane,
                cargo_composition_nitrogen, bog_generation_rate_kg_h,
                tank_top_temp_k, tank_mid_temp_k, tank_bottom_temp_k,
                stratification_index, rollover_risk_level)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.voyage_id, self.tank_id, self.record_timestamp,
             self.cargo_level_pct, self.cargo_volume_m3, self.cargo_mass_mt,
             self.cargo_temperature_k, self.cargo_pressure_bar,
             self.cargo_composition_methane, self.cargo_composition_ethane,
             self.cargo_composition_propane, self.cargo_composition_butane,
             self.cargo_composition_nitrogen, self.bog_generation_rate_kg_h,
             self.tank_top_temp_k, self.tank_mid_temp_k, self.tank_bottom_temp_k,
             self.stratification_index, self.rollover_risk_level),
        )
        self.cargo_id = cur.lastrowid
        return self.cargo_id

    @classmethod
    def list_by_voyage(cls, db, voyage_id: int) -> list["CargoRecord"]:
        rows = db.fetchall(
            """SELECT * FROM cargo_records WHERE voyage_id=?
               ORDER BY record_timestamp DESC, tank_id""",
            (voyage_id,),
        )
        return [cls(**{k: r[k] for k in r.keys()}) for r in rows]

    @classmethod
    def get_latest_by_tank(cls, db, voyage_id: int, tank_id: int) -> Optional["CargoRecord"]:
        row = db.fetchone(
            """SELECT * FROM cargo_records
               WHERE voyage_id=? AND tank_id=?
               ORDER BY record_timestamp DESC LIMIT 1""",
            (voyage_id, tank_id),
        )
        return cls(**{k: row[k] for k in row.keys()}) if row else None


@dataclass
class BORDailySummary:
    voyage_id: int
    summary_date: str
    bor_id: Optional[int] = None
    avg_bor_pct_day: float = 0
    measured_bor_pct_day: float = 0
    energy_balance_bor: float = 0
    bog_to_engine_mt: float = 0
    bog_to_reliquefaction_mt: float = 0
    bog_to_gcu_mt: float = 0
    reliquefaction_power_kw: float = 0
    reliquefaction_cop: float = 0
    tank_avg_temp_k: float = 0
    sea_water_temp_k: float = 0
    ambient_temp_k: float = 0

    def save(self, db):
        cur = db.execute(
            """INSERT INTO bor_daily_summary
               (voyage_id, summary_date, avg_bor_pct_day, measured_bor_pct_day,
                energy_balance_bor, bog_to_engine_mt, bog_to_reliquefaction_mt,
                bog_to_gcu_mt, reliquefaction_power_kw, reliquefaction_cop,
                tank_avg_temp_k, sea_water_temp_k, ambient_temp_k)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.voyage_id, self.summary_date, self.avg_bor_pct_day,
             self.measured_bor_pct_day, self.energy_balance_bor,
             self.bog_to_engine_mt, self.bog_to_reliquefaction_mt,
             self.bog_to_gcu_mt, self.reliquefaction_power_kw,
             self.reliquefaction_cop, self.tank_avg_temp_k,
             self.sea_water_temp_k, self.ambient_temp_k),
        )
        self.bor_id = cur.lastrowid
        return self.bor_id

    @classmethod
    def list_by_voyage(cls, db, voyage_id: int) -> list["BORDailySummary"]:
        rows = db.fetchall(
            "SELECT * FROM bor_daily_summary WHERE voyage_id=? ORDER BY summary_date",
            (voyage_id,),
        )
        return [cls(**{k: r[k] for k in r.keys()}) for r in rows]
