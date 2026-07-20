from datetime import datetime
from typing import Optional


class ReportGenerator:
    def __init__(self, db):
        self.db = db

    def voyage_summary(self, voyage_id: int) -> dict:
        v = self.db.fetchone("SELECT * FROM voyages WHERE voyage_id=?", (voyage_id,))
        if not v:
            return {"error": "Voyage not found"}
        vessel = self.db.fetchone(
            "SELECT * FROM vessels WHERE vessel_id=?", (v["vessel_id"],))
        bor = self.db.fetchall(
            "SELECT * FROM bor_daily_summary WHERE voyage_id=? ORDER BY summary_date",
            (voyage_id,))
        engines = self.db.fetchall(
            """SELECT COUNT(*) as cnt, AVG(shaft_power_kw) as avg_power,
               AVG(sfoc_actual_g_kwh) as avg_sfoc
               FROM engine_performance WHERE voyage_id=?""",
            (voyage_id,))
        eca = self.db.fetchone(
            "SELECT SUM(eca_time_hours) as total_eca FROM voyages WHERE voyage_id=?",
            (voyage_id,))

        total_fuel = (v["total_fuel_hfo_mt"] + v["total_fuel_vlsfo_mt"] +
                      v["total_fuel_ulsfo_mt"] + v["total_fuel_mgo_mt"] +
                      v["total_fuel_lng_mt"])
        avg_bor = (sum(b["avg_bor_pct_day"] or 0 for b in bor) / len(bor)
                   if bor else 0)

        return {
            "voyage": v["voyage_number"],
            "vessel": vessel["vessel_name"] if vessel else "N/A",
            "route": f"{v['load_port']} → {v['discharge_port']}",
            "status": v["status"],
            "distance_nm": v["total_distance_nm"],
            "total_fuel_mt": round(total_fuel, 2),
            "co2_emissions_mt": v["co2_total_mt"],
            "avg_bor_pct_day": round(avg_bor, 4),
            "avg_power_kw": engines[0]["avg_power"] if engines else 0,
            "avg_sfoc": engines[0]["avg_sfoc"] if engines else 0,
            "eca_hours": eca["total_eca"] if eca else 0,
            "eu_ets_applicable": v["eu_ets_applicable"],
        }

    def vessel_cii_summary(self, vessel_id: int) -> dict:
        vessel = self.db.fetchone(
            "SELECT * FROM vessels WHERE vessel_id=?", (vessel_id,))
        if not vessel:
            return {"error": "Vessel not found"}
        cii = self.db.fetchall(
            "SELECT * FROM cii_assessment WHERE vessel_id=? ORDER BY assessment_year DESC",
            (vessel_id,))
        voyages = self.db.fetchall(
            "SELECT * FROM voyages WHERE vessel_id=? AND status='completed'",
            (vessel_id,))
        return {
            "vessel": vessel["vessel_name"],
            "imo": vessel["imo_number"],
            "eexi": vessel["eexi_value"],
            "design_speed": vessel["design_speed_kn"],
            "cii_assessments": len(cii),
            "latest_cii": {
                "year": cii[0]["assessment_year"] if cii else None,
                "rating": cii[0]["cii_rating"] if cii else None,
                "value": cii[0]["cii_calculated"] if cii else None,
                "projected": cii[0]["projected_rating"] if cii else None,
            } if cii else None,
            "completed_voyages": len(voyages),
        }

    def eca_compliance_report(self, vessel_id: int) -> dict:
        events = self.db.fetchall(
            """SELECT * FROM eca_events WHERE vessel_id=?
               ORDER BY event_timestamp DESC LIMIT 50""",
            (vessel_id,))
        switches = self.db.fetchall(
            """SELECT * FROM fuel_switch_log WHERE vessel_id=?
               ORDER BY switch_timestamp DESC LIMIT 50""",
            (vessel_id,))
        total_entries = len(events)
        compliant = sum(1 for e in events if e["nox_compliant"])
        return {
            "vessel_id": vessel_id,
            "total_eca_entries": total_entries,
            "compliant_entries": compliant,
            "compliance_rate": round(compliant / total_entries * 100, 1) if total_entries else 100,
            "fuel_switches": len(switches),
            "recent_events": [
                {"timestamp": e["event_timestamp"], "type": e["event_type"],
                 "zone": e["eca_zone_name"], "compliant": e["nox_compliant"]}
                for e in events[:10]
            ],
        }

    def charter_party_performance(self, voyage_id: int) -> dict:
        cp = self.db.fetchone(
            "SELECT * FROM charter_party WHERE voyage_id=?", (voyage_id,))
        perf = self.db.fetchall(
            "SELECT * FROM charter_performance WHERE voyage_id=? ORDER BY record_date",
            (voyage_id,))
        off_hire = self.db.fetchall(
            "SELECT * FROM off_hire_events WHERE voyage_id=?", (voyage_id,))
        if not cp:
            return {"error": "No charter party data for this voyage"}
        avg_speed_dev = (sum(p["speed_deviation_pct"] or 0 for p in perf) / len(perf)
                         if perf else 0)
        avg_consumption_dev = (sum(p["consumption_deviation_pct"] or 0 for p in perf) /
                               len(perf) if perf else 0)
        total_off_hire = sum(o["net_off_hire_hours"] or 0 for o in off_hire)
        return {
            "voyage_id": voyage_id,
            "charterer": cp["charterer"],
            "speed_warranted": cp["speed_warranted_kn"],
            "consumption_warranted": cp["consumption_warranted_mt_day"],
            "avg_speed_deviation_pct": round(avg_speed_dev, 2),
            "avg_consumption_deviation_pct": round(avg_consumption_dev, 2),
            "total_off_hire_hours": total_off_hire,
            "performance_compliant": abs(avg_speed_dev) < 3 and abs(avg_consumption_dev) < 3,
            "off_hire_events": len(off_hire),
        }

    def fleet_overview(self) -> list[dict]:
        vessels = self.db.fetchall("SELECT * FROM vessels ORDER BY vessel_name")
        result = []
        for v in vessels:
            active = self.db.fetchone(
                """SELECT COUNT(*) as cnt FROM voyages
                   WHERE vessel_id=? AND status='in_progress'""",
                (v["vessel_id"],))
            completed = self.db.fetchone(
                """SELECT COUNT(*) as cnt FROM voyages
                   WHERE vessel_id=? AND status='completed'""",
                (v["vessel_id"],))
            cii = self.db.fetchone(
                """SELECT * FROM cii_assessment
                   WHERE vessel_id=? ORDER BY assessment_year DESC LIMIT 1""",
                (v["vessel_id"],))
            result.append({
                "vessel_id": v["vessel_id"],
                "name": v["vessel_name"],
                "imo": v["imo_number"],
                "flag": v["flag_state"],
                "type": v["propulsion_type"],
                "dwt": v["deadweight_tonnage"],
                "cargo_cap_m3": v["cargo_capacity_m3"],
                "active_voyages": active["cnt"] if active else 0,
                "completed_voyages": completed["cnt"] if completed else 0,
                "latest_cii_rating": cii["cii_rating"] if cii else None,
            })
        return result

    def emissions_summary(self, vessel_id: int, year: int = None) -> dict:
        if year is None:
            year = datetime.utcnow().year
        voyages = self.db.fetchall(
            """SELECT * FROM voyages
               WHERE vessel_id=? AND status='completed'
               AND strftime('%Y', actual_departure)=?""",
            (vessel_id, str(year)))
        total_co2 = sum(v["co2_total_mt"] or 0 for v in voyages)
        total_hfo = sum(v["total_fuel_hfo_mt"] or 0 for v in voyages)
        total_vlsfo = sum(v["total_fuel_vlsfo_mt"] or 0 for v in voyages)
        total_ulsfo = sum(v["total_fuel_ulsfo_mt"] or 0 for v in voyages)
        total_mgo = sum(v["total_fuel_mgo_mt"] or 0 for v in voyages)
        total_lng = sum(v["total_fuel_lng_mt"] or 0 for v in voyages)
        total_bog = sum(v["total_bog_mt"] or 0 for v in voyages)
        total_cargo = sum(v["cargo_quantity_mt"] or 0 for v in voyages)
        total_distance = sum(v["total_distance_nm"] or 0 for v in voyages)
        return {
            "vessel_id": vessel_id,
            "year": year,
            "voyages": len(voyages),
            "total_co2_mt": round(total_co2, 2),
            "total_fuel_mt": round(total_hfo + total_vlsfo + total_ulsfo +
                                   total_mgo + total_lng, 2),
            "fuel_breakdown": {
                "HFO": round(total_hfo, 2),
                "VLSFO": round(total_vlsfo, 2),
                "ULSFO": round(total_ulsfo, 2),
                "MGO": round(total_mgo, 2),
                "LNG": round(total_lng, 2),
                "BOG": round(total_bog, 2),
            },
            "total_cargo_mt": round(total_cargo, 2),
            "total_distance_nm": round(total_distance, 2),
        }

    def print_report(self, title: str, data: dict):
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}")
        self._print_dict(data, indent=0)
        print(f"{'='*70}\n")

    def _print_dict(self, data: dict, indent: int = 0):
        prefix = "  " * indent
        for k, v in data.items():
            if isinstance(v, dict):
                print(f"{prefix}{k}:")
                self._print_dict(v, indent + 1)
            elif isinstance(v, list):
                print(f"{prefix}{k}: [{len(v)} items]")
                for item in v[:5]:
                    if isinstance(item, dict):
                        self._print_dict(item, indent + 1)
                        print()
                    else:
                        print(f"{prefix}  - {item}")
            else:
                print(f"{prefix}{k}: {v}")
