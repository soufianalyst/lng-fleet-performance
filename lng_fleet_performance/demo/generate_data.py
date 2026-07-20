import random
import math
from datetime import datetime, timedelta

from ..database.connection import DatabaseManager
from ..database.schema import create_all_tables
from ..models.vessel import Vessel, VesselTank
from ..models.voyage import Voyage, VoyageWaypoint
from ..models.cargo import CargoRecord, BORDailySummary
from ..models.engine import EnginePerformance
from ..models.compliance import CIIAssessment, EUETSRecord
from ..modules.hull_machinery import HullMachinery
from ..modules.certificate_manager import CertificateManager
from ..modules.seemp_compliance import SEEMPCompliance
from ..utils.geofencing import PREDEFINED_ECA_ZONES


class DemoDataGenerator:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def generate_all(self):
        print("Generating demo data...")
        self._clear_existing_data()
        self._seed_eca_zones()
        vessels = self._create_vessels()
        for vessel in vessels:
            self._create_tanks(vessel)
            voyages = self._create_voyages(vessel)
            for voyage in voyages:
                self._create_waypoints(voyage)
                self._create_cargo_records(voyage)
                self._create_bor_summaries(voyage)
                self._create_engine_data(voyage)
                self._create_hull_data(vessel)
                self._create_charter_party(voyage)
            self._create_certificates(vessel)
            self._create_seemp_measures(vessel)
        print(f"Demo data generated: {len(vessels)} vessels, "
              f"{sum(len(self.db.fetchall('SELECT * FROM voyages WHERE vessel_id=?', (v.vessel_id,))) for v in vessels)} voyages")

    def _seed_eca_zones(self):
        for zone in PREDEFINED_ECA_ZONES:
            zone.save(self.db)

    def _clear_existing_data(self):
        tables = [
            "charter_party_audit", "digital_twin_assessments", "digital_twin_parameters",
            "voyage_eca_events", "voyage_fuel_switch_log",
            "cargo_records", "bor_daily_summary",
            "eu_ets_surrender", "certificate_expiry_log", "igc_compliance_log",
            "egr_data", "seemp_reports", "seemp_measures", "epl_config", "eexi_assessment",
            "certificates", "predictive_alerts", "scr_data", "scrubber_data",
            "fueleu_records", "eu_ets_records", "cii_assessment",
            "auxiliary_engines", "engine_performance", "engine_cylinder_data",
            "hull_performance", "emissions_log", "eca_events", "fuel_switch_log",
            "charter_party", "charter_performance", "off_hire_events",
            "digital_twin_state", "maintenance_events",
            "weather_data", "sensor_readings", "bunkering_records",
            "voyage_weather_data",
            "voyage_waypoints", "voyages",
        ]
        for t in tables:
            try:
                self.db.execute(f"DELETE FROM {t}")
            except Exception:
                pass
        self.db.execute("DELETE FROM vessel_tanks")
        self.db.execute("DELETE FROM vessels")

    def _create_vessels(self) -> list[Vessel]:
        vessel_specs = [
            {"imo": "9801001", "name": "LNG Atlantic Eagle", "flag": "Marshall Islands",
             "dwt": 82000, "capacity": 174000, "mcr": 14500, "speed": 19.5,
             "eexi": 4.80, "year": 2020, "type": "ME-GI"},
            {"imo": "9801002", "name": "LNG Pacific Titan", "flag": "Panama",
             "dwt": 85000, "capacity": 180000, "mcr": 15200, "speed": 19.8,
             "eexi": 4.78, "year": 2021, "type": "X-DF"},
            {"imo": "9801003", "name": "LNG Nordic Voyager", "flag": "Norway",
             "dwt": 78000, "capacity": 170000, "mcr": 13800, "speed": 19.2,
             "eexi": 4.88, "year": 2019, "type": "ME-GI"},
            {"imo": "9801004", "name": "LNG Silk Route", "flag": "Singapore",
             "dwt": 88000, "capacity": 185000, "mcr": 16000, "speed": 20.0,
             "eexi": 4.81, "year": 2022, "type": "X-DF"},
            {"imo": "9801005", "name": "LNG Desert Star", "flag": "Cyprus",
             "dwt": 81000, "capacity": 172000, "mcr": 14200, "speed": 19.3,
             "eexi": 4.84, "year": 2018, "type": "ME-GI"},
        ]
        vessels = []
        for spec in vessel_specs:
            vessel = Vessel(
                imo_number=spec["imo"],
                vessel_name=spec["name"],
                flag_state=spec["flag"],
                classification_society="DNV",
                gross_tonnage=spec["dwt"] * 1.3,
                deadweight_tonnage=spec["dwt"],
                cargo_capacity_m3=spec["capacity"],
                number_of_tanks=4,
                propulsion_type=spec["type"],
                engine_manufacturer="WinGD" if "X-DF" in spec["type"] else "MAN Energy Solutions",
                engine_model="X-DF 7G80" if "X-DF" in spec["type"] else "ME-GI 7G80",
                engine_mcr_kw=spec["mcr"],
                service_speed_kn=spec["speed"],
                design_speed_kn=spec["speed"] + 0.5,
                eexi_value=spec["eexi"],
                eedi_value=spec["eexi"] * 0.95,
                cii_reference_value=0.96,
                year_of_build=spec["year"],
                scrubber_equipped=random.choice([True, False]),
                reliquefaction_plant=True,
                shaft_power_meter=True,
            )
            vessel.save(self.db)
            vessels.append(vessel)
            print(f"  Created vessel: {vessel.vessel_name} ({vessel.imo_number})")
        return vessels

    def _create_tanks(self, vessel: Vessel):
        tank_capacity = vessel.cargo_capacity_m3 / vessel.number_of_tanks
        positions = ["PORT", "STARBOARD"]
        for i in range(vessel.number_of_tanks):
            pos = positions[i % 2]
            tank = VesselTank(
                vessel_id=vessel.vessel_id,
                tank_name=f"Tank {i+1}",
                tank_position=pos,
                capacity_m3=tank_capacity,
                design_pressure_bar=1.2,
                design_temperature_k=111.0,
                insulation_type="membrane",
                sensor_count=12,
            )
            tank.save(self.db)

    def _create_voyages(self, vessel: Vessel) -> list[Voyage]:
        routes = [
            ("Ras Laffan", 12000, 75000),
            ("Hamad", 2500, 80000),
            ("Sabine Pass", 4800, 70000),
            ("Darwin", 5500, 65000),
            ("Snovit", 2800, 72000),
            ("Ras Laffan", 5200, 78000),
            ("Hamad", 1500, 82000),
            ("Cameron LNG", 5000, 68000),
        ]
        statuses = ["completed", "completed", "completed", "in_progress"]
        voyages = []
        now = datetime.utcnow()
        for i, (load, dist_nm, cargo) in enumerate(random.sample(routes, min(4, len(routes)))):
            discharge = random.choice(["Rotterdam", "Tokyo", "Busan", "Sines",
                                       "Zeebrugge", "Barcelona", "Incheon"])
            days_ago = random.randint(5, 60)
            dep = now - timedelta(days=days_ago)
            arr = dep + timedelta(hours=dist_nm / 19.0 + random.uniform(-1, 1))
            status = statuses[i % len(statuses)]
            fuel_hfo = random.uniform(0, 50)
            fuel_vlsfo = random.uniform(0, 100)
            fuel_ulsfo = random.uniform(0, 30)
            fuel_mgo = random.uniform(0, 20)
            fuel_lng = random.uniform(500, 1200)
            total_fuel = fuel_hfo + fuel_vlsfo + fuel_ulsfo + fuel_mgo + fuel_lng
            co2 = fuel_hfo * 3.114 + fuel_vlsfo * 3.114 + fuel_ulsfo * 3.114 + \
                  fuel_mgo * 3.206 + fuel_lng * 2.75
            voyage = Voyage(
                vessel_id=vessel.vessel_id,
                voyage_number=f"V{vessel.vessel_id}-{i+1:03d}",
                charterer=random.choice(["Shell", "TotalEnergies", "QatarEnergy", "Cheniere"]),
                load_port=load,
                discharge_port=discharge,
                cargo_quantity_mt=cargo,
                planned_departure=dep.isoformat(),
                actual_departure=dep.isoformat(),
                planned_arrival=arr.isoformat(),
                actual_arrival=arr.isoformat() if status == "completed" else "",
                status=status,
                total_distance_nm=dist_nm,
                total_fuel_hfo_mt=fuel_hfo,
                total_fuel_vlsfo_mt=fuel_vlsfo,
                total_fuel_ulsfo_mt=fuel_ulsfo,
                total_fuel_mgo_mt=fuel_mgo,
                total_fuel_lng_mt=fuel_lng,
                total_bog_mt=random.uniform(50, 150),
                co2_total_mt=co2,
                eca_time_hours=random.uniform(10, 80),
                eu_ets_applicable=random.choice([True, False]),
            )
            voyage.save(self.db)
            voyages.append(voyage)
        return voyages

    def _create_waypoints(self, voyage: Voyage):
        load_ports = {
            "Ras Laffan": (25.0, 51.5), "Hamad": (25.3, 51.6),
            "Sabine Pass": (29.7, -93.8), "Darwin": (-12.5, 130.8),
            "Snovit": (70.5, 20.0), "Cameron LNG": (29.8, -93.3),
        }
        discharge_ports = {
            "Yokosuka": (35.3, 139.7), "Jebel Ali": (25.0, 55.1),
            "Zeebrugge": (51.3, 3.2), "Incheon": (37.5, 126.6),
            "Montoir": (47.3, -1.9), "Sines": (37.9, -8.9),
            "Rotterdam": (51.9, 4.0), "Tokyo": (35.6, 139.8),
            "Busan": (35.1, 129.0), "Barcelona": (41.3, 2.2),
            "Dahej": (21.7, 72.6),
        }
        start = load_ports.get(voyage.load_port, (25.0, 51.5))
        end = discharge_ports.get(voyage.discharge_port, (35.0, 140.0))
        num_wps = random.randint(8, 15)
        for i in range(num_wps):
            t = i / (num_wps - 1)
            lat = start[0] + t * (end[0] - start[0]) + random.gauss(0, 0.3)
            lon = start[1] + t * (end[1] - start[1]) + random.gauss(0, 0.3)
            bearing = random.uniform(0, 360)
            speed = voyage.service_speed_kn if hasattr(voyage, 'service_speed_kn') else 19.0
            speed = random.uniform(speed - 1, speed + 1)
            wp = VoyageWaypoint(
                voyage_id=voyage.voyage_id,
                sequence_num=i + 1,
                latitude=lat,
                longitude=lon,
                speed_planned_kn=19.0,
                speed_actual_kn=speed,
                course_deg=bearing,
                in_eca=random.random() < 0.15,
                weather_hs_m=random.uniform(0.5, 4.0),
                weather_tp_s=random.uniform(4, 10),
                wind_speed_kn=random.uniform(5, 30),
                wind_direction_deg=random.uniform(0, 360),
                current_speed_kn=random.uniform(0, 2),
                current_direction_deg=random.uniform(0, 360),
                fuel_consumption_mt=random.uniform(2, 5),
                shaft_power_kw=random.uniform(8000, 14000),
            )
            wp.save(self.db)

    def _create_cargo_records(self, voyage: Voyage):
        tanks = self.db.fetchall(
            "SELECT tank_id FROM vessel_tanks WHERE vessel_id=?",
            (voyage.vessel_id,))
        fill = random.uniform(85, 98)
        dep = datetime.fromisoformat(voyage.actual_departure) if voyage.actual_departure \
              else datetime.utcnow() - timedelta(days=10)
        for tank_row in tanks:
            for day in range(0, 10):
                t = dep + timedelta(days=day)
                fill -= random.uniform(0.05, 0.15)
                temp_k = 111.0 + random.gauss(0, 0.3)
                rec = CargoRecord(
                    voyage_id=voyage.voyage_id,
                    tank_id=tank_row["tank_id"],
                    record_timestamp=t.isoformat(),
                    cargo_level_pct=fill,
                    cargo_volume_m3=fill / 100 * 43000,
                    cargo_mass_mt=fill / 100 * 43000 * 0.45,
                    cargo_temperature_k=temp_k,
                    cargo_pressure_bar=1.0 + random.gauss(0, 0.05),
                    tank_top_temp_k=temp_k + 0.3,
                    tank_mid_temp_k=temp_k,
                    tank_bottom_temp_k=temp_k - 0.2,
                    stratification_index=random.uniform(0.01, 0.3),
                    rollover_risk_level="low",
                    bog_generation_rate_kg_h=random.uniform(800, 1500),
                )
                rec.save(self.db)

    def _create_bor_summaries(self, voyage: Voyage):
        dep = datetime.fromisoformat(voyage.actual_departure) if voyage.actual_departure \
              else datetime.utcnow() - timedelta(days=10)
        for day in range(10):
            d = (dep + timedelta(days=day)).strftime("%Y-%m-%d")
            bor = BORDailySummary(
                voyage_id=voyage.voyage_id,
                summary_date=d,
                avg_bor_pct_day=random.uniform(0.10, 0.18),
                measured_bor_pct_day=random.uniform(0.10, 0.18),
                energy_balance_bor=random.uniform(0.09, 0.17),
                bog_to_engine_mt=random.uniform(60, 120),
                bog_to_reliquefaction_mt=random.uniform(20, 50),
                bog_to_gcu_mt=random.uniform(5, 20),
                reliquefaction_power_kw=random.uniform(500, 800),
                reliquefaction_cop=random.uniform(3, 5),
                tank_avg_temp_k=random.uniform(110.5, 111.5),
                sea_water_temp_k=random.uniform(282, 295),
                ambient_temp_k=random.uniform(275, 300),
            )
            bor.save(self.db)

    def _create_engine_data(self, voyage: Voyage):
        dep = datetime.fromisoformat(voyage.actual_departure) if voyage.actual_departure \
              else datetime.utcnow() - timedelta(days=10)
        for h in range(0, 240, 6):
            t = dep + timedelta(hours=h)
            power = random.uniform(9000, 14000)
            sfoc = 168 + 80 * ((power / 15000 - 0.85) ** 2) + random.gauss(0, 2)
            ep = EnginePerformance(
                voyage_id=voyage.voyage_id,
                record_timestamp=t.isoformat(),
                engine_mode="gas",
                shaft_power_kw=power,
                mcr_pct=power / 15000 * 100,
                sfoc_actual_g_kwh=sfoc,
                sfoc_reference_g_kwh=168,
                sfoc_delta=sfoc - 168,
                thermal_efficiency_pct=42 - (sfoc - 168) * 0.1,
                cylinder_pmax_bar=145 + random.gauss(0, 2),
                exhaust_temp_cyl_avg=350 + random.gauss(0, 5),
                turbocharger_speed_rpm=12000 + random.gauss(0, 200),
                turbocharger_surge_margin=25 + random.gauss(0, 3),
                methane_slip_g_kwh=3.5 + random.gauss(0, 0.5),
                pilot_fuel_pct=random.uniform(0.5, 1.5),
            )
            ep.save(self.db)

    def _create_hull_data(self, vessel: Vessel):
        hull = HullMachinery(self.db)
        now = datetime.utcnow()
        for day in range(30):
            d = (now - timedelta(days=day)).strftime("%Y-%m-%d")
            power_dev = 3 + day * 0.2 + random.gauss(0, 0.5)
            cur = self.db.execute(
                """INSERT INTO hull_performance
                   (vessel_id, record_date, speed_kn, shaft_power_kw,
                    wind_speed_kn, wind_direction_deg, current_speed_kn,
                    current_direction_deg, sea_state, water_temp_k, water_depth_m,
                    displacement_mt, draft_fwd_m, draft_aft_m, trim_m,
                    reference_power_kw, power_deviation_pct, friction_coeff_delta,
                    equivalent_roughness_mm, fouling_level, qpc_trending)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (vessel.vessel_id, d, 19.0 + random.gauss(0, 0.3),
                 11000 + power_dev * 100, random.uniform(5, 25),
                 random.uniform(0, 360), random.uniform(0, 1.5),
                 random.uniform(0, 360), random.randint(3, 6),
                 random.uniform(282, 295), random.uniform(50, 200),
                 80000, 12.0 + random.gauss(0, 0.1),
                 12.5 + random.gauss(0, 0.1), 0.5,
                 11000, power_dev, power_dev * 0.001,
                 0.3 + power_dev * 0.01,
                 "clean" if power_dev < 5 else "light" if power_dev < 10 else "moderate",
                 0.85 - power_dev * 0.001),
            )

    def _create_charter_party(self, voyage: Voyage):
        self.db.execute(
            """INSERT INTO charter_party
               (voyage_id, charterer, charter_type, speed_warranted_kn,
                consumption_warranted_mt_day, consumption_tolerance_pct,
                bor_warranted_pct_day, bor_tolerance_pct, sea_margin_pct,
                weather_exclusion_beaufort, off_hire_rate_usd_day)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (voyage.voyage_id, voyage.charterer or "Unknown", "voyage",
             19.0, 120, 3.0, 0.15, 1.5, 15.0, 6, 80000),
        )
        dep = datetime.fromisoformat(voyage.actual_departure) if voyage.actual_departure \
              else datetime.utcnow() - timedelta(days=10)
        for day in range(5):
            d = (dep + timedelta(days=day)).strftime("%Y-%m-%d")
            speed = random.uniform(18.5, 20.0)
            consumption = random.uniform(100, 140)
            self.db.execute(
                """INSERT INTO charter_performance
                   (voyage_id, record_date, speed_actual_kn, speed_warranted_kn,
                    speed_weather_corrected_kn, consumption_actual_mt,
                    consumption_warranted_mt, consumption_weather_corrected_mt,
                    consumption_deviation_pct, speed_deviation_pct,
                    wind_speed_kn, sea_state_beaufort,
                    performance_compliant, discrepancy_alert)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (voyage.voyage_id, d, speed, 19.0,
                 speed + random.uniform(-0.5, 0.5), consumption,
                 120, consumption * 0.97,
                 (consumption - 120) / 120 * 100, (speed - 19) / 19 * 100,
                 random.uniform(5, 25), random.randint(3, 6),
                 1, 0),
            )

    def _create_certificates(self, vessel: Vessel):
        cert_mgr = CertificateManager(self.db)
        now = datetime.utcnow()
        cert_configs = [
            ("IAPP", f"IAPP-{vessel.imo_number}", 5),
            ("IGC", f"IGC-{vessel.imo_number}", 5),
            ("ISM", f"ISM-{vessel.imo_number}", 5),
            ("ISPS", f"ISPS-{vessel.imo_number}", 5),
            ("CLASS", f"CLS-{vessel.imo_number}", 5),
            ("MLC", f"MLC-{vessel.imo_number}", 5),
            ("EIAPP", f"EIAPP-{vessel.imo_number}", None),
        ]
        for cert_type, cert_num, validity_years in cert_configs:
            if validity_years:
                expiry = now + timedelta(days=random.randint(-30, validity_years * 365))
            else:
                expiry = now + timedelta(days=random.randint(365, 365 * 10))
            issue = now - timedelta(days=random.randint(30, 1800))
            cert_mgr.add_certificate(
                vessel.vessel_id, cert_type, cert_num,
                expiry.isoformat(), issue.isoformat(),
                random.choice(["DNV", "Lloyd's Register", "Bureau Veritas"]))

    def _create_seemp_measures(self, vessel: Vessel):
        seemp = SEEMPCompliance(self.db)
        year = datetime.utcnow().year
        measures = random.sample([
            ("weather_routing", "AI-based weather routing optimization", 150),
            ("slow_steaming", "Speed reduction to 17.5kn on return legs", 200),
            ("trim_optimization", "Automatic trim optimization system", 80),
            ("hull_cleaning", "Underwater hull cleaning and propeller polish", 120),
            ("engine_tuning", "Main engine tuning for optimal SFOC", 60),
            ("waste_heat_recovery", "Waste heat recovery for cargo reliquefaction", 100),
        ], k=random.randint(2, 4))
        for measure_type, description, saving in measures:
            seemp.add_measure(
                vessel.vessel_id, year, measure_type, description, saving)
