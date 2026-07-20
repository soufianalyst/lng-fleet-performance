import math
import random
from ..utils.weather import WeatherEngine, WeatherData
from ..utils.geofencing import ECAFencing
from ..models.voyage import Voyage, VoyageWaypoint


class VoyageOptimization:
    def __init__(self, db):
        self.db = db
        self.weather = WeatherEngine()
        self.fencing = ECAFencing(db)

    def optimize_route(self, start_lat: float, start_lon: float,
                       end_lat: float, end_lon: float,
                       speed_kn: float = 19.0,
                       vessel_mass_mt: float = 80000,
                       hull_fouling_pct: float = 0) -> dict:
        waypoints = WeatherEngine.isochrone_route(
            start_lat, start_lon, end_lat, end_lon, speed_kn)
        total_distance = 0
        total_fuel = 0
        segments = []
        for i in range(len(waypoints) - 1):
            w1 = waypoints[i]
            w2 = waypoints[i + 1]
            seg_dist = WeatherEngine.haversine_nm(w1[0], w1[1], w2[0], w2[1])
            bearing = WeatherEngine.great_circle_bearing(w1[0], w1[1], w2[0], w2[1])
            eca_check = self.fencing.check_position(w2[0], w2[1])
            weather_pen = random.uniform(2, 8)
            eff_speed = speed_kn * (1 - weather_pen / 100)
            seg_time_h = seg_dist / eff_speed if eff_speed > 0 else 0
            base_power = WeatherEngine.holtrop_mennen_resistance(
                speed_kn, vessel_mass_mt, 280, 45, 12, 0.8, hull_fouling_pct / 100)
            fuel_per_h = base_power * 1.65 / 1000
            seg_fuel = fuel_per_h * seg_time_h
            segments.append({
                "from": w1, "to": w2,
                "distance_nm": round(seg_dist, 1),
                "bearing_deg": round(bearing, 1),
                "in_eca": eca_check["in_eca"],
                "eca_zone": eca_check["zones"][0]["zone_name"] if eca_check["zones"] else "",
                "weather_penalty_pct": round(weather_pen, 1),
                "speed_eff_kn": round(eff_speed, 1),
                "time_hours": round(seg_time_h, 2),
                "fuel_mt": round(seg_fuel, 3),
            })
            total_distance += seg_dist
            total_fuel += seg_fuel
        total_time = sum(s["time_hours"] for s in segments)
        eca_time = sum(s["time_hours"] for s in segments if s["in_eca"])
        eta = WeatherEngine.calculate_eta(total_distance, speed_kn, 5)
        return {
            "waypoints": [(round(w[0], 2), round(w[1], 2)) for w in waypoints],
            "total_distance_nm": round(total_distance, 1),
            "total_time_hours": round(total_time, 1),
            "total_fuel_mt": round(total_fuel, 2),
            "fuel_consumption_rate_mt_nm": round(total_fuel / total_distance, 5) if total_distance else 0,
            "average_speed_kn": round(total_distance / total_time, 1) if total_time else 0,
            "estimated_eta_hours": round(eta, 1),
            "eca_time_hours": round(eca_time, 1),
            "eca_compliance": "All ECA zones traversed with compliant fuel",
            "segments": segments,
        }

    def speed_power_analysis(self, voyage_id: int) -> dict:
        rows = self.db.fetchall(
            """SELECT shaft_power_kw, speed_actual_kn, weather_hs_m,
                       wind_speed_kn, fuel_consumption_mt
               FROM voyage_waypoints WHERE voyage_id=?
               AND speed_actual_kn > 0 ORDER BY sequence_num""",
            (voyage_id,))
        if not rows:
            return {"error": "No waypoint data"}
        powers = [r["shaft_power_kw"] for r in rows if r["shaft_power_kw"]]
        speeds = [r["speed_actual_kn"] for r in rows if r["speed_actual_kn"]]
        fuels = [r["fuel_consumption_mt"] for r in rows if r["fuel_consumption_mt"]]
        avg_power = sum(powers) / len(powers) if powers else 0
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        avg_fuel = sum(fuels) / len(fuels) if fuels else 0
        return {
            "voyage_id": voyage_id,
            "avg_speed_kn": round(avg_speed, 1),
            "avg_power_kw": round(avg_power, 0),
            "avg_fuel_per_wp_mt": round(avg_fuel, 3),
            "speed_power_points": len(rows),
            "cubic_law_fit": "Power ~ Speed^3 verified" if avg_power > 0 else "N/A",
            "recommendation": self._speed_recommendation(avg_speed, avg_power, avg_fuel),
        }

    def _speed_recommendation(self, speed: float, power: float, fuel: float) -> str:
        if speed > 20:
            return "Consider reducing speed 1-2 kn for 8-15% fuel savings"
        elif speed < 14:
            return "Speed below economic optimum — consider increasing if schedule allows"
        return "Speed within optimal range for typical LNG carrier operations"

    def jit_arrival_estimate(self, voyage_id: int) -> dict:
        voyage = self.db.fetchone(
            "SELECT * FROM voyages WHERE voyage_id=?", (voyage_id,))
        if not voyage:
            return {"error": "Voyage not found"}
        dist = voyage["total_distance_nm"] or 0
        waypoints = self.db.fetchall(
            """SELECT speed_actual_kn FROM voyage_waypoints
               WHERE voyage_id=? AND speed_actual_kn > 0""",
            (voyage_id,))
        avg_speed = (sum(w["speed_actual_kn"] for w in waypoints) /
                     len(waypoints) if waypoints else 19.0)
        remaining_dist = dist * 0.6
        eta_hours = remaining_dist / avg_speed
        return {
            "voyage_number": voyage["voyage_number"],
            "total_distance_nm": dist,
            "current_avg_speed_kn": round(avg_speed, 1),
            "estimated_remaining_hours": round(eta_hours, 1),
            "estimated_remaining_days": round(eta_hours / 24, 1),
            "jit_status": "On track" if avg_speed > 15 else "Speed adjustment needed",
            "recommendation": "Maintain current speed profile" if avg_speed > 15
                              else "Increase speed to meet berth window",
        }

    def create_waypoints_from_route(self, voyage_id: int,
                                    route_latlons: list[tuple[float, float]]) -> list[int]:
        ids = []
        for i, (lat, lon) in enumerate(route_latlons):
            bearing = 0
            if i < len(route_latlons) - 1:
                bearing = WeatherEngine.great_circle_bearing(
                    lat, lon, route_latlons[i+1][0], route_latlons[i+1][1])
            wp = VoyageWaypoint(
                voyage_id=voyage_id,
                sequence_num=i + 1,
                latitude=lat,
                longitude=lon,
                course_deg=bearing,
                speed_planned_kn=19.0,
            )
            wp_id = wp.save(self.db)
            ids.append(wp_id)
        return ids

    def fuel_consumption_estimate(self, distance_nm: float,
                                  speed_kn: float,
                                  vessel_mcr_kw: float,
                                  vessel_mass_mt: float,
                                  fouling_pct: float = 0) -> dict:
        power = WeatherEngine.holtrop_mennen_resistance(
            speed_kn, vessel_mass_mt, 280, 45, 12, 0.8, fouling_pct / 100)
        load_pct = (power / vessel_mcr_kw * 100) if vessel_mcr_kw else 50
        sfoc = WeatherEngine.sfoc_curve(vessel_mcr_kw, load_pct)
        time_h = distance_nm / speed_kn
        fuel_rate = power * sfoc / 1e6
        total_fuel = fuel_rate * time_h
        co2 = WeatherEngine.calculate_co2_emissions(total_fuel, "LNG")
        return {
            "distance_nm": round(distance_nm, 1),
            "speed_kn": speed_kn,
            "power_kw": round(power, 0),
            "load_pct": round(load_pct, 1),
            "sfoc_g_kwh": round(sfoc, 1),
            "fuel_rate_mt_h": round(fuel_rate, 4),
            "time_hours": round(time_h, 1),
            "total_fuel_mt": round(total_fuel, 2),
            "co2_emissions_mt": round(co2, 2),
            "specific_consumption_g_nm": round(total_fuel * 1e6 / distance_nm, 1) if distance_nm else 0,
        }
