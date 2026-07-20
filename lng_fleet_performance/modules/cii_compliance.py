import math
import os
from datetime import datetime
from ..models.compliance import CIIAssessment, EUETSRecord, FuelEURecord
from ..utils.weather import WeatherEngine
from ..utils.analytics_db import get_analytics_connection


class CIICompliance:

    # IMO CII rating boundaries for LNG carriers (gCO2 / mt-nm)
    # 2023 reference C_ref ≈ 6.35 for large LNGC; reduction factors per MEPC.338(76):
    # 2023: 5%, 2024: 7%, 2025: 9%, 2026: 11% vs 2019 reference line.
    # Rating dd-vectors: A ≤ 0.83·C, B ≤ 0.94·C, C ≤ 1.06·C, D ≤ 1.18·C
    CII_RATING_BOUNDARIES_LNG = {
        2023: {"A": 5.30, "B": 6.00, "C": 6.75, "D": 7.50},
        2024: {"A": 5.15, "B": 5.85, "C": 6.55, "D": 7.30},
        2025: {"A": 5.05, "B": 5.70, "C": 6.40, "D": 7.15},
        2026: {"A": 4.90, "B": 5.55, "C": 6.20, "D": 6.95},
    }

    FUEL_EMISSION_FACTORS = {
        "HFO": 3.114, "VLSFO": 3.114, "ULSFO": 3.114,
        "MGO": 3.206, "LNG": 2.750, "B30": 2.980,
    }

    FUEL_ENERGY_CONTENT = {
        "HFO": 40200, "VLSFO": 40200, "ULSFO": 42700,
        "MGO": 42700, "LNG": 50000, "B30": 39000,
    }

    WTW_GHG_FACTORS = {
        "HFO": 3.207, "VLSFO": 3.207, "ULSFO": 3.314,
        "MGO": 3.314, "LNG": 3.560,
    }

    EU_EMISSION_FACTOR = 0.9245

    def __init__(self, db):
        self.db = db
        self._analytics_db = None

    @property
    def analytics_db(self):
        if self._analytics_db is None:
            self._analytics_db = _get_analytics_db()
        return self._analytics_db

    def _analytics_fetchall(self, query: str, params: tuple = ()):
        if self.analytics_db is None:
            return []
        cursor = self.analytics_db.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def _analytics_fetchone(self, query: str, params: tuple = ()):
        if self.analytics_db is None:
            return None
        cursor = self.analytics_db.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def _calculate_cii_from_analytics(self, vessel_id: int, year: int) -> dict:
        """Compute CII from analytics telemetry_daily for vessels without main-DB voyages."""
        analytics_id = f"LNG-{vessel_id:03d}"
        # Get vessel DWT for AER denominator (IMO MEPC.338(76): DWT × distance)
        vessel_row = self._analytics_fetchone(
            "SELECT cargo_capacity_m3 FROM vessel_registry WHERE vessel_id = ?",
            (analytics_id,))
        if vessel_row:
            cargo_m3 = vessel_row["cargo_capacity_m3"] or 174000
            vessel_dwt = cargo_m3 * 0.55  # DWT ≈ 55% of cargo capacity m³ for LNG carriers
        else:
            vessel_dwt = 85000  # Default for typical LNG carrier
        rows = self._analytics_fetchall(
            """SELECT day, co2_total_mt, distance_total_nm, cargo_qty_avg,
                      fuel_consumption_total_kg
               FROM telemetry_daily WHERE vessel_id = ? ORDER BY day""",
            (analytics_id,))
        if not rows:
            return None

        total_co2 = 0
        total_transport_work = 0
        total_distance = 0
        total_cargo = 0
        total_fuel_kg = 0
        for r in rows:
            co2 = r["co2_total_mt"] or 0
            dist = r["distance_total_nm"] or 0
            cargo_mt = (r["cargo_qty_avg"] or 0) / 100.0 * cargo_m3 * 0.45  # fill% → mt
            fuel_kg = r["fuel_consumption_total_kg"] or 0
            total_co2 += co2
            total_distance += dist
            total_cargo += cargo_mt
            total_fuel_kg += fuel_kg
            if dist > 0:
                total_transport_work += vessel_dwt * dist

        if total_transport_work == 0:
            return None

        days_in_data = len(rows)
        cii = total_co2 / total_transport_work * 1000000
        boundaries = self._get_boundaries_for_year(year)
        rating = self._rate_cii(cii, boundaries)
        # Annualize from data period to full year
        annual_factor = 365 / max(days_in_data, 1)
        projected_co2 = total_co2 * annual_factor
        projected_cii = projected_co2 / (total_transport_work * annual_factor) * 1000000
        proj_rating = self._rate_cii(projected_cii, boundaries)
        required_cii = boundaries["C"]
        improvement_needed = 0
        if proj_rating in ("D", "E"):
            improvement_needed = (projected_cii - required_cii) / projected_cii * 100

        return {
            "vessel_id": vessel_id,
            "year": year,
            "source": "analytics",
            "data_days": days_in_data,
            "total_co2_mt": round(total_co2, 2),
            "transport_work_mt_nm": round(total_transport_work, 0),
            "distance_sailed_nm": round(total_distance, 0),
            "cargo_carried_mt": round(total_cargo, 0),
            "total_fuel_mt": round(total_fuel_kg / 1000, 2),
            "cii_calculated": round(cii, 2),
            "cii_required_c": required_cii,
            "cii_rating": rating,
            "rating_boundaries": boundaries,
            "projected_cii": round(projected_cii, 2),
            "projected_rating": proj_rating,
            "days_elapsed_in_year": round(days_in_data, 1),
            "days_at_sea": round(days_in_data, 1),
            "improvement_needed_pct": round(improvement_needed, 1),
            "drift_alert": proj_rating in ("D", "E"),
            "fuel_breakdown": {"LNG": round(total_fuel_kg / 1000, 2)},
            "compliant": rating in ("A", "B", "C"),
        }

    def get_boundaries(self, year: int = 2024) -> dict:
        boundaries = self.CII_RATING_BOUNDARIES_LNG.get(
            year,
            self.CII_RATING_BOUNDARIES_LNG.get(2026)
        )
        return {
            "year": year,
            "ship_type": "LNG Carrier",
            "boundaries": boundaries,
            "description": {
                "A": "Major superior",
                "B": "Minor superior",
                "C": "Moderate",
                "D": "Minor inferior",
                "E": "Inferior",
            },
        }

    def _get_boundaries_for_year(self, year: int) -> dict:
        if year in self.CII_RATING_BOUNDARIES_LNG:
            return self.CII_RATING_BOUNDARIES_LNG[year]
        if year > 2026:
            return self.CII_RATING_BOUNDARIES_LNG[2026]
        return self.CII_RATING_BOUNDARIES_LNG.get(2024)

    def _rate_cii(self, cii: float, boundaries: dict) -> str:
        if cii <= boundaries["A"]:
            return "A"
        elif cii <= boundaries["B"]:
            return "B"
        elif cii <= boundaries["C"]:
            return "C"
        elif cii <= boundaries["D"]:
            return "D"
        return "E"

    def calculate_cii(self, vessel_id: int, year: int = None) -> dict:
        if year is None:
            year = datetime.utcnow().year
        vessel = self.db.fetchone(
            "SELECT * FROM vessels WHERE vessel_id=?", (vessel_id,))
        if not vessel:
            return {"error": "Vessel not found"}
        voyages = self.db.fetchall(
            """SELECT * FROM voyages WHERE vessel_id=? AND status='completed'
               AND strftime('%Y', actual_departure)=?""",
            (vessel_id, str(year)))
        total_co2 = 0
        total_cargo_distance = 0
        total_distance = 0
        total_cargo = 0
        total_days_at_sea = 0
        total_fuel = {"HFO": 0, "VLSFO": 0, "ULSFO": 0, "MGO": 0, "LNG": 0}
        for v in voyages:
            dist = v["total_distance_nm"] or 0
            cargo = v["cargo_quantity_mt"] or 0
            total_co2 += v["co2_total_mt"] or 0
            total_cargo_distance += cargo * dist
            total_distance += dist
            total_cargo += cargo
            if v["actual_departure"] and v["actual_arrival"]:
                try:
                    dep = datetime.fromisoformat(v["actual_departure"])
                    arr = datetime.fromisoformat(v["actual_arrival"])
                    total_days_at_sea += (arr - dep).total_seconds() / 86400
                except (ValueError, TypeError):
                    pass
            total_fuel["HFO"] += v["total_fuel_hfo_mt"] or 0
            total_fuel["VLSFO"] += v["total_fuel_vlsfo_mt"] or 0
            total_fuel["ULSFO"] += v["total_fuel_ulsfo_mt"] or 0
            total_fuel["MGO"] += v["total_fuel_mgo_mt"] or 0
            total_fuel["LNG"] += v["total_fuel_lng_mt"] or 0
        if total_cargo_distance == 0:
            analytics_result = self._calculate_cii_from_analytics(vessel_id, year)
            if analytics_result:
                return analytics_result
            return {"error": "No transport work data", "year": year}
        # CII uses DWT × distance (IMO MEPC.338(76)) — use DWT from vessel record
        dwt = vessel["deadweight_tonnage"] or 85000
        total_transport_work_dwt = dwt * total_distance
        cii = total_co2 / total_transport_work_dwt * 1000000
        boundaries = self._get_boundaries_for_year(year)
        rating = self._rate_cii(cii, boundaries)
        now = datetime.utcnow()
        start_of_year = datetime(year, 1, 1)
        end_of_year = datetime(year, 12, 31, 23, 59, 59)
        days_elapsed = max((now - start_of_year).total_seconds() / 86400, 1)
        days_in_year = (end_of_year - start_of_year).total_seconds() / 86400
        projected_co2 = total_co2 / max(days_elapsed, 1) * days_in_year
        projected_cii = projected_co2 / total_transport_work_dwt * 1000000
        proj_rating = self._rate_cii(projected_cii, boundaries)
        required_cii = boundaries["C"]
        projection_days_remaining = max(days_in_year - days_elapsed, 1)
        improvement_needed = 0
        if proj_rating in ("D", "E"):
            improvement_needed = (projected_cii - required_cii) / projected_cii * 100
        assessment = CIIAssessment(
            vessel_id=vessel_id,
            assessment_year=year,
            assessment_date=datetime.utcnow().isoformat(),
            annual_co2_mt=total_co2,
            annual_cargo_mt_nm=total_cargo_distance,
            cii_calculated=cii,
            cii_required=required_cii,
            cii_rating=rating,
            rating_boundary_a=boundaries["A"],
            rating_boundary_b=boundaries["B"],
            rating_boundary_c=boundaries["C"],
            rating_boundary_d=boundaries["D"],
            projected_year_end_cii=projected_cii,
            projected_rating=proj_rating,
            distance_sailed_nm=total_distance,
            cargo_carried_mt=total_cargo,
            fuel_hfo_mt=total_fuel["HFO"],
            fuel_vlsfo_mt=total_fuel["VLSFO"],
            fuel_ulsfo_mt=total_fuel["ULSFO"],
            fuel_mgo_mt=total_fuel["MGO"],
            fuel_lng_mt=total_fuel["LNG"],
        )
        assessment.save(self.db)
        return {
            "vessel_id": vessel_id,
            "year": year,
            "total_co2_mt": round(total_co2, 2),
            "transport_work_mt_nm": round(total_cargo_distance, 0),
            "distance_sailed_nm": round(total_distance, 0),
            "cargo_carried_mt": round(total_cargo, 0),
            "days_at_sea": round(total_days_at_sea, 1),
            "days_elapsed_in_year": round(days_elapsed, 1),
            "cii_calculated": round(cii, 2),
            "cii_required_c": round(required_cii, 2),
            "cii_rating": rating,
            "rating_boundaries": boundaries,
            "projected_cii": round(projected_cii, 2),
            "projected_rating": proj_rating,
            "projection_days_remaining": round(projection_days_remaining, 0),
            "improvement_needed_pct": round(improvement_needed, 1),
            "fuel_breakdown": total_fuel,
            "compliant": rating in ("A", "B", "C"),
            "drift_alert": proj_rating in ("D", "E"),
        }

    def cii_drift_alert(self, vessel_id: int, year: int = None) -> dict:
        if year is None:
            year = datetime.utcnow().year
        result = self.calculate_cii(vessel_id, year)
        if "error" in result:
            return result
        alerts = []
        if result["drift_alert"]:
            alerts.append({
                "severity": "critical",
                "message": f"CII projected rating is {result['projected_rating']} at year-end. "
                           f"Current projected CII: {result['projected_cii']}, "
                           f"Required for C: {result['cii_required_c']}.",
                "improvement_needed_pct": result["improvement_needed_pct"],
            })
        if result["days_elapsed_in_year"] > 180 and result["cii_rating"] in ("D", "E"):
            alerts.append({
                "severity": "warning",
                "message": f"Mid-year CII rating is {result['cii_rating']}. "
                           f"Action required to avoid consecutive poor ratings.",
            })
        if result["projected_rating"] == "E" and result["days_elapsed_in_year"] > 270:
            alerts.append({
                "severity": "critical",
                "message": "CII E-rating confirmed for year. Consider speed reduction "
                           "or additional cargo to improve transport work denominator.",
            })
        return {
            "vessel_id": vessel_id,
            "year": year,
            "current_rating": result["cii_rating"],
            "projected_rating": result["projected_rating"],
            "alerts": alerts,
            "recommendation": self._generate_cii_recommendations(result),
        }

    def _generate_cii_recommendations(self, result: dict) -> list[str]:
        recs = []
        if result["projected_rating"] in ("D", "E"):
            recs.append("Reduce average speed by 5-10% for remaining voyages")
            recs.append("Maximize cargo per voyage to improve transport work")
            recs.append("Optimize routing to reduce distance without cargo")
        if result["projected_rating"] == "E":
            recs.append("Consider slow steaming for all remaining voyages this year")
            recs.append("Evaluate weather routing to reduce fuel consumption")
        if result["days_elapsed_in_year"] < 90:
            recs.append("Early year projection - low confidence, monitor after more data")
        return recs

    def cii_what_if(self, vessel_id: int, speed_reduction_pct: float = 5,
                    additional_voyages: int = 0) -> dict:
        current = self.db.fetchone(
            """SELECT * FROM cii_assessment WHERE vessel_id=?
               ORDER BY assessment_year DESC LIMIT 1""", (vessel_id,))
        if not current:
            return {"error": "No CII baseline data"}
        base_cii = current["cii_calculated"]
        base_co2 = current["annual_co2_mt"]
        base_cargo_dist = current["annual_cargo_mt_nm"]
        speed_factor = (1 - speed_reduction_pct / 100) ** 3
        adjusted_co2 = base_co2 * speed_factor
        new_cii = adjusted_co2 / base_cargo_dist * 1000000 if base_cargo_dist > 0 else base_cii
        year = current["assessment_year"]
        boundaries = self._get_boundaries_for_year(year)
        new_rating = self._rate_cii(new_cii, boundaries)
        return {
            "scenario": f"Speed reduction {speed_reduction_pct}%",
            "original_cii": round(base_cii, 2),
            "adjusted_cii": round(new_cii, 2),
            "original_rating": current["cii_rating"],
            "adjusted_rating": new_rating,
            "co2_saving_mt": round(base_co2 - adjusted_co2, 2),
            "fuel_saving_mt": round((base_co2 - adjusted_co2) / 2.75, 2),
            "improvement": round((base_cii - new_cii) / base_cii * 100, 1),
        }

    def calculate_eu_ets(self, voyage_id: int, eua_price_eur: float = 80.0) -> dict:
        voyage = self.db.fetchone(
            "SELECT * FROM voyages WHERE voyage_id=?", (voyage_id,))
        if not voyage:
            return {"error": "Voyage not found"}
        vessel = self.db.fetchone(
            "SELECT * FROM vessels WHERE vessel_id=?", (voyage["vessel_id"],))
        total_fuel = (voyage["total_fuel_hfo_mt"] or 0) + (voyage["total_fuel_vlsfo_mt"] or 0) + \
                     (voyage["total_fuel_ulsfo_mt"] or 0) + (voyage["total_fuel_mgo_mt"] or 0)
        lng_fuel = voyage["total_fuel_lng_mt"] or 0
        total_co2_oil = total_fuel * self.EU_EMISSION_FACTOR
        total_co2_lng = lng_fuel * 2.75
        total_co2 = total_co2_oil + total_co2_lng
        allocation = 1.0
        load_port = voyage["load_port"] or ""
        discharge_port = voyage["discharge_port"] or ""
        eu_ports = [
            "rotterdam", "zeebrugge", "sines", "hamburg", "barcelona",
            "marseille", "arzew", "skikda", "algiers", "oran",
            "wilhelmshaven", "brunsbuttel", "bremerhaven", "lillebaelt",
            "gothenburg", "stockholm", "arhus", "copenhagen", "klaipeda",
            "ristinummi", "parnas", "piraeus", "patras", "limassol",
            "vrystaat", "dunkirk", "havre", "bordeaux", "lafito",
            "palma", "valencia", "bilbao", "santander", "tarragona",
            "alicante", "gibraltar",
        ]
        load_in_eu = any(p in load_port.lower() for p in eu_ports)
        discharge_in_eu = any(p in discharge_port.lower() for p in eu_ports)
        if load_in_eu and discharge_in_eu:
            allocation = 1.0
        elif load_in_eu or discharge_in_eu:
            allocation = 0.5
        else:
            allocation = 0
        allocated = total_co2 * allocation
        cost = allocated * eua_price_eur
        record = EUETSRecord(
            voyage_id=voyage_id,
            record_type="voyage_emission",
            eu_port_call=load_port if load_in_eu else (discharge_port if discharge_in_eu else ""),
            voyage_leg_from=load_port,
            voyage_leg_to=discharge_port,
            emissions_mt_co2=total_co2,
            allocation_pct=allocation * 100,
            allocated_emissions_mt=allocated,
            eu_allowance_cost_eur=cost,
        )
        record.save(self.db)
        return {
            "voyage_number": voyage["voyage_number"],
            "total_fuel_mt": round(total_fuel + lng_fuel, 2),
            "total_co2_mt": round(total_co2, 2),
            "eu_allocation_pct": round(allocation * 100, 0),
            "allocated_emissions_mt": round(allocated, 2),
            "eua_price_eur": eua_price_eur,
            "eu_ets_cost_eur": round(cost, 2),
            "eu_ets_cost_usd": round(cost * 1.08, 2),
            "load_in_eu": load_in_eu,
            "discharge_in_eu": discharge_in_eu,
        }

    def eu_ets_annual_summary(self, vessel_id: int, year: int = None,
                              eua_price_eur: float = 80.0) -> dict:
        if year is None:
            year = datetime.utcnow().year
        records = self.db.fetchall(
            """SELECT e.*, v.voyage_number FROM eu_ets_records e
               JOIN voyages v ON e.voyage_id = v.voyage_id
               WHERE v.vessel_id=? AND strftime('%Y', e.created_at)=?""",
            (vessel_id, str(year)))
        total_allocated = sum(r["allocated_emissions_mt"] or 0 for r in records)
        total_cost = sum(r["eu_allowance_cost_eur"] or 0 for r in records)
        surrender_deadline = f"{year + 1}-09-30"
        existing = self.db.fetchone(
            "SELECT * FROM eu_ets_surrender WHERE vessel_id=? AND compliance_year=?",
            (vessel_id, year))
        if not existing:
            self.db.execute(
                """INSERT OR REPLACE INTO eu_ets_surrender
                   (vessel_id, compliance_year, total_allocated_mt, balance_mt,
                    eua_price_eur, total_cost_eur, surrender_deadline, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (vessel_id, year, total_allocated, total_allocated,
                 eua_price_eur, total_cost, surrender_deadline, "pending"))
        return {
            "vessel_id": vessel_id,
            "year": year,
            "total_voyages": len(records),
            "total_allocated_mt": round(total_allocated, 2),
            "eua_price_eur": eua_price_eur,
            "total_cost_eur": round(total_cost, 2),
            "surrender_deadline": surrender_deadline,
            "status": "pending",
        }

    def calculate_fueleu(self, voyage_id: int,
                         reference_g_mj: float = 91.16) -> dict:
        voyage = self.db.fetchone(
            "SELECT * FROM voyages WHERE voyage_id=?", (voyage_id,))
        if not voyage:
            return {"error": "Voyage not found"}
        total_fuel = (voyage["total_fuel_hfo_mt"] or 0) + (voyage["total_fuel_vlsfo_mt"] or 0) + \
                     (voyage["total_fuel_ulsfo_mt"] or 0) + (voyage["total_fuel_mgo_mt"] or 0) + \
                     (voyage["total_fuel_lng_mt"] or 0)
        records = []
        fuel_breakdown = {
            "VLSFO": voyage["total_fuel_vlsfo_mt"] or 0,
            "HFO": voyage["total_fuel_hfo_mt"] or 0,
            "ULSFO": voyage["total_fuel_ulsfo_mt"] or 0,
            "MGO": voyage["total_fuel_mgo_mt"] or 0,
            "LNG": voyage["total_fuel_lng_mt"] or 0,
        }
        total_energy = 0
        total_ghg_co2e = 0
        for fuel_type, mass_mt in fuel_breakdown.items():
            if mass_mt <= 0:
                continue
            energy = mass_mt * self.FUEL_ENERGY_CONTENT.get(fuel_type, 40)
            ghg = mass_mt * self.WTW_GHG_FACTORS.get(fuel_type, 3.207)
            intensity = ghg / energy * 1e6 if energy > 0 else 0
            rec = FuelEURecord(
                voyage_id=voyage_id,
                record_date=voyage["actual_departure"] or "",
                fuel_type=fuel_type,
                fuel_mass_mt=mass_mt,
                energy_mj=energy,
                ghg_wtw_co2e_mt=ghg,
                ghg_intensity_g_mj=intensity,
                reference_value_g_mj=reference_g_mj,
            )
            rec.save(self.db)
            total_energy += energy
            total_ghg_co2e += ghg
            records.append({
                "fuel_type": fuel_type,
                "mass_mt": round(mass_mt, 2),
                "energy_mj": round(energy, 0),
                "ghg_co2e_mt": round(ghg, 2),
                "intensity_g_mj": round(intensity, 2),
            })
        overall_intensity = total_ghg_co2e / total_energy * 1e6 if total_energy > 0 else 0
        compliance = overall_intensity <= reference_g_mj
        penalty = 0
        if not compliance:
            excess = overall_intensity - reference_g_mj
            penalty = excess / 1000 * total_energy * 1200
        return {
            "voyage_number": voyage["voyage_number"],
            "total_energy_mj": round(total_energy, 0),
            "total_ghg_co2e_mt": round(total_ghg_co2e, 2),
            "overall_intensity_g_mj": round(overall_intensity, 2),
            "reference_value_g_mj": reference_g_mj,
            "compliant": compliance,
            "penalty_cost_eur": round(penalty, 2),
            "penalty_rate_eur_per_tco2e": 1200,
            "fuel_details": records,
        }

    def fueleu_trajectory_limit(self, year: int) -> dict:
        trajectory = {
            2025: 91.16, 2026: 89.23, 2027: 87.29,
            2028: 85.36, 2029: 83.43, 2030: 77.44,
            2035: 66.46, 2040: 55.48, 2045: 44.50,
            2050: 18.23,
        }
        limit = trajectory.get(year)
        if limit is None:
            if year < 2025:
                limit = 91.16
            elif year > 2050:
                limit = 0
            else:
                years = sorted(trajectory.keys())
                for i in range(len(years) - 1):
                    if years[i] <= year <= years[i + 1]:
                        frac = (year - years[i]) / (years[i + 1] - years[i])
                        limit = trajectory[years[i]] + frac * (trajectory[years[i + 1]] - trajectory[years[i]])
                        break
        return {"year": year, "reference_limit_g_mj": round(limit, 2)}

    def fueleu_annual_aggregation(self, vessel_id: int, year: int) -> dict:
        records = self.db.fetchall(
            """SELECT f.* FROM fueleu_records f
               JOIN voyages v ON f.voyage_id = v.voyage_id
               WHERE v.vessel_id=? AND strftime('%Y', f.record_date)=?""",
            (vessel_id, str(year)))
        if not records:
            return {"vessel_id": vessel_id, "year": year, "total_energy_mj": 0,
                    "total_ghg_co2e_mt": 0, "overall_intensity_g_mj": 0,
                    "compliant": True, "banking_balance": 0}
        total_energy = sum(r["energy_mj"] or 0 for r in records)
        total_ghg = sum(r["ghg_wtw_co2e_mt"] or 0 for r in records)
        overall_intensity = total_ghg / total_energy * 1e6 if total_energy > 0 else 0
        limit = self.fueleu_trajectory_limit(year)["reference_limit_g_mj"]
        compliant = overall_intensity <= limit
        surplus = max(0, limit - overall_intensity)
        return {
            "vessel_id": vessel_id,
            "year": year,
            "total_energy_mj": round(total_energy, 0),
            "total_ghg_co2e_mt": round(total_ghg, 2),
            "overall_intensity_g_mj": round(overall_intensity, 2),
            "year_limit_g_mj": limit,
            "compliant": compliant,
            "surplus_g_mj": round(surplus, 2),
            "banking_eligible": compliant and surplus > 0,
        }
