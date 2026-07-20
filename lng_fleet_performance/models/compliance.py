from dataclasses import dataclass
from typing import Optional


@dataclass
class CIIAssessment:
    vessel_id: int
    assessment_year: int
    assessment_date: str
    cii_id: Optional[int] = None
    annual_co2_mt: float = 0
    annual_cargo_mt_nm: float = 0
    cii_calculated: float = 0
    cii_required: float = 0
    cii_rating: str = ""
    rating_boundary_a: float = 0
    rating_boundary_b: float = 0
    rating_boundary_c: float = 0
    rating_boundary_d: float = 0
    projected_year_end_cii: float = 0
    projected_rating: str = ""
    distance_sailed_nm: float = 0
    cargo_carried_mt: float = 0
    port_time_hours: float = 0
    sea_time_hours: float = 0
    fuel_hfo_mt: float = 0
    fuel_vlsfo_mt: float = 0
    fuel_ulsfo_mt: float = 0
    fuel_mgo_mt: float = 0
    fuel_lng_mt: float = 0
    bog_consumed_mt: float = 0

    def save(self, db):
        cur = db.execute(
            """INSERT INTO cii_assessment
               (vessel_id, assessment_year, assessment_date, annual_co2_mt,
                annual_cargo_mt_nm, cii_calculated, cii_required, cii_rating,
                rating_boundary_a, rating_boundary_b, rating_boundary_c, rating_boundary_d,
                projected_year_end_cii, projected_rating, distance_sailed_nm,
                cargo_carried_mt, port_time_hours, sea_time_hours,
                fuel_hfo_mt, fuel_vlsfo_mt, fuel_ulsfo_mt, fuel_mgo_mt,
                fuel_lng_mt, bog_consumed_mt)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.vessel_id, self.assessment_year, self.assessment_date,
             self.annual_co2_mt, self.annual_cargo_mt_nm, self.cii_calculated,
             self.cii_required, self.cii_rating, self.rating_boundary_a,
             self.rating_boundary_b, self.rating_boundary_c, self.rating_boundary_d,
             self.projected_year_end_cii, self.projected_rating,
             self.distance_sailed_nm, self.cargo_carried_mt,
             self.port_time_hours, self.sea_time_hours,
             self.fuel_hfo_mt, self.fuel_vlsfo_mt, self.fuel_ulsfo_mt,
             self.fuel_mgo_mt, self.fuel_lng_mt, self.bog_consumed_mt),
        )
        self.cii_id = cur.lastrowid
        return self.cii_id

    @classmethod
    def list_by_vessel(cls, db, vessel_id: int) -> list["CIIAssessment"]:
        rows = db.fetchall(
            "SELECT * FROM cii_assessment WHERE vessel_id=? ORDER BY assessment_year DESC",
            (vessel_id,),
        )
        return [cls(**{k: r[k] for k in r.keys()}) for r in rows]

    @classmethod
    def get_latest(cls, db, vessel_id: int) -> Optional["CIIAssessment"]:
        rows = cls.list_by_vessel(db, vessel_id)
        return rows[0] if rows else None


@dataclass
class EUETSRecord:
    voyage_id: int
    record_type: str
    ets_id: Optional[int] = None
    eu_port_call: str = ""
    voyage_leg_from: str = ""
    voyage_leg_to: str = ""
    emission_factor_mt: float = 0
    emissions_mt_co2: float = 0
    allocation_pct: float = 0
    allocated_emissions_mt: float = 0
    eu_allowance_cost_eur: float = 0
    verification_status: str = "pending"
    verification_body: str = ""
    surrender_deadline: str = ""

    def save(self, db):
        cur = db.execute(
            """INSERT INTO eu_ets_records
               (voyage_id, record_type, eu_port_call, voyage_leg_from, voyage_leg_to,
                emission_factor_mt, emissions_mt_co2, allocation_pct,
                allocated_emissions_mt, eu_allowance_cost_eur, verification_status,
                verification_body, surrender_deadline)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.voyage_id, self.record_type, self.eu_port_call,
             self.voyage_leg_from, self.voyage_leg_to, self.emission_factor_mt,
             self.emissions_mt_co2, self.allocation_pct,
             self.allocated_emissions_mt, self.eu_allowance_cost_eur,
             self.verification_status, self.verification_body,
             self.surrender_deadline),
        )
        self.ets_id = cur.lastrowid
        return self.ets_id

    @classmethod
    def list_by_voyage(cls, db, voyage_id: int) -> list["EUETSRecord"]:
        rows = db.fetchall(
            "SELECT * FROM eu_ets_records WHERE voyage_id=?", (voyage_id,),
        )
        return [cls(**{k: r[k] for k in r.keys()}) for r in rows]


@dataclass
class FuelEURecord:
    voyage_id: int
    record_date: str
    fuel_type: str
    fuel_mass_mt: float
    fueleu_id: Optional[int] = None
    energy_mj: float = 0
    ghg_wtw_co2e_mt: float = 0
    ghg_intensity_g_mj: float = 0
    reference_value_g_mj: float = 91.16
    compliance_balance: float = 0
    penalty_cost_eur: float = 0

    def save(self, db):
        cur = db.execute(
            """INSERT INTO fueleu_records
               (voyage_id, record_date, fuel_type, fuel_mass_mt, energy_mj,
                ghg_wtw_co2e_mt, ghg_intensity_g_mj, reference_value_g_mj,
                compliance_balance, penalty_cost_eur)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (self.voyage_id, self.record_date, self.fuel_type, self.fuel_mass_mt,
             self.energy_mj, self.ghg_wtw_co2e_mt, self.ghg_intensity_g_mj,
             self.reference_value_g_mj, self.compliance_balance,
             self.penalty_cost_eur),
        )
        self.fueleu_id = cur.lastrowid
        return self.fueleu_id

    @classmethod
    def list_by_voyage(cls, db, voyage_id: int) -> list["FuelEURecord"]:
        rows = db.fetchall(
            "SELECT * FROM fueleu_records WHERE voyage_id=? ORDER BY record_date",
            (voyage_id,),
        )
        return [cls(**{k: r[k] for k in r.keys()}) for r in rows]
