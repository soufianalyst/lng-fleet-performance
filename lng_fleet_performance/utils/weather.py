import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WeatherData:
    timestamp: str
    latitude: float
    longitude: float
    wind_speed_kn: float = 0
    wind_direction_deg: float = 0
    significant_wave_height_m: float = 0
    wave_period_s: float = 0
    wave_direction_deg: float = 0
    sea_water_temp_k: float = 0
    air_temp_k: float = 0
    air_pressure_hpa: float = 1013.25
    visibility_nm: float = 10
    current_speed_kn: float = 0
    current_direction_deg: float = 0
    sea_ice_coverage_pct: float = 0
    source: str = "GFS"


class WeatherEngine:
    # Fuel oil CO2 emission factors (tCO2/t fuel)
    EMISSION_FACTORS = {
        "HFO": 3.114,
        "VLSFO": 3.114,
        "ULSFO": 3.114,
        "MGO": 3.206,
        "MDO": 3.206,
        "LNG": 2.750,
        "LNG_DUAL_FUEL": 2.750,
        "B30": 2.980,
    }

    # Fuel lower heating values (MJ/kg)
    LHV = {
        "HFO": 40.2,
        "VLSFO": 40.2,
        "ULSFO": 42.7,
        "MGO": 42.7,
        "MDO": 42.7,
        "LNG": 50.0,
        "B30": 39.0,
    }

    # Well-to-Wake CO2e factors (tCO2e/t fuel)
    WTW_FACTORS = {
        "HFO": 3.207,
        "VLSFO": 3.207,
        "ULSFO": 3.314,
        "MGO": 3.314,
        "LNG": 3.560,
    }

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0  # Earth radius in km
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return WeatherEngine.haversine_distance(lat1, lon1, lat2, lon2) * 0.539957

    @staticmethod
    def great_circle_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlon_r = math.radians(lon2 - lon1)
        y = math.sin(dlon_r) * math.cos(lat2_r)
        x = (math.cos(lat1_r) * math.sin(lat2_r) -
             math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon_r))
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    @staticmethod
    def holtrop_mennen_resistance(speed_kn: float, displacement_mt: float,
                                  lwl_m: float, beam_m: float,
                                  draft_m: float, cb: float,
                                  fouling_factor: float = 0) -> float:
        v_ms = speed_kn * 0.5144
        design_speed = 19.0
        base_power = displacement_mt ** 0.667 * design_speed ** 3 * 0.000125
        speed_ratio = v_ms / (design_speed * 0.5144)
        power = base_power * speed_ratio ** 3
        power *= (1 + fouling_factor)
        return max(power, 100)

    @staticmethod
    def wind_resistance额外(speed_kn: float, wind_speed_kn: float,
                            wind_direction_deg: float, heading_deg: float,
                            frontal_area_m2: float) -> float:
        v_ship = speed_kn * 0.5144
        v_wind_true = wind_speed_kn * 0.5144
        rel_angle = math.radians(wind_direction_deg - heading_deg)
        v_wind_rel = math.sqrt(
            v_wind_true ** 2 + v_ship ** 2 -
            2 * v_wind_true * v_ship * math.cos(rel_angle)
        )
        rho_air = 1.225
        cx = 0.8
        r_wind = 0.5 * rho_air * (v_wind_rel ** 2) * frontal_area_m2 * cx
        return r_wind / 1000

    @staticmethod
    def sfoc_curve(engine_mcr_kw: float, load_pct: float,
                   sfoc_min: float = 165.0) -> float:
        x = load_pct / 100.0
        sfoc = sfoc_min + 80 * ((x - 0.85) ** 2) + 30 * ((x - 0.85) ** 4)
        return sfoc

    @staticmethod
    def boustrophedon_route(start_lat: float, start_lon: float,
                            end_lat: float, end_lon: float,
                            grid_step_deg: float = 0.25) -> list[tuple[float, float]]:
        waypoints = []
        num_steps = max(int(WeatherEngine.haversine_nm(
            start_lat, start_lon, end_lat, end_lon) / 20), 5)
        for i in range(num_steps + 1):
            t = i / num_steps
            lat = start_lat + t * (end_lat - start_lat)
            lon = start_lon + t * (end_lon - start_lon)
            waypoints.append((lat, lon))
        return waypoints

    @staticmethod
    def isochrone_route(start_lat: float, start_lon: float,
                        end_lat: float, end_lon: float,
                        speed_kn: float = 19.0,
                        num_isochrones: int = 20,
                        num_branches: int = 12) -> list[tuple[float, float]]:
        current_lat = start_lat
        current_lon = start_lon
        waypoints = [(current_lat, current_lon)]
        for _ in range(num_isochrones):
            best_lat, best_lon = current_lat, current_lon
            best_cost = float('inf')
            dist_to_end = WeatherEngine.haversine_nm(
                current_lat, current_lon, end_lat, end_lon)
            for b in range(num_branches):
                bearing = b * (360.0 / num_branches)
                dist_step = speed_kn * 6  # 6 hours
                dist_step = min(dist_step, dist_to_end * 1.1)
                R = 6371.0 * 0.539957
                d = dist_step / R
                lat1 = math.radians(current_lat)
                lon1 = math.radians(current_lon)
                brng = math.radians(bearing)
                lat2 = math.asin(math.sin(lat1) * math.cos(d) +
                                 math.cos(lat1) * math.sin(d) * math.cos(brng))
                lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(d) * math.cos(lat1),
                                         math.cos(d) - math.sin(lat1) * math.sin(lat2))
                new_lat = math.degrees(lat2)
                new_lon = math.degrees(lon2)
                remaining = WeatherEngine.haversine_nm(new_lat, new_lon, end_lat, end_lon)
                cost = remaining + abs(remaining - dist_to_end) * 0.3
                if cost < best_cost:
                    best_cost = cost
                    best_lat, best_lon = new_lat, new_lon
            current_lat, current_lon = best_lat, best_lon
            waypoints.append((current_lat, current_lon))
            if WeatherEngine.haversine_nm(current_lat, current_lon, end_lat, end_lon) < 50:
                break
        waypoints.append((end_lat, end_lon))
        return waypoints

    @staticmethod
    def calculate_eta(distance_nm: float, speed_kn: float,
                      weather_penalty_pct: float = 0) -> float:
        effective_speed = speed_kn * (1 - weather_penalty_pct / 100)
        return distance_nm / effective_speed

    @staticmethod
    def weather_penalty_factor(hs_m: float, wind_kn: float) -> float:
        penalty = 0
        if hs_m > 2.5:
            penalty += (hs_m - 2.5) * 2.0
        if wind_kn > 20:
            penalty += (wind_kn - 20) * 0.3
        return min(penalty, 20)

    @staticmethod
    def calculate_co2_emissions(fuel_mt: float, fuel_type: str) -> float:
        ef = WeatherEngine.EMISSION_FACTORS.get(fuel_type, 3.114)
        return fuel_mt * ef

    @staticmethod
    def calculate_co2e_wtw(fuel_mt: float, fuel_type: str) -> float:
        f = WeatherEngine.WTW_FACTORS.get(fuel_type, 3.207)
        return fuel_mt * f

    @staticmethod
    def calculate_sox_emissions(fuel_mt: float, sulfur_content_pct: float) -> float:
        return fuel_mt * sulfur_content_pct / 100 * 2.0  # SOx as SO2 equivalent

    @staticmethod
    def calculate_nox_emissions(fuel_mt: float, nox_factor: float = 0.087) -> float:
        return fuel_mt * nox_factor

    @staticmethod
    def generate_weather_forecast(lat: float, lon: float,
                                  hours: int = 72) -> list[WeatherData]:
        forecasts = []
        base_wind = 10 + 5 * math.sin(lat * 0.1)
        base_hs = 1.0 + 0.5 * math.sin(lon * 0.05)
        for h in range(0, hours, 6):
            wind = base_wind + random.gauss(0, 3)
            hs = base_hs + random.gauss(0, 0.3)
            tp = 5 + random.gauss(0, 1)
            ws = WeatherData(
                timestamp=f"t+{h}h",
                latitude=lat + random.gauss(0, 0.01),
                longitude=lon + random.gauss(0, 0.01),
                wind_speed_kn=max(0, wind),
                wind_direction_deg=random.uniform(0, 360),
                significant_wave_height_m=max(0.1, hs),
                wave_period_s=max(2, tp),
                wave_direction_deg=random.uniform(0, 360),
                sea_water_temp_k=285 + random.gauss(0, 2),
                air_temp_k=290 + random.gauss(0, 3),
                air_pressure_hpa=1013 + random.gauss(0, 5),
                current_speed_kn=random.uniform(0, 2),
                current_direction_deg=random.uniform(0, 360),
            )
            forecasts.append(ws)
        return forecasts

    @staticmethod
    def fuel_switch_timing(distance_to_eca_nm: float, speed_kn: float,
                           flush_time_hours: float = 1.0) -> dict:
        transit_time_h = distance_to_eca_nm / speed_kn
        switch_start_h = transit_time_h - flush_time_hours - 0.5
        return {
            "distance_to_eca_nm": distance_to_eca_nm,
            "transit_time_hours": round(transit_time_h, 2),
            "switch_start_hours_before_entry": round(max(0, switch_start_h), 2),
            "flush_time_hours": flush_time_hours,
            "recommended_action": "Begin fuel switch" if switch_start_h > 0 else "Switch immediately",
        }
