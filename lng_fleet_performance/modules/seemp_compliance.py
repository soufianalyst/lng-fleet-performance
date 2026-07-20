from datetime import datetime


class SEEMPCompliance:

    EFFICIENCY_MEASURE_TYPES = [
        "hull_cleaning", "propeller_polishing", "weather_routing",
        "slow_steaming", "trim_optimization", "engine_tuning",
        "waste_heat_recovery", "air_lubrication", "sail_assist",
        "fuel_switch", "voyage_optimization", "shoreside_power",
    ]

    def __init__(self, db):
        self.db = db

    def add_measure(self, vessel_id: int, year: int, measure_type: str,
                    description: str, estimated_saving_mt: float = 0,
                    implementation_date: str = None) -> dict:
        if measure_type not in self.EFFICIENCY_MEASURE_TYPES:
            return {"error": f"Invalid measure type. Valid: {self.EFFICIENCY_MEASURE_TYPES}"}
        self.db.execute(
            """INSERT INTO seemp_measures
               (vessel_id, assessment_year, measure_type, measure_description,
                implementation_date, estimated_fuel_saving_mt, status)
               VALUES (?,?,?,?,?,?,?)""",
            (vessel_id, year, measure_type, description,
             implementation_date or datetime.utcnow().isoformat(),
             estimated_saving_mt, "planned"))
        return {
            "vessel_id": vessel_id,
            "year": year,
            "measure_type": measure_type,
            "description": description,
            "estimated_saving_mt": estimated_saving_mt,
            "status": "planned",
        }

    def get_measures(self, vessel_id: int, year: int = None) -> dict:
        if year is None:
            year = datetime.utcnow().year
        measures = self.db.fetchall(
            """SELECT * FROM seemp_measures
               WHERE vessel_id=? AND assessment_year=?
               ORDER BY implementation_date""",
            (vessel_id, year))
        measure_list = []
        for m in measures:
            measure_list.append({
                "measure_id": m["measure_id"],
                "measure_type": m["measure_type"],
                "description": m["measure_description"],
                "implementation_date": m["implementation_date"],
                "estimated_saving_mt": m["estimated_fuel_saving_mt"],
                "actual_saving_mt": m["actual_fuel_saving_mt"],
                "status": m["status"],
                "verified": bool(m["verified"]),
            })
        total_estimated = sum(m["estimated_fuel_saving_mt"] or 0 for m in measures)
        total_actual = sum(m["actual_fuel_saving_mt"] or 0 for m in measures if m["actual_fuel_saving_mt"])
        return {
            "vessel_id": vessel_id,
            "year": year,
            "measures": measure_list,
            "total_measures": len(measures),
            "total_estimated_saving_mt": round(total_estimated, 2),
            "total_actual_saving_mt": round(total_actual, 2),
        }

    def calculate_improvement(self, vessel_id: int, year: int = None) -> dict:
        if year is None:
            year = datetime.utcnow().year
        baseline = self.db.fetchone(
            """SELECT SUM(fuel_hfo_mt + fuel_vlsfo_mt + fuel_ulsfo_mt +
               fuel_mgo_mt + fuel_lng_mt) as baseline_fuel
               FROM cii_assessment WHERE vessel_id=? AND assessment_year=?""",
            (vessel_id, year - 1))
        current = self.db.fetchone(
            """SELECT SUM(fuel_hfo_mt + fuel_vlsfo_mt + fuel_ulsfo_mt +
               fuel_mgo_mt + fuel_lng_mt) as current_fuel
               FROM cii_assessment WHERE vessel_id=? AND assessment_year=?""",
            (vessel_id, year))
        baseline_fuel = (baseline["baseline_fuel"] or 0) if baseline else 0
        current_fuel = (current["current_fuel"] or 0) if current else 0
        if baseline_fuel > 0:
            improvement_pct = (baseline_fuel - current_fuel) / baseline_fuel * 100
        else:
            improvement_pct = 0
        measures = self.get_measures(vessel_id, year)
        measures_status = {
            "total": measures["total_measures"],
            "planned": sum(1 for m in measures["measures"] if m["status"] == "planned"),
            "implemented": sum(1 for m in measures["measures"] if m["status"] == "implemented"),
            "verified": sum(1 for m in measures["measures"] if m["verified"]),
        }
        return {
            "vessel_id": vessel_id,
            "year": year,
            "baseline_fuel_mt": round(baseline_fuel, 2),
            "current_fuel_mt": round(current_fuel, 2),
            "fuel_saving_mt": round(baseline_fuel - current_fuel, 2),
            "improvement_pct": round(improvement_pct, 1),
            "measures": measures_status,
        }

    def generate_dcs_report(self, vessel_id: int, year: int = None) -> dict:
        if year is None:
            year = datetime.utcnow().year - 1
        vessel = self.db.fetchone(
            "SELECT * FROM vessels WHERE vessel_id=?", (vessel_id,))
        if not vessel:
            return {"error": "Vessel not found"}
        assessments = self.db.fetchall(
            """SELECT * FROM cii_assessment WHERE vessel_id=?
               AND assessment_year=?""",
            (vessel_id, year))
        total_fuel = 0
        total_co2 = 0
        total_distance = 0
        for a in assessments:
            total_fuel += (a["fuel_hfo_mt"] or 0) + (a["fuel_vlsfo_mt"] or 0) + \
                          (a["fuel_ulsfo_mt"] or 0) + (a["fuel_mgo_mt"] or 0) + \
                          (a["fuel_lng_mt"] or 0)
            total_co2 += a["annual_co2_mt"] or 0
            total_distance += a["distance_sailed_nm"] or 0
        dcs_report = {
            "report_type": "IMO DCS",
            "imo_number": vessel["imo_number"],
            "vessel_name": vessel["vessel_name"],
            "reporting_year": year,
            "ship_type": vessel.get("ship_type", "LNG"),
            "gross_tonnage_gt": vessel["gross_tonnage"],
            "total_fuel_consumed_mt": round(total_fuel, 2),
            "total_co2_emissions_mt": round(total_co2, 2),
            "distance_sailed_nm": round(total_distance, 0),
            "hours_underway": round(total_distance / 18, 1),
            "fuel_consumption_per_nm": round(total_fuel / max(total_distance, 1), 4),
            "co2_per_nm": round(total_co2 / max(total_distance, 1), 4),
            "compliance_status": "submitted",
        }
        existing = self.db.fetchone(
            "SELECT * FROM seemp_reports WHERE vessel_id=? AND assessment_year=?",
            (vessel_id, year))
        if existing:
            self.db.execute(
                """UPDATE seemp_reports SET dcs_report_data=?, baseline_co2_mt=?,
                   current_co2_mt=?, updated_at=datetime('now')
                   WHERE report_id=?""",
                (str(dcs_report), total_co2, total_co2, existing["report_id"]))
        else:
            self.db.execute(
                """INSERT INTO seemp_reports
                   (vessel_id, assessment_year, baseline_co2_mt, current_co2_mt,
                    dcs_report_data, submission_status)
                   VALUES (?,?,?,?,?,?)""",
                (vessel_id, year, total_co2, total_co2, str(dcs_report), "draft"))
        return dcs_report
