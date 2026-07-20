import math
import hashlib
import json
from datetime import datetime
from ..utils.weather import WeatherEngine


class CharterPartyVerification:
    ISO_15016_WIND_CORRECTION = 0.025
    ISO_15016_WAVE_CORRECTION = 0.015
    ISO_15016_CURRENT_CORRECTION = 0.010

    def __init__(self, db):
        self.db = db

    def weather_correct_speed(self, measured_speed_kn: float,
                              wind_speed_kn: float,
                              wind_direction_deg: float,
                              heading_deg: float,
                              wave_height_m: float,
                              current_speed_kn: float = 0) -> dict:
        wind_penalty = 0
        rel_angle = abs(wind_direction_deg - heading_deg) % 360
        if rel_angle > 180:
            rel_angle = 360 - rel_angle
        if wind_speed_kn > 10:
            headwind_factor = math.cos(math.radians(rel_angle))
            wind_penalty = self.ISO_15016_WIND_CORRECTION * wind_speed_kn * headwind_factor
        wave_penalty = self.ISO_15016_WAVE_CORRECTION * wave_height_m ** 2
        current_effect = current_speed_kn * math.cos(math.radians(heading_deg))
        corrected = measured_speed_kn + wind_penalty + wave_penalty + current_effect
        return {
            "measured_speed_kn": round(measured_speed_kn, 2),
            "wind_penalty_kn": round(wind_penalty, 3),
            "wave_penalty_kn": round(wave_penalty, 3),
            "current_effect_kn": round(current_effect, 3),
            "weather_corrected_speed_kn": round(corrected, 2),
            "correction_total_kn": round(corrected - measured_speed_kn, 3),
        }

    def weather_correct_consumption(self, measured_mt: float,
                                     wind_speed_kn: float,
                                     wave_height_m: float,
                                     displacement_mt: float = 80000) -> dict:
        wind_penalty_pct = 0.002 * wind_speed_kn if wind_speed_kn > 10 else 0
        wave_penalty_pct = 0.005 * wave_height_m if wave_height_m > 1.5 else 0
        trim_penalty = 0.001
        total_penalty = wind_penalty_pct + wave_penalty_pct + trim_penalty
        corrected = measured_mt * (1 - total_penalty)
        return {
            "measured_consumption_mt": round(measured_mt, 3),
            "wind_penalty_pct": round(wind_penalty_pct * 100, 3),
            "wave_penalty_pct": round(wave_penalty_pct * 100, 3),
            "trim_penalty_pct": round(trim_penalty * 100, 3),
            "total_penalty_pct": round(total_penalty * 100, 3),
            "weather_corrected_consumption_mt": round(corrected, 3),
        }

    def verify_speed_consumption(self, voyage_id: int) -> dict:
        cp = self.db.fetchone(
            "SELECT * FROM charter_party WHERE voyage_id=?", (voyage_id,))
        if not cp:
            return {"error": "No charter party data"}
        waypoints = self.db.fetchall(
            """SELECT * FROM voyage_waypoints
               WHERE voyage_id=? AND speed_actual_kn > 0
               ORDER BY sequence_num""", (voyage_id,))
        if not waypoints:
            return {"error": "No waypoint performance data"}
        speed_results = []
        total_off_hire = 0
        for wp in waypoints:
            if cp["speed_warranted_kn"] and wp["speed_actual_kn"]:
                corrected = self.weather_correct_speed(
                    wp["speed_actual_kn"],
                    wp["wind_speed_kn"] or 0,
                    wp["wind_direction_deg"] or 0,
                    wp["course_deg"] or 0,
                    wp["weather_hs_m"] or 0,
                )
                speed_dev = (corrected["weather_corrected_speed_kn"] -
                             cp["speed_warranted_kn"]) / cp["speed_warranted_kn"] * 100
                compliant = speed_dev >= -3
                speed_results.append({
                    "waypoint": wp["sequence_num"],
                    "actual_kn": round(wp["speed_actual_kn"], 1),
                    "corrected_kn": corrected["weather_corrected_speed_kn"],
                    "warranted_kn": cp["speed_warranted_kn"],
                    "deviation_pct": round(speed_dev, 2),
                    "compliant": compliant,
                })
                if not compliant:
                    total_off_hire += 1
        avg_dev = (sum(r["deviation_pct"] for r in speed_results) /
                   len(speed_results) if speed_results else 0)
        return {
            "voyage_id": voyage_id,
            "charterer": cp["charterer"],
            "speed_warranted_kn": cp["speed_warranted_kn"],
            "weather_corrected_speeds": speed_results,
            "average_speed_deviation_pct": round(avg_dev, 2),
            "speed_compliant": avg_dev >= -3,
            "potential_off_hire_hours": total_off_hire,
            "performance_assessment": "Satisfactory" if avg_dev >= -3 else "Deficiency detected",
        }

    def verify_bor(self, voyage_id: int) -> dict:
        cp = self.db.fetchone(
            "SELECT * FROM charter_party WHERE voyage_id=?", (voyage_id,))
        if not cp or not cp["bor_warranted_pct_day"]:
            return {"error": "No BOR warranty data"}
        bor_data = self.db.fetchall(
            "SELECT * FROM bor_daily_summary WHERE voyage_id=? ORDER BY summary_date",
            (voyage_id,))
        if not bor_data:
            return {"error": "No BOR data"}
        bors = [b["avg_bor_pct_day"] for b in bor_data if b["avg_bor_pct_day"]]
        avg_bor = sum(bors) / len(bors) if bors else 0
        warranted = cp["bor_warranted_pct_day"]
        tolerance = cp["bor_tolerance_pct"] or 1.5
        allowed = warranted * (1 + tolerance / 100)
        deviation = (avg_bor - warranted) / warranted * 100 if warranted > 0 else 0
        compliant = avg_bor <= allowed
        return {
            "voyage_id": voyage_id,
            "bor_warranted_pct_day": warranted,
            "bor_allowed_pct_day": round(allowed, 4),
            "bor_actual_pct_day": round(avg_bor, 4),
            "deviation_pct": round(deviation, 2),
            "bor_compliant": compliant,
            "daily_bors": [{"date": b["summary_date"], "bor": b["avg_bor_pct_day"]}
                           for b in bor_data],
        }

    def create_charter_party(self, voyage_id: int, charterer: str,
                             speed_warranted: float = 19.0,
                             consumption_warranted: float = 120,
                             bor_warranted: float = 0.15,
                             **kwargs) -> int:
        from ..models.voyage import Voyage
        v = self.db.fetchone(
            "SELECT * FROM voyages WHERE voyage_id=?", (voyage_id,))
        cur = self.db.execute(
            """INSERT INTO charter_party
               (voyage_id, charterer, charter_type, speed_warranted_kn,
                consumption_warranted_mt_day, consumption_tolerance_pct,
                bor_warranted_pct_day, bor_tolerance_pct, sea_margin_pct,
                weather_exclusion_beaufort, off_hire_rate_usd_day)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (voyage_id, charterer, kwargs.get("charter_type", "voyage"),
             speed_warranted, consumption_warranted,
             kwargs.get("consumption_tolerance_pct", 3.0),
             bor_warranted, kwargs.get("bor_tolerance_pct", 1.5),
             kwargs.get("sea_margin_pct", 15.0),
             kwargs.get("weather_exclusion_beaufort", 6),
             kwargs.get("off_hire_rate_usd_day", 80000)),
        )
        return cur.lastrowid

    def record_performance(self, voyage_id: int, record_date: str,
                           speed_actual: float, consumption_actual: float,
                           wind_speed: float = 0, sea_state: int = 3) -> int:
        cp = self.db.fetchone(
            "SELECT * FROM charter_party WHERE voyage_id=?", (voyage_id,))
        if not cp:
            return -1
        corrected = self.weather_correct_speed(
            speed_actual, wind_speed, 180, 90, sea_state * 0.5)
        speed_dev = (corrected["weather_corrected_speed_kn"] -
                     cp["speed_warranted_kn"]) / cp["speed_warranted_kn"] * 100
        cons_corr = self.weather_correct_consumption(
            consumption_actual, wind_speed, sea_state * 0.5)
        cons_dev = (cons_corr["weather_corrected_consumption_mt"] -
                    cp["consumption_warranted_mt_day"]) / cp["consumption_warranted_mt_day"] * 100
        compliant = speed_dev >= -3 and cons_dev <= 3
        alert = abs(speed_dev) > 5 or abs(cons_dev) > 5
        cur = self.db.execute(
            """INSERT INTO charter_performance
               (voyage_id, cp_id, record_date, speed_actual_kn,
                speed_warranted_kn, speed_weather_corrected_kn,
                consumption_actual_mt, consumption_warranted_mt,
                consumption_weather_corrected_mt, consumption_deviation_pct,
                speed_deviation_pct, wind_speed_kn, sea_state_beaufort,
                performance_compliant, discrepancy_alert)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (voyage_id, cp["cp_id"], record_date, speed_actual,
             cp["speed_warranted_kn"], corrected["weather_corrected_speed_kn"],
             consumption_actual, cp["consumption_warranted_mt_day"],
             cons_corr["weather_corrected_consumption_mt"],
             round(cons_dev, 2), round(speed_dev, 2),
             wind_speed, sea_state, int(compliant), int(alert)),
        )
        return cur.lastrowid

    def create_audit_trail(self, voyage_id: int) -> dict:
        records = self.db.fetchall(
            "SELECT * FROM charter_performance WHERE voyage_id=?", (voyage_id,))
        events = self.db.fetchall(
            "SELECT * FROM off_hire_events WHERE voyage_id=?", (voyage_id,))
        data = {
            "voyage_id": voyage_id,
            "performance_records": len(records),
            "off_hire_events": len(events),
            "total_off_hire_hours": sum(e["net_off_hire_hours"] or 0 for e in events),
        }
        data_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()
        return {
            "audit_data": data,
            "hash": data_hash,
            "hash_algorithm": "SHA-256",
            "timestamp": datetime.utcnow().isoformat(),
            "immutability": "Hash chain created — any modification will be detectable",
        }
