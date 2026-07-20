from dataclasses import dataclass
from typing import Optional


@dataclass
class EnginePerformance:
    voyage_id: int
    record_timestamp: str
    engine_id: Optional[int] = None
    engine_mode: str = "gas"
    engine_speed_rpm: float = 0
    shaft_power_kw: float = 0
    mcr_pct: float = 0
    sfoc_actual_g_kwh: float = 0
    sfoc_reference_g_kwh: float = 0
    sfoc_delta: float = 0
    thermal_efficiency_pct: float = 0
    cylinder_pmax_bar: float = 0
    cylinder_pcomp_bar: float = 0
    exhaust_temp_cyl_avg: float = 0
    turbocharger_speed_rpm: float = 0
    turbocharger_surge_margin: float = 0
    scavenge_air_temp_c: float = 0
    scavenge_air_pressure_bar: float = 0
    fuel_injection_timing_deg: float = 0
    pilot_fuel_pct: float = 0
    gas_admission_valve_timing: float = 0
    methane_slip_g_kwh: float = 0
    specific_bog_consumption: float = 0

    def save(self, db):
        cur = db.execute(
            """INSERT INTO engine_performance
               (voyage_id, record_timestamp, engine_mode, engine_speed_rpm,
                shaft_power_kw, mcr_pct, sfoc_actual_g_kwh, sfoc_reference_g_kwh,
                sfoc_delta, thermal_efficiency_pct, cylinder_pmax_bar,
                cylinder_pcomp_bar, exhaust_temp_cyl_avg, turbocharger_speed_rpm,
                turbocharger_surge_margin, scavenge_air_temp_c, scavenge_air_pressure_bar,
                fuel_injection_timing_deg, pilot_fuel_pct, gas_admission_valve_timing,
                methane_slip_g_kwh, specific_bog_consumption)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.voyage_id, self.record_timestamp, self.engine_mode,
             self.engine_speed_rpm, self.shaft_power_kw, self.mcr_pct,
             self.sfoc_actual_g_kwh, self.sfoc_reference_g_kwh, self.sfoc_delta,
             self.thermal_efficiency_pct, self.cylinder_pmax_bar,
             self.cylinder_pcomp_bar, self.exhaust_temp_cyl_avg,
             self.turbocharger_speed_rpm, self.turbocharger_surge_margin,
             self.scavenge_air_temp_c, self.scavenge_air_pressure_bar,
             self.fuel_injection_timing_deg, self.pilot_fuel_pct,
             self.gas_admission_valve_timing, self.methane_slip_g_kwh,
             self.specific_bog_consumption),
        )
        self.engine_id = cur.lastrowid
        return self.engine_id

    @classmethod
    def list_by_voyage(cls, db, voyage_id: int) -> list["EnginePerformance"]:
        rows = db.fetchall(
            "SELECT * FROM engine_performance WHERE voyage_id=? ORDER BY record_timestamp",
            (voyage_id,),
        )
        result = []
        for r in rows:
            result.append(cls(
                engine_id=r["engine_id"], voyage_id=r["voyage_id"],
                record_timestamp=r["record_timestamp"],
                engine_mode=r["engine_mode"] or "gas",
                engine_speed_rpm=r["engine_speed_rpm"] or 0,
                shaft_power_kw=r["shaft_power_kw"] or 0,
                mcr_pct=r["mcr_pct"] or 0,
                sfoc_actual_g_kwh=r["sfoc_actual_g_kwh"] or 0,
                sfoc_reference_g_kwh=r["sfoc_reference_g_kwh"] or 0,
                sfoc_delta=r["sfoc_delta"] or 0,
                thermal_efficiency_pct=r["thermal_efficiency_pct"] or 0,
                cylinder_pmax_bar=r["cylinder_pmax_bar"] or 0,
                cylinder_pcomp_bar=r["cylinder_pcomp_bar"] or 0,
                exhaust_temp_cyl_avg=r["exhaust_temp_cyl_avg"] or 0,
                turbocharger_speed_rpm=r["turbocharger_speed_rpm"] or 0,
                turbocharger_surge_margin=r["turbocharger_surge_margin"] or 0,
                scavenge_air_temp_c=r["scavenge_air_temp_c"] or 0,
                scavenge_air_pressure_bar=r["scavenge_air_pressure_bar"] or 0,
                fuel_injection_timing_deg=r["fuel_injection_timing_deg"] or 0,
                pilot_fuel_pct=r["pilot_fuel_pct"] or 0,
                gas_admission_valve_timing=r["gas_admission_valve_timing"] or 0,
                methane_slip_g_kwh=r["methane_slip_g_kwh"] or 0,
                specific_bog_consumption=r["specific_bog_consumption"] or 0,
            ))
        return result

    @classmethod
    def get_latest(cls, db, voyage_id: int) -> Optional["EnginePerformance"]:
        rows = cls.list_by_voyage(db, voyage_id)
        return rows[-1] if rows else None


@dataclass
class AuxiliaryEngine:
    voyage_id: int
    record_timestamp: str
    aux_id: Optional[int] = None
    aux_engine_number: int = 1
    load_kw: float = 0
    load_pct: float = 0
    sfoc_g_kwh: float = 0
    fuel_type: str = "VLSFO"
    running_hours: float = 0
    exhaust_temp_c: float = 0
    oil_pressure_bar: float = 0
    coolant_temp_c: float = 0

    def save(self, db):
        cur = db.execute(
            """INSERT INTO auxiliary_engines
               (voyage_id, record_timestamp, aux_engine_number, load_kw,
                load_pct, sfoc_g_kwh, fuel_type, running_hours,
                exhaust_temp_c, oil_pressure_bar, coolant_temp_c)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (self.voyage_id, self.record_timestamp, self.aux_engine_number,
             self.load_kw, self.load_pct, self.sfoc_g_kwh, self.fuel_type,
             self.running_hours, self.exhaust_temp_c, self.oil_pressure_bar,
             self.coolant_temp_c),
        )
        self.aux_id = cur.lastrowid
        return self.aux_id
