import csv
import math
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from collections import OrderedDict

import numpy as np
import pandas as pd

from src.models import (
    Vessel, Voyage, TelemetryPoint, BOGRecord, ECAEvent,
    CIIRecord, CharterParty, CharterVerification, MaintenancePrediction,
)
from src.ports import (
    PORT_COORDS, get_route_waypoints, route_distance_nm,
    great_circle_interpolate, haversine_nm, course_between,
    check_in_any_eca, ROUTE_MAP,
)
from src.weather import WeatherSimulator
from src.fuel_calc import FuelCalculator

import config.settings as cfg


class UUIDGenerator:
    def __init__(self, namespace="lng-fleet"):
        self.ns = uuid.uuid5(uuid.NAMESPACE_DNS, namespace)
        self.counter = 0

    def next(self):
        self.counter += 1
        return uuid.uuid5(self.ns, str(self.counter))


class DataGenerator:
    def __init__(self, seed=cfg.RANDOM_SEED):
        self.rng = random.Random(seed)
        self.np_rng = np.random.RandomState(seed)
        self.uuid_gen = UUIDGenerator()
        self.weather = WeatherSimulator(rng=self.rng)
        self.fuel = FuelCalculator(rng=self.rng)

    def _create_vessels(self):
        seed_vessels = [
            {"imo": 9912345, "name": "LNG Innovator", "flag": "PA",
             "cap": 174000, "year": 2023, "engine": "ME-GI", "tank": "Membrane Type A",
             "draft": 12.0, "speed": 19.5, "power": 42000},
            {"imo": 9912346, "name": "LNG Pioneer", "flag": "MH",
             "cap": 174000, "year": 2022, "engine": "X-DF", "tank": "Membrane Type A",
             "draft": 12.0, "speed": 19.5, "power": 41000},
            {"imo": 9912347, "name": "LNG Voyager", "flag": "BS",
             "cap": 180000, "year": 2024, "engine": "ME-GI", "tank": "Membrane Type A",
             "draft": 12.5, "speed": 19.5, "power": 45000},
            {"imo": 9912348, "name": "LNG Champion", "flag": "SG",
             "cap": 170000, "year": 2021, "engine": "X-DF", "tank": "Membrane Type A",
             "draft": 11.8, "speed": 19.0, "power": 40000},
            {"imo": 9912349, "name": "LNG Navigator", "flag": "PA",
             "cap": 145000, "year": 2020, "engine": "TFDE", "tank": "MOSS",
             "draft": 11.5, "speed": 19.0, "power": 35000},
            {"imo": 9912350, "name": "LNG Horizon", "flag": "MH",
             "cap": 138000, "year": 2019, "engine": "ST", "tank": "Membrane Type B",
             "draft": 11.2, "speed": 18.5, "power": 32000},
            {"imo": 9912351, "name": "LNG Endeavor", "flag": "BS",
             "cap": 174000, "year": 2023, "engine": "X-DF", "tank": "Membrane Type A",
             "draft": 12.0, "speed": 19.5, "power": 42000},
            {"imo": 9912352, "name": "LNG Spirit", "flag": "PA",
             "cap": 160000, "year": 2022, "engine": "ME-GI", "tank": "Membrane Type A",
             "draft": 11.8, "speed": 19.2, "power": 39000},
            {"imo": 9912353, "name": "LNG Discovery", "flag": "MH",
             "cap": 174000, "year": 2024, "engine": "X-DF", "tank": "Membrane Type A",
             "draft": 12.0, "speed": 19.5, "power": 42000},
            {"imo": 9912354, "name": "LNG Enterprise", "flag": "SG",
             "cap": 180000, "year": 2024, "engine": "ME-GI", "tank": "Membrane Type A",
             "draft": 12.5, "speed": 19.5, "power": 45000},
        ]
        vessels = []
        for v in seed_vessels:
            vessels.append(Vessel(
                id=self.uuid_gen.next(),
                imo=v["imo"],
                name=v["name"],
                flag=v["flag"],
                capacity_m3=v["cap"],
                build_year=v["year"],
                engine_type=v["engine"],
                tank_type=v["tank"],
                design_draft_m=v["draft"],
                design_speed_kn=v["speed"],
                max_power_kw=v["power"],
            ))
        return vessels

    def _assign_trade_route(self, vessel_idx):
        assignments = [
            "mideast_asia", "mideast_europe",
            "us_europe", "australia_japan",
            "westafrica_europe", "westafrica_americas",
            "indonesia_china", "us_asia_panama",
            "norway_europe", "yamal_europe",
            "us_southamerica", "us_gulf_mexico",
        ]
        return assignments[vessel_idx % len(assignments)]

    def _pick_ports(self, route_name):
        info = ROUTE_MAP[route_name]
        load = self.rng.choice(info["loading"])
        disch = self.rng.choice(info["discharge"])
        return load, disch

    def _calc_voyage_duration(self, waypoints, speed_kn):
        dist_nm = route_distance_nm(waypoints)
        hours = dist_nm / max(speed_kn, 1.0)
        port_hours = self.rng.uniform(12, 36)
        return hours + port_hours, dist_nm

    def _interpolate_voyage_positions(self, waypoints, num_samples):
        if num_samples <= 0:
            return []
        num_legs = len(waypoints) - 1
        if num_legs == 0:
            return [waypoints[0]] * num_samples
        samples_per_leg = [0] * num_legs
        leg_distances = []
        for i in range(num_legs):
            d = haversine_nm(
                waypoints[i][0], waypoints[i][1],
                waypoints[i + 1][0], waypoints[i + 1][1],
            )
            leg_distances.append(max(d, 0.001))
        total_dist = sum(leg_distances)
        for i in range(num_legs):
            samples_per_leg[i] = max(1, int(num_samples * leg_distances[i] / total_dist))
        diff = num_samples - sum(samples_per_leg)
        if diff > 0:
            samples_per_leg[-1] += diff
        elif diff < 0:
            samples_per_leg[-1] = max(1, samples_per_leg[-1] + diff)
        positions = []
        for i in range(num_legs):
            n = samples_per_leg[i]
            if i > 0:
                n += 1
            pts = great_circle_interpolate(
                waypoints[i][0], waypoints[i][1],
                waypoints[i + 1][0], waypoints[i + 1][1],
                n,
            )
            if i > 0 and positions:
                pts = pts[1:]
            positions.extend(pts)
        return positions[:num_samples]

    def generate_all(self, start_date=None, num_days=None):
        if start_date is None:
            start_date = cfg.DEFAULT_START_DATE
        if num_days is None:
            num_days = cfg.DEFAULT_NUM_DAYS
        tz = timezone.utc
        start = start_date.replace(tzinfo=tz)
        end = start + timedelta(days=num_days)

        vessels = self._create_vessels()
        all_voyages = []
        all_telemetry = []
        all_bog = []
        all_eca_events = []
        all_cii = []
        all_charters = []
        all_charter_verifications = []
        all_maintenance = []

        for vi, vessel in enumerate(vessels):
            route_name = self._assign_trade_route(vi)
            v_voyages, v_telemetry, v_bog, v_eca, v_cii, v_charter, v_verif, v_maint = (
                self._generate_vessel_data(vessel, route_name, start, end)
            )
            all_voyages.extend(v_voyages)
            all_telemetry.extend(v_telemetry)
            all_bog.extend(v_bog)
            all_eca_events.extend(v_eca)
            all_cii.extend(v_cii)
            all_charters.extend(v_charter)
            all_charter_verifications.extend(v_verif)
            all_maintenance.extend(v_maint)

        return {
            "vessels": vessels,
            "voyages": all_voyages,
            "telemetry": all_telemetry,
            "bog": all_bog,
            "eca_events": all_eca_events,
            "cii": all_cii,
            "charter_parties": all_charters,
            "charter_verifications": all_charter_verifications,
            "maintenance": all_maintenance,
        }

    def _generate_vessel_data(self, vessel, route_name, start, end):
        voyages = []
        telemetry = []
        bog = []
        eca_events = []
        cii_records = []
        charter = self._generate_charter_party(vessel, start)
        charter_verifications = []
        maintenance = self._generate_maintenance_predictions(vessel, start)

        current_time = start
        voy_num = 1
        prev_arrival = None

        while current_time < end:
            load_port, disch_port = self._pick_ports(route_name)
            waypoints = get_route_waypoints(load_port, disch_port)
            if not waypoints or len(waypoints) < 2:
                current_time += timedelta(days=1)
                continue
            speed = self.rng.uniform(*cfg.SERVICE_SPEED_RANGE)
            dur_hours, dist_nm = self._calc_voyage_duration(waypoints, speed)
            arr_time = current_time + timedelta(hours=dur_hours)
            if arr_time > end + timedelta(days=2):
                break
            cargo_m3 = vessel.capacity_m3 * self.rng.uniform(0.92, 0.99)
            voy = Voyage(
                id=self.uuid_gen.next(),
                vessel_id=vessel.id,
                voyage_number=f"V{voy_num}",
                departure_port=load_port,
                arrival_port=disch_port,
                departure_time=current_time,
                arrival_time=arr_time,
                cargo_laden=True,
                cargo_quantity_m3=round(cargo_m3, 1),
                status="completed",
                total_distance_nm=round(dist_nm, 1),
            )
            voyages.append(voy)

            voy_telemetry, voy_bog, voy_eca = self._generate_voyage_data(
                vessel, voy, waypoints, speed, current_time, arr_time,
            )
            telemetry.extend(voy_telemetry)
            bog.extend(voy_bog)
            eca_events.extend(voy_eca)

            if len(voyages) >= 1:
                verif = self._generate_charter_verification(
                    charter, voy, vessel, telemetry[-min(len(telemetry), 100):],
                )
                charter_verifications.append(verif)

            buf_days = self.rng.uniform(*cfg.BUFFER_DAYS_BETWEEN_VOYAGES)
            current_time = arr_time + timedelta(days=buf_days)
            prev_arrival = arr_time
            voy_num += 1

            if arr_time > end:
                break

        for month in range(1, 13):
            cii = self._generate_cii_record(vessel, voyages, 2025, month)
            if cii:
                cii_records.append(cii)

        return voyages, telemetry, bog, eca_events, cii_records, [charter], charter_verifications, maintenance

    def _generate_voyage_data(self, vessel, voyage, waypoints, speed, depart, arrive):
        total_seconds = (arrive - depart).total_seconds()
        telemetry_interval_s = cfg.TELEMETRY_INTERVAL_MINUTES * 60
        num_samples = max(1, int(total_seconds / telemetry_interval_s))
        if num_samples > 50000:
            num_samples = 50000

        positions = self._interpolate_voyage_positions(waypoints, num_samples)
        if len(positions) < num_samples:
            positions = positions * (num_samples // max(len(positions), 1) + 1)
            positions = positions[:num_samples]
        if not positions:
            return [], [], []

        tz = timezone.utc
        telemetry_data = []
        bog_flow_values = []
        sea_temp_values = []
        active_eca_events = {}

        eca_events = []

        total_hours = total_seconds / 3600.0
        base_bor = self.rng.uniform(cfg.BOR_MIN, cfg.BOR_MAX)
        base_load = self.rng.uniform(55, 80)
        initial_level = voyage.cargo_quantity_m3 / vessel.capacity_m3 * 100.0

        prev_lat, prev_lon = positions[0]
        prev_lon = None

        for i in range(num_samples):
            ts = depart + timedelta(seconds=i * telemetry_interval_s)
            lat, lon = positions[i]

            lat += self.rng.gauss(0, 0.003)
            lon += self.rng.gauss(0, 0.003)

            if prev_lon is not None:
                cog = course_between(prev_lat, prev_lon, lat, lon)
            else:
                if i + 1 < num_samples:
                    cog = course_between(lat, lon, positions[i + 1][0], positions[i + 1][1])
                else:
                    cog = 0.0
            heading = cog + self.rng.gauss(0, 2)

            frac = i / max(num_samples - 1, 1)
            if frac < 0.05:
                sog = speed * (0.3 + 0.7 * frac / 0.05)
            elif frac > 0.90:
                sog = speed * (0.3 + 0.7 * (1 - frac) / 0.10)
            else:
                sog = speed

            w = self.weather.get_weather(lat, lon, ts)
            speed_loss = self.weather.speed_loss_factor(w["wind_speed_kn"], w["wave_height_m"])
            sog *= speed_loss
            sog += self.rng.gauss(0, 0.15)
            sog = max(1.0, min(25.0, sog))

            eca_name = check_in_any_eca(lat, lon)
            in_eca = eca_name is not None

            engine_params = self.fuel.calc_engine_params(
                sog, vessel.design_speed_kn, vessel.max_power_kw,
                base_load, in_eca,
            )
            exhaust_params = self.fuel.calc_exhaust(
                engine_params["engine_load_pct"],
                engine_params["shaft_power_kw"],
                vessel.engine_type,
            )
            methane_slip = self.fuel.calc_methane_slip(
                engine_params["engine_load_pct"],
                vessel.engine_type,
                engine_params["fuel_type"],
            )
            pilot_fuel = self.fuel.calc_pilot_fuel(
                engine_params["shaft_power_kw"],
                engine_params["fuel_type"],
            )

            bor = self.fuel.calc_bor(
                w["sea_temp_c"], base_bor,
                hours_since_departure=frac * total_hours,
                total_voyage_hours=total_hours,
            )
            cargo_temp = self.rng.uniform(*cfg.TANK_TEMP_RANGE)
            cargo_pressure = self.rng.uniform(*cfg.TANK_PRESSURE_RANGE)
            cargo_level = initial_level * (1 - frac * base_bor * total_hours / 100.0 / 24.0)
            cargo_level = max(10.0, min(98.0, cargo_level))
            top_temp = cargo_temp + self.rng.uniform(-2, 5)
            mid_temp = cargo_temp + self.rng.uniform(-1, 2)
            bot_temp = cargo_temp + self.rng.uniform(-3, 1)

            remaining_cargo_mt = cargo_level / 100.0 * vessel.capacity_m3 * 0.45
            bog_flow_tpd = remaining_cargo_mt * bor / 100.0
            bog_flow_tph = bog_flow_tpd / 24.0
            bog_flow_values.append(bog_flow_tpd)
            sea_temp_values.append(w["sea_temp_c"])

            emissions = self.fuel.calc_emissions(
                engine_params["fuel_flow_t_per_day"],
                engine_params["shaft_power_kw"],
                engine_params["fuel_type"],
                engine_params["sfoc_g_per_kwh"],
                vessel.engine_type,
            )

            draft_loaded = vessel.design_draft_m * (0.85 + 0.15 * (cargo_level / 100.0))
            if frac > 0.8:
                draft_loaded *= 0.7 + 0.3 * (1 - (frac - 0.8) / 0.2)
            draft_trim = self.rng.uniform(-0.5, 0.5)

            tp = TelemetryPoint(
                time=ts,
                vessel_id=vessel.id,
                voyage_id=voyage.id,
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                sog_kn=round(sog, 2),
                cog_deg=round(cog, 2),
                heading_deg=round(heading, 2),
                engine_speed_rpm=engine_params["engine_speed_rpm"],
                shaft_power_kw=engine_params["shaft_power_kw"],
                sfoc_g_per_kwh=engine_params["sfoc_g_per_kwh"],
                fuel_flow_t_per_day=engine_params["fuel_flow_t_per_day"],
                bog_flow_t_per_day=round(bog_flow_tpd, 3),
                pilot_fuel_flow_t_per_day=pilot_fuel,
                engine_load_pct=engine_params["engine_load_pct"],
                exhaust_temp_c=exhaust_params["exhaust_temp_c"],
                scavenge_air_pressure_bar=exhaust_params["scavenge_air_pressure_bar"],
                turbocharger_speed_rpm=exhaust_params["turbocharger_speed_rpm"],
                fuel_type=engine_params["fuel_type"],
                fuel_sulfur_pct=engine_params["fuel_sulfur_pct"],
                methane_slip_g_per_kwh=methane_slip,
                cargo_tank_temp_c=round(cargo_temp, 1),
                cargo_tank_pressure_bar=round(cargo_pressure, 3),
                cargo_tank_level_pct=round(cargo_level, 2),
                cargo_tank_top_temp_c=round(top_temp, 1),
                cargo_tank_mid_temp_c=round(mid_temp, 1),
                cargo_tank_bot_temp_c=round(bot_temp, 1),
                bor_pct_per_day=round(bor, 4),
                wind_speed_kn=w["wind_speed_kn"],
                wind_direction_deg=w["wind_direction_deg"],
                wave_height_m=w["wave_height_m"],
                wave_period_s=w["wave_period_s"],
                air_temp_c=w["air_temp_c"],
                sea_temp_c=w["sea_temp_c"],
                current_speed_kn=w["current_speed_kn"],
                current_direction_deg=w["current_direction_deg"],
                air_pressure_hpa=w["air_pressure_hpa"],
                in_eca_zone=in_eca,
                eca_zone_name=eca_name if in_eca else "",
                scrubber_operating=engine_params["scrubber_operating"],
                co2_t_per_day=emissions["co2_t_per_day"],
                nox_g_per_kwh=emissions["nox_g_per_kwh"],
                sox_g_per_kwh=emissions["sox_g_per_kwh"],
                hull_draft_fwd_m=round(draft_loaded - draft_trim / 2, 2),
                hull_draft_aft_m=round(draft_loaded + draft_trim / 2, 2),
                hull_trim_m=round(draft_trim, 2),
                water_depth_m=round(self.rng.uniform(30, 2000), 1),
                quality_flag=0,
            )
            telemetry_data.append(tp)

            if eca_name and eca_name not in active_eca_events:
                active_eca_events[eca_name] = {
                    "entry_time": ts,
                    "fuel_before": "LNG" if engine_params["fuel_type"] == "LNG" else engine_params["fuel_type"],
                }
            elif not eca_name and eca_name is None:
                for zone in list(active_eca_events.keys()):
                    ev = active_eca_events.pop(zone)
                    eca_events.append(ECAEvent(
                        id=self.uuid_gen.next(),
                        vessel_id=vessel.id,
                        voyage_id=voyage.id,
                        eca_zone_name=zone,
                        entry_time=ev["entry_time"],
                        exit_time=ts,
                        fuel_type_before=ev["fuel_before"],
                        fuel_type_after=engine_params["fuel_type"],
                        fuel_switch_completed=True,
                        compliance_status="compliant",
                        scrubber_mode="n_a",
                        nox_aftertreatment_active=True,
                    ))

            prev_lat, prev_lon = lat, lon

        for zone, ev in active_eca_events.items():
            eca_events.append(ECAEvent(
                id=self.uuid_gen.next(),
                vessel_id=vessel.id,
                voyage_id=voyage.id,
                eca_zone_name=zone,
                entry_time=ev["entry_time"],
                exit_time=arrive,
                fuel_type_before=ev["fuel_before"],
                fuel_type_after="LNG",
                fuel_switch_completed=True,
                compliance_status="compliant",
                scrubber_mode="n_a",
                nox_aftertreatment_active=True,
            ))

        bog_records = self._generate_bog_records(
            vessel, voyage, depart, arrive, sea_temp_values, bog_flow_values,
        )

        return telemetry_data, bog_records, eca_events

    def _generate_bog_records(self, vessel, voyage, depart, arrive, sea_temps, bog_flows):
        records = []
        interval_hours = cfg.BOG_INTERVAL_MINUTES / 60.0
        total_hours = max(1, (arrive - depart).total_seconds() / 3600.0)
        num_records = max(1, int(total_hours / interval_hours))
        base_bor = self.rng.uniform(cfg.BOR_MIN, cfg.BOR_MAX)

        for i in range(num_records):
            ts = depart + timedelta(hours=i * interval_hours)
            frac = i / max(num_records - 1, 1)
            sea_temp_idx = min(int(frac * len(sea_temps)), len(sea_temps) - 1) if sea_temps else 15
            sea_temp = sea_temps[sea_temp_idx] if sea_temps else 15.0

            for tank_id in range(1, cfg.NUM_CARGO_TANKS + 1):
                bor = self.fuel.calc_bor(sea_temp, base_bor, hours_since_departure=frac * total_hours)
                tank_level = 95.0 * (1 - frac * bor * total_hours / 100.0 / 24.0) + self.rng.gauss(0, 0.5)
                tank_level = max(10.0, min(98.0, tank_level))
                tank_temp = self.rng.uniform(-163, -158)
                tank_press = self.rng.uniform(1.01, 1.10)
                cargo_mt = tank_level / 100.0 * (vessel.capacity_m3 / cfg.NUM_CARGO_TANKS) * 0.45
                bog_tpd = cargo_mt * bor / 100.0
                bog_tpd += self.rng.gauss(0, bog_tpd * 0.02)

                engine_bog_req = 30.0 + self.rng.gauss(0, 5)
                bog_dest = self.fuel.calc_bog_destination(
                    engine_bog_req, bog_tpd,
                    have_reliquefaction=vessel.engine_type in ("ME-GI", "X-DF"),
                )
                strat = self.fuel.calc_stratification(tank_level)
                rollover = self.fuel.calc_rollover_risk(strat, tank_level)

                records.append(BOGRecord(
                    id=self.uuid_gen.next(),
                    vessel_id=vessel.id,
                    voyage_id=voyage.id,
                    recorded_at=ts,
                    tank_id=tank_id,
                    tank_level_pct=round(tank_level, 2),
                    tank_temp_c=round(tank_temp, 1),
                    tank_pressure_bar=round(tank_press, 3),
                    bor_pct_per_day=round(bor, 4),
                    bog_flow_t_per_day=round(bog_tpd, 3),
                    bog_to_engine_pct=bog_dest["bog_to_engine_pct"],
                    bog_to_gcu_pct=bog_dest["bog_to_gcu_pct"],
                    bog_to_reliquefaction_pct=bog_dest["bog_to_reliquefaction_pct"],
                    reliquefaction_power_kw=bog_dest["reliquefaction_power_kw"],
                    stratification_index=round(strat, 6),
                    rollover_risk=rollover,
                ))
        return records

    def _generate_cii_record(self, vessel, voyages, year, month):
        month_voyages = [v for v in voyages
                         if v.departure_time.month == month and v.departure_time.year == year]
        if not month_voyages:
            return None

        dwt_map = {138000: 65000, 145000: 70000, 155000: 75000,
                   160000: 77000, 170000: 82000, 174000: 85000, 180000: 88000}
        dwt = dwt_map.get(vessel.capacity_m3, int(vessel.capacity_m3 * 0.48))

        total_distance = 0.0
        for v in month_voyages:
            total_distance += v.total_distance_nm

        cii_ref = 9.827 * (dwt ** (-0.25))

        perf_factor = self.rng.uniform(0.88, 1.02)
        base_trend = 0.90 + (month / 12.0) * 0.10
        vessel_seed = hash(vessel.name + str(year)) % 100 / 100.0
        vessel_bias = (vessel_seed - 0.5) * 0.04
        cii_val = cii_ref * (perf_factor + vessel_bias)

        d1, d2, d3, d4 = 0.86, 0.94, 1.06, 1.18
        ratio = cii_val / cii_ref
        if ratio <= d1:
            rating = "A"
        elif ratio <= d2:
            rating = "B"
        elif ratio <= d3:
            rating = "C"
        elif ratio <= d4:
            rating = "D"
        else:
            rating = "E"

        avg_speed = 17.0
        total_hours = total_distance / avg_speed if avg_speed > 0 else 1
        avg_power = vessel.max_power_kw * 0.70
        avg_sfoc = 175.0
        fuel_total = avg_sfoc * avg_power * total_hours / 1e6
        co2_total = fuel_total * 2.75
        transport_work = dwt * total_distance

        return CIIRecord(
            id=self.uuid_gen.next(),
            vessel_id=vessel.id,
            year=year,
            month=month,
            co2_total_t=round(co2_total, 3),
            transport_work_t_nm=round(transport_work, 2),
            cii_calculated=round(cii_val, 4),
            cii_required_c=round(cii_ref, 4),
            cii_rating=rating,
            running_annual_cii=round(cii_val * self.rng.uniform(0.98, 1.02), 4),
        )

    def _generate_charter_party(self, vessel, start_date):
        charterer = self.rng.choice(cfg.CHARTERER_NAMES)
        dur_days = self.rng.randint(180, 730)
        return CharterParty(
            id=self.uuid_gen.next(),
            vessel_id=vessel.id,
            charterer_name=charterer,
            charter_type="time",
            start_date=start_date,
            end_date=start_date + timedelta(days=dur_days),
            warranted_speed_kn=round(vessel.design_speed_kn - self.rng.uniform(0.0, 0.5), 2),
            warranted_consumption_t_per_day=round(self.rng.uniform(120, 180), 3),
            warranted_bor_pct_per_day=round(self.rng.uniform(0.08, 0.12), 3),
            speed_tolerance_pct=5.0,
            weather_allowance_beaufort_max=4,
            demurrage_rate_usd_per_day=round(self.rng.uniform(*cfg.DEMURRAGE_RATE_RANGE), 2),
        )

    def _generate_charter_verification(self, charter, voyage, vessel, recent_telemetry):
        avg_speed = sum(t.sog_kn for t in recent_telemetry) / max(len(recent_telemetry), 1)
        avg_consumption = sum(t.fuel_flow_t_per_day for t in recent_telemetry) / max(len(recent_telemetry), 1)
        avg_weather = sum(
            self.weather.beaufort_from_wind(t.wind_speed_kn) for t in recent_telemetry
        ) / max(len(recent_telemetry), 1)

        weather_correction = 1.0 + max(0, avg_weather - charter.weather_allowance_beaufort_max) * 0.02
        adj_speed = avg_speed * weather_correction
        adj_consumption = avg_consumption / max(weather_correction, 0.5)

        speed_ok = adj_speed >= charter.warranted_speed_kn * (1 - charter.speed_tolerance_pct / 100.0)
        cons_ok = adj_consumption <= charter.warranted_consumption_t_per_day * 1.05
        off_hire = 0.0 if speed_ok else self.rng.uniform(0, 8)
        claim = off_hire * charter.demurrage_rate_usd_per_day / 24 if not speed_ok else 0.0

        return CharterVerification(
            id=self.uuid_gen.next(),
            charter_id=charter.id,
            voyage_id=voyage.id,
            verified_speed_kn=round(avg_speed, 2),
            verified_consumption_t_per_day=round(avg_consumption, 3),
            weather_correction_applied=True,
            weather_adjusted_speed_kn=round(adj_speed, 2),
            weather_adjusted_consumption_t_per_day=round(adj_consumption, 3),
            speed_compliance=speed_ok,
            consumption_compliance=cons_ok,
            off_hire_hours=round(off_hire, 2),
            claim_amount_usd=round(claim, 2),
        )

    def _generate_maintenance_predictions(self, vessel, start_date):
        records = []
        for component in cfg.MAINTENANCE_COMPONENTS:
            anomaly = self.rng.uniform(0.01, 0.95)
            if anomaly < 0.3:
                severity = "low"
                rul = self.rng.randint(90, 365)
                conf = self.rng.uniform(60, 85)
            elif anomaly < 0.6:
                severity = "moderate"
                rul = self.rng.randint(30, 90)
                conf = self.rng.uniform(70, 90)
            elif anomaly < 0.8:
                severity = "high"
                rul = self.rng.randint(7, 30)
                conf = self.rng.uniform(75, 95)
            else:
                severity = "critical"
                rul = self.rng.randint(1, 7)
                conf = self.rng.uniform(85, 99)

            param = {
                "Main Engine": "cylinder_pressure",
                "Aux Engine": "exhaust_temp",
                "Turbocharger": "vibration_level",
                "GCU": "combustion_temp",
                "Cargo Pump": "bearing_temp",
                "Vaporizer": "heat_exchange_eff",
                "Reliquefaction Unit": "compressor_pressure",
                "Boiler": "steam_pressure",
                "Propeller": "cavitation_index",
                "Rudder": "hydraulic_pressure",
                "Hull Coating": "roughness_factor",
                "Shaft Generator": "winding_temp",
                "SCR System": "catalyst_temp",
                "EGR System": "flow_rate",
                "Fuel Gas Supply System": "pressure_drop",
                "Ballast Water Treatment": "uv_intensity",
            }.get(component, "general_health")

            base_val = self.rng.uniform(50, 100)
            actual_val = base_val * (1 + anomaly * self.rng.uniform(-0.2, 0.2))
            deviation = (actual_val - base_val) / base_val * 100

            records.append(MaintenancePrediction(
                id=self.uuid_gen.next(),
                vessel_id=vessel.id,
                component=component,
                parameter=param,
                predicted_value=round(base_val, 4),
                actual_value=round(actual_val, 4),
                deviation_pct=round(deviation, 4),
                rul_days=rul,
                confidence_pct=round(conf, 1),
                anomaly_score=round(anomaly, 3),
                model_version="ML-v2.4",
                predicted_at=start_date + timedelta(days=self.rng.randint(0, 30)),
            ))
        return records


def _dataclass_to_dict(obj):
    d = {}
    for field_name in [f.name for f in type(obj).__dataclass_fields__.values()]:
        val = getattr(obj, field_name)
        if isinstance(val, uuid.UUID):
            d[field_name] = str(val)
        elif isinstance(val, datetime):
            d[field_name] = val.isoformat()
        else:
            d[field_name] = val
    return d


def write_csv(filename, records):
    if not records:
        with open(filename, "w") as f:
            f.write("")
        return
    keys = [f.name for f in type(records[0]).__dataclass_fields__.values()]
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for rec in records:
            writer.writerow(_dataclass_to_dict(rec))


def generate_and_save(output_dir, start_date=None, num_days=None):
    os.makedirs(output_dir, exist_ok=True)
    gen = DataGenerator()
    data = gen.generate_all(start_date, num_days)

    write_csv(os.path.join(output_dir, "vessels.csv"), data["vessels"])
    write_csv(os.path.join(output_dir, "voyages.csv"), data["voyages"])
    write_csv(os.path.join(output_dir, "telemetry.csv"), data["telemetry"])
    write_csv(os.path.join(output_dir, "bog_records.csv"), data["bog"])
    write_csv(os.path.join(output_dir, "eca_events.csv"), data["eca_events"])
    write_csv(os.path.join(output_dir, "cii_records.csv"), data["cii"])
    write_csv(os.path.join(output_dir, "charter_parties.csv"), data["charter_parties"])
    write_csv(os.path.join(output_dir, "charter_verifications.csv"), data["charter_verifications"])
    write_csv(os.path.join(output_dir, "maintenance_predictions.csv"), data["maintenance"])

    summary = {
        "vessels": len(data["vessels"]),
        "voyages": len(data["voyages"]),
        "telemetry": len(data["telemetry"]),
        "bog_records": len(data["bog"]),
        "eca_events": len(data["eca_events"]),
        "cii_records": len(data["cii"]),
        "charter_parties": len(data["charter_parties"]),
        "charter_verifications": len(data["charter_verifications"]),
        "maintenance_predictions": len(data["maintenance"]),
    }
    return summary, data
