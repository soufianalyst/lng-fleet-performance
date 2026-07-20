import random


class FuelCalculator:
    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()

    def calc_engine_params(self, speed_kn, design_speed_kn, max_power_kw, base_load_pct, in_eca):
        load_pct = base_load_pct * (speed_kn / max(design_speed_kn * 0.85, 0.1))
        load_pct = max(25.0, min(90.0, load_pct))
        shaft_power = max_power_kw * (load_pct / 100.0)
        engine_rpm = 60.0 + (load_pct / 100.0) * 35.0
        rpm_noise = self.rng.gauss(0, 1.5)
        engine_rpm += rpm_noise
        power_noise = self.rng.gauss(0, shaft_power * 0.02)
        shaft_power += power_noise
        if not in_eca:
            fuel_type = "LNG"
            sulfur_pct = 0.0
            sfoc = self.rng.uniform(165, 185)
            scrubber_op = False
        else:
            fuel_type = self.rng.choices(
                ["ULSFO", "MGO"], weights=[0.7, 0.3], k=1
            )[0]
            sulfur_pct = 0.10
            sfoc = self.rng.uniform(175, 195)
            scrubber_op = False
        sfoc_noise = self.rng.gauss(0, 2.0)
        sfoc += sfoc_noise
        fuel_flow_tpd = sfoc * shaft_power * 24.0 / 1_000_000
        fuel_flow_tpd += self.rng.gauss(0, fuel_flow_tpd * 0.01)

        return {
            "engine_speed_rpm": round(engine_rpm, 1),
            "shaft_power_kw": round(shaft_power, 1),
            "sfoc_g_per_kwh": round(sfoc, 1),
            "fuel_flow_t_per_day": round(fuel_flow_tpd, 3),
            "engine_load_pct": round(load_pct, 2),
            "fuel_type": fuel_type,
            "fuel_sulfur_pct": sulfur_pct,
            "scrubber_operating": scrubber_op,
        }

    def calc_exhaust(self, engine_load_pct, shaft_power_kw, engine_type):
        rpm_load = engine_load_pct / 100.0
        exhaust_temp = 250 + rpm_load * 150 + self.rng.gauss(0, 10)
        scavenge_pressure = 0.5 + rpm_load * 1.5 + self.rng.gauss(0, 0.05)
        turbo_speed = 5000 + rpm_load * 15000 + self.rng.gauss(0, 200)
        return {
            "exhaust_temp_c": round(exhaust_temp, 1),
            "scavenge_air_pressure_bar": round(scavenge_pressure, 3),
            "turbocharger_speed_rpm": round(turbo_speed, 1),
        }

    def calc_methane_slip(self, engine_load_pct, engine_type, fuel_type):
        if fuel_type != "LNG":
            return 0.0
        slip_range = {
            "ME-GI": (0.2, 0.5),
            "X-DF": (0.5, 1.5),
            "TFDE": (1.5, 2.5),
            "ST": (0.0, 0.0),
        }.get(engine_type, (0.5, 1.5))
        load_factor = max(0.0, 1.0 - (engine_load_pct / 100.0))
        slip = slip_range[0] + (slip_range[1] - slip_range[0]) * (0.3 + 0.7 * load_factor)
        slip += self.rng.gauss(0, slip * 0.05)
        return max(0.0, round(slip, 3))

    def calc_pilot_fuel(self, shaft_power_kw, fuel_type):
        if fuel_type == "LNG":
            pilot = shaft_power_kw * 0.008
        else:
            pilot = shaft_power_kw * 0.005
        pilot_tpd = pilot * 24 / 1_000_000
        return round(pilot_tpd, 4)

    def calc_bor(self, sea_temp_c, base_bor=0.10, hours_since_departure=0, total_voyage_hours=1):
        temp_factor = 1.0 + 0.02 * (sea_temp_c - 15.0)
        time_factor = 1.0 + 0.0005 * hours_since_departure
        bor = base_bor * temp_factor * time_factor
        bor = max(0.06, min(0.22, bor))
        bor += self.rng.gauss(0, 0.005)
        return max(0.05, min(0.25, bor))

    def calc_emissions(self, fuel_flow_tpd, shaft_power_kw, fuel_type, sfoc, engine_type):
        if fuel_type == "LNG":
            co2_tpd = fuel_flow_tpd * 2.75
            sox_g_kwh = 0.0
        elif fuel_type == "VLSFO":
            co2_tpd = fuel_flow_tpd * 3.11
            sox_g_kwh = 10.0 * (fuel_flow_tpd * 1000 / 24) / max(shaft_power_kw, 1)
        elif fuel_type == "ULSFO":
            co2_tpd = fuel_flow_tpd * 3.11
            sox_g_kwh = 2.0 * (fuel_flow_tpd * 1000 / 24) / max(shaft_power_kw, 1)
        elif fuel_type == "MGO":
            co2_tpd = fuel_flow_tpd * 3.15
            sox_g_kwh = 2.0 * (fuel_flow_tpd * 1000 / 24) / max(shaft_power_kw, 1)
        else:
            co2_tpd = fuel_flow_tpd * 2.75
            sox_g_kwh = 0.0
        co2_tpd += self.rng.gauss(0, co2_tpd * 0.01)
        engine_nox = {
            "ME-GI": (8.0, 12.0),
            "X-DF": (7.0, 11.0),
            "TFDE": (10.0, 15.0),
            "ST": (14.0, 18.0),
        }.get(engine_type, (8.0, 14.0))
        load_factor = 0.7 + 0.3 * (sfoc - 165) / 30
        nox_g_kwh = engine_nox[0] + (engine_nox[1] - engine_nox[0]) * load_factor
        nox_g_kwh += self.rng.gauss(0, 0.5)
        sox_kg_per_day = sox_g_kwh * shaft_power_kw * 24 / 1000
        sox_g_kwh = max(0.0, sox_g_kwh + self.rng.gauss(0, sox_g_kwh * 0.05))
        return {
            "co2_t_per_day": round(co2_tpd, 3),
            "nox_g_per_kwh": round(nox_g_kwh, 2),
            "sox_g_per_kwh": round(sox_g_kwh, 3),
        }

    def calc_bog_destination(self, engine_bog_requirement, bog_available, have_reliquefaction):
        bog_to_engine = min(bog_available, engine_bog_requirement)
        remaining = bog_available - bog_to_engine
        if have_reliquefaction and remaining > 0:
            bog_to_rel = remaining * 0.7
            bog_to_gcu = remaining * 0.3
            reliq_power = bog_to_rel * 50
        else:
            bog_to_rel = 0.0
            bog_to_gcu = remaining
            reliq_power = 0.0
        total = bog_to_engine + bog_to_gcu + bog_to_rel
        return {
            "bog_to_engine_pct": round(bog_to_engine / max(total, 0.001) * 100, 2),
            "bog_to_gcu_pct": round(bog_to_gcu / max(total, 0.001) * 100, 2),
            "bog_to_reliquefaction_pct": round(bog_to_rel / max(total, 0.001) * 100, 2),
            "reliquefaction_power_kw": round(reliq_power, 1),
        }

    def calc_stratification(self, tank_level_pct):
        index = self.rng.uniform(0.0001, 0.05) * (1.0 - tank_level_pct / 100.0)
        return index

    def calc_rollover_risk(self, stratification_index, tank_level_pct):
        if stratification_index < 0.005:
            return "none"
        elif stratification_index < 0.015:
            return "low"
        elif stratification_index < 0.03:
            return "moderate"
        elif stratification_index < 0.045:
            return "high"
        else:
            return "critical"
