from datetime import datetime


class EEXICompliance:

    REQUIRED_EEXI_LNG = {
        (0, 20000, 2024): 8.2,
        (20000, 40000, 2024): 7.5,
        (40000, 60000, 2024): 6.8,
        (60000, 80000, 2024): 6.2,
        (80000, 100000, 2024): 5.8,
        (100000, 150000, 2024): 5.4,
        (150000, 200000, 2024): 5.1,
        (200000, float('inf'), 2024): 4.9,
    }

    def __init__(self, db):
        self.db = db

    def get_required_eexi(self, dwt: float, year: int = 2024) -> float:
        for (dwt_min, dwt_max, y), val in self.REQUIRED_EEXI_LNG.items():
            if dwt_min <= dwt < dwt_max and year >= y:
                return val
        return 5.0

    def calculate_eexi(self, vessel_id: int) -> dict:
        vessel = self.db.fetchone(
            "SELECT * FROM vessels WHERE vessel_id=?", (vessel_id,))
        if not vessel:
            return {"error": "Vessel not found"}
        dwt = vessel["deadweight_tonnage"] or 85000
        mcr = vessel["engine_mcr_kw"] or 35000
        design_speed = vessel["design_speed_kn"] or 19.5
        eexi_stored = vessel["eexi_value"] or 0
        if eexi_stored > 0:
            attained_eexi = eexi_stored
        else:
            sfoc = 170  # g/kWh reference SFOC
            fuel_emission_factor = 3.114  # kgCO2/kgfuel for LNG
            # EEXI = (MCR × SFOC × FEC) / (DWT × V_ref) × 1000
            co2_per_hour = mcr * sfoc * fuel_emission_factor / 1e6  # tCO2/h
            reference_speed = design_speed
            attained_eexi = co2_per_hour / (reference_speed * dwt) * 1e6 if reference_speed > 0 else 0
        required_eexi = self.get_required_eexi(dwt)
        compliant = attained_eexi <= required_eexi
        headroom = required_eexi - attained_eexi
        headroom_pct = headroom / required_eexi * 100 if required_eexi > 0 else 0
        existing = self.db.fetchone(
            "SELECT * FROM eexi_assessment WHERE vessel_id=? ORDER BY assessment_year DESC LIMIT 1",
            (vessel_id,))
        if existing and existing["assessment_year"] == datetime.utcnow().year:
            self.db.execute(
                """UPDATE eexi_assessment SET attained_eexi=?, required_eexi=?,
                   compliant=?, created_at=datetime('now')
                   WHERE assessment_id=?""",
                (attained_eexi, required_eexi, int(compliant), existing["assessment_id"]))
        else:
            self.db.execute(
                """INSERT INTO eexi_assessment
                   (vessel_id, assessment_year, attained_eexi, required_eexi,
                    compliant, reference_speed_kn, reference_power_kw)
                   VALUES (?,?,?,?,?,?,?)""",
                (vessel_id, datetime.utcnow().year, attained_eexi, required_eexi,
                 int(compliant), design_speed, mcr))
        return {
            "vessel_id": vessel_id,
            "vessel_name": vessel["vessel_name"],
            "deadweight_tonnage_dwt": round(dwt, 0),
            "mcr_kw": round(mcr, 0),
            "design_speed_kn": round(design_speed, 1),
            "attained_eexi": round(attained_eexi, 2),
            "required_eexi": round(required_eexi, 2),
            "compliant": compliant,
            "headroom": round(headroom, 2),
            "headroom_pct": round(headroom_pct, 1),
            "epl_impact": "No EPL needed" if compliant else "EPL required",
        }

    def configure_epl(self, vessel_id: int, power_limit_pct: float = 80,
                      eca_zone: str = None, reason: str = "") -> dict:
        if not (10 <= power_limit_pct <= 100):
            return {"error": "Power limit must be between 10% and 100%"}
        self.db.execute(
            """INSERT INTO epl_config
               (vessel_id, eca_zone_name, power_limit_pct, override_active,
                override_reason, configured_date, configured_by)
               VALUES (?,?,?,?,?,?,?)""",
            (vessel_id, eca_zone, power_limit_pct, 0, reason,
             datetime.utcnow().isoformat(), "system"))
        return {
            "vessel_id": vessel_id,
            "power_limit_pct": power_limit_pct,
            "eca_zone": eca_zone,
            "reason": reason,
            "status": "configured",
        }

    def get_epl_status(self, vessel_id: int) -> dict:
        configs = self.db.fetchall(
            "SELECT * FROM epl_config WHERE vessel_id=? ORDER BY configured_date DESC",
            (vessel_id,))
        vessel = self.db.fetchone(
            "SELECT * FROM vessels WHERE vessel_id=?", (vessel_id,))
        mcr = vessel["main_engine_mcr_kw"] if vessel else 35000
        active = [c for c in configs if c["power_limit_pct"] < 100]
        epl_configurations = []
        for c in configs:
            epl_configurations.append({
                "eca_zone": c["eca_zone_name"],
                "power_limit_pct": c["power_limit_pct"],
                "limited_power_kw": round(mcr * c["power_limit_pct"] / 100, 0),
                "override_active": bool(c["override_active"]),
                "reason": c["override_reason"],
                "configured_date": c["configured_date"],
            })
        return {
            "vessel_id": vessel_id,
            "total_configs": len(configs),
            "active_epl_count": len(active),
            "configurations": epl_configurations,
        }

    def verify_epl_compliance(self, vessel_id: int, current_lat: float,
                              current_lon: float, current_power_pct: float = 100) -> dict:
        eca_check = self.db.fetchone(
            "SELECT * FROM eca_zones WHERE status='active'")
        epl = self.db.fetchall(
            "SELECT * FROM epl_config WHERE vessel_id=?", (vessel_id,))
        active_epl = [c for c in epl if c["power_limit_pct"] < 100]
        if not active_epl:
            return {
                "vessel_id": vessel_id,
                "epl_active": False,
                "current_power_pct": current_power_pct,
                "compliant": True,
                "message": "No EPL restriction configured",
            }
        highest_limit = max(c["power_limit_pct"] for c in active_epl)
        compliant = current_power_pct <= highest_limit
        return {
            "vessel_id": vessel_id,
            "epl_active": True,
            "power_limit_pct": highest_limit,
            "current_power_pct": current_power_pct,
            "compliant": compliant,
            "over_by_pct": round(max(0, current_power_pct - highest_limit), 1),
            "message": "Compliant" if compliant else f"Exceeding EPL by {max(0, current_power_pct - highest_limit):.1f}%",
        }
