import math
import numpy as np

EARTH_RADIUS_NM = 3440.065

# Fuel lower heating values (MJ/tonne)
LHV = {
    "LNG": 50000,
    "MGO": 42700,
    "VLSFO": 40200,
    "PILOT": 42700,
}

# Emission factors (kg CO2 per tonne fuel)
EMISSION_FACTORS = {
    "LNG": 2750,
    "MGO": 3206,
    "VLSFO": 3151,
    "PILOT": 3206,
}

# WTW well-to-tank factors
WTW_FACTORS = {"LNG": 0.68, "MGO": 1.0, "VLSFO": 1.0, "PILOT": 1.0}

# NOx emission factors (g NOx per kWh, engine dependent)
# ME-GI (high-pressure Diesel cycle): ~7 g/kWh with EGR
# X-DF (low-pressure Otto cycle): ~1.5 g/kWh (inherently low NOx)
# AUX (4-stroke MGO, Tier II): ~10 g/kWh
NOX_FACTORS = {"ME_GI": 7.0, "X_DF": 1.5, "AUX": 10.0}

# SOx proportional to sulfur content
SOX_FACTOR_PER_SULFUR_PCT = 2.0


def haversine_nm(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def interpolate_position(lat1, lon1, lat2, lon2, fraction):
    fraction = max(0.0, min(1.0, fraction))
    lat = lat1 + (lat2 - lat1) * fraction
    lon = lon1 + (lon2 - lon1) * fraction
    return lat, lon


def cubic_resistance(speed_kn, displacement_mt, lwl_m):
    speed_ms = speed_kn * 0.5144
    if speed_ms < 0.1:
        return 0.0
    c_resistance = 0.001 * displacement_mt ** (2.0 / 3.0)
    return c_resistance * speed_ms ** 3


def shaft_power_from_speed(speed_kn, displacement_mt, lwl_m, hull_fouling_pct=0.0):
    base_power = cubic_resistance(speed_kn, displacement_mt, lwl_m)
    fouling_factor = 1.0 + (hull_fouling_pct / 100.0) * 0.15
    return base_power * fouling_factor


def speed_from_power(power_kw, displacement_mt, lwl_m, hull_fouling_pct=0.0):
    fouling_factor = 1.0 + (hull_fouling_pct / 100.0) * 0.15
    c_resistance = 0.001 * displacement_mt ** (2.0 / 3.0) * fouling_factor
    if c_resistance < 1e-10:
        return 0.0
    speed_ms = (power_kw / (c_resistance + 1e-10)) ** (1.0 / 3.0)
    return speed_ms / 0.5144


def sfoc_curve(load_pct, rated_sfoc=163.0):
    load_pct = max(25.0, min(105.0, load_pct))
    optimal_load = 85.0
    deviation = load_pct - optimal_load
    return rated_sfoc * (1.0 + 0.00008 * deviation ** 2)


def exhaust_temp_from_load(load_pct, base_temp=240.0, max_temp=380.0):
    load_pct = max(0.0, min(105.0, load_pct))
    return base_temp + (max_temp - base_temp) * (load_pct / 100.0) ** 1.3


def bog_generation_rate(tank_pressure_bar, sea_temp_c, cargo_temp_k, tank_fill_pct,
                        insulation_quality=0.95, num_tanks=4, tank_capacity_m3=43500):
    total_capacity = num_tanks * tank_capacity_m3
    total_volume = total_capacity * tank_fill_pct / 100.0
    delta_t = max(0, (273.15 + sea_temp_c) - cargo_temp_k)
    heat_leak_kw = (1.0 - insulation_quality) * total_volume * delta_t * 0.001
    boil_off_density = 0.45  # kg/m3/h per degree and per m3
    bog_kg_h = heat_leak_kw * boil_off_density * 2.0
    pressure_factor = 1.0 + max(0, (tank_pressure_bar - 1.1) * 0.3)
    bog_kg_h *= pressure_factor
    return max(50.0, bog_kg_h)


def calculate_displacement(draft_f, draft_a, beam, lwl, block_coeff=0.72):
    mean_draft = (draft_f + draft_a) / 2.0
    displacement_mt = block_coeff * lwl * beam * mean_draft * 1.025 / 1000.0
    return displacement_mt


def calculate_trim(draft_f, draft_a):
    return draft_a - draft_f


def calculate_gm(GM_0, free_surface_correction, heel_angle_deg, KB, BM):
    KG = KB + BM - GM_0
    if abs(heel_angle_deg) < 0.01:
        return GM_0 - free_surface_correction
    cos_angle = math.cos(math.radians(heel_angle_deg))
    GZ = (GM_0 - free_surface_correction) * math.sin(math.radians(heel_angle_deg))
    return GZ / (math.sin(math.radians(heel_angle_deg)) + 1e-10) if abs(heel_angle_deg) > 0.01 else GM_0 - free_surface_correction


def fuel_consumption_kg_h(power_kw, sfoc_g_kwh):
    return power_kw * sfoc_g_kwh / 1e6


def co2_from_fuel(fuel_mass_mt, fuel_type="LNG"):
    ef = EMISSION_FACTORS.get(fuel_type, EMISSION_FACTORS["LNG"])
    return fuel_mass_mt * ef / 1000.0


def nox_from_power(power_kw, duration_h, engine_type="ME_GI"):
    """NOx in kg from g/kWh emission factor: kW × h × g/kWh = g → kg (/1000)."""
    ef = NOX_FACTORS.get(engine_type, 7.0)
    return power_kw * duration_h * ef / 1000.0


def sox_from_fuel(fuel_mass_mt, sulfur_pct):
    return fuel_mass_mt * sulfur_pct * SOX_FACTOR_PER_SULFUR_PCT / 100.0


def methane_slip_g_kwh(propulsion_type, load_pct):
    """Methane slip in g CH4 per kWh shaft power.
    ME-GI (high-pressure Diesel cycle): ~0.2-0.35 g/kWh, mild load dependence.
    X-DF (low-pressure Otto cycle): ~2.5-4.0 g/kWh, strong increase at low load
    (incomplete premixed combustion below ~50% load).
    """
    pt = (propulsion_type or "").upper().replace("-", "_")
    load_frac = max(0.15, min(1.05, load_pct / 100.0))
    if "ME_GI" in pt or "MEGI" in pt:
        return 0.25 + 0.10 * (1.0 - load_frac)
    if "X_DF" in pt or "XDF" in pt:
        base = 2.6
        if load_frac < 0.5:
            base += (0.5 - load_frac) * 4.0  # strong slip increase at low load
        else:
            base += (1.0 - load_frac) * 0.5
        return base
    return 0.5


def eeoi_calculation(co2_mt, cargo_mt, distance_nm):
    """EEOI in g CO2 / (t·nm) — industry convention."""
    if cargo_mt < 1.0 or distance_nm < 1.0:
        return 0.0
    return co2_mt * 1e6 / (cargo_mt * distance_nm)


def cii_calculation(co2_emissions_mt, deadweight_mt, distance_nm):
    if distance_nm < 1.0 or deadweight_mt < 1.0:
        return 0.0
    return (co2_emissions_mt * 1000000.0) / (deadweight_mt * distance_nm)
