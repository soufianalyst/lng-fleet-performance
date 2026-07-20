#!/usr/bin/env python3
"""
LNG Carrier Fleet Performance Management System
Main CLI Interface
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lng_fleet_performance.database.connection import DatabaseManager
from lng_fleet_performance.database.schema import create_all_tables
from lng_fleet_performance.demo.generate_data import DemoDataGenerator
from lng_fleet_performance.models.vessel import Vessel, VesselTank
from lng_fleet_performance.models.voyage import Voyage
from lng_fleet_performance.modules.voyage_optimization import VoyageOptimization
from lng_fleet_performance.modules.cargo_monitoring import CargoMonitoring
from lng_fleet_performance.modules.hull_machinery import HullMachinery
from lng_fleet_performance.modules.cii_compliance import CIICompliance
from lng_fleet_performance.modules.digital_twin import DigitalTwin
from lng_fleet_performance.modules.charter_party import CharterPartyVerification
from lng_fleet_performance.modules.eca_optimization import ECAOptimization
from lng_fleet_performance.utils.reporting import ReportGenerator
from lng_fleet_performance.utils.weather import WeatherEngine


class FleetPerformanceCLI:
    def __init__(self, db_path="lng_fleet.db"):
        self.db = DatabaseManager(db_path)
        create_all_tables(self.db)
        self.report = ReportGenerator(self.db)

    def print_banner(self):
        print("""
╔══════════════════════════════════════════════════════════════╗
║        LNG CARRIER FLEET PERFORMANCE MANAGEMENT SYSTEM       ║
║                    v1.0 — July 2026                          ║
║                                                              ║
║  Modules: Voyage | Cargo | Machinery | CII | Digital Twin    ║
║           Charter Party | ECA & Emissions                     ║
╚══════════════════════════════════════════════════════════════╝
        """)

    def print_menu(self):
        print("""
┌──────────────────────────────────────────────────────────────┐
│ MAIN MENU                                                     │
├──────────────────────────────────────────────────────────────┤
│  1. Fleet Overview                                            │
│  2. Voyage Management                                         │
│  3. Voyage Optimization                                       │
│  4. Cargo & BOR Monitoring                                    │
│  5. Hull & Machinery Performance                              │
│  6. CII & Regulatory Compliance                               │
│  7. Digital Twin & Predictive Maintenance                     │
│  8. Charter Party Verification                                │
│  9. ECA Zone & Emissions                                      │
│ 10. Emissions Summary                                         │
│ 11. Generate Demo Data                                        │
│  0. Exit                                                      │
└──────────────────────────────────────────────────────────────┘
        """)

    def run(self):
        self.print_banner()
        while True:
            self.print_menu()
            choice = input("  Select option: ").strip()
            if choice == "1":
                self._fleet_overview()
            elif choice == "2":
                self._voyage_management()
            elif choice == "3":
                self._voyage_optimization()
            elif choice == "4":
                self._cargo_monitoring()
            elif choice == "5":
                self._hull_machinery()
            elif choice == "6":
                self._cii_compliance()
            elif choice == "7":
                self._digital_twin()
            elif choice == "8":
                self._charter_party()
            elif choice == "9":
                self._eca_emissions()
            elif choice == "10":
                self._emissions_summary()
            elif choice == "11":
                self._generate_demo_data()
            elif choice == "0":
                print("\n  Goodbye.\n")
                break
            else:
                print("  Invalid option. Try again.")

    def _select_vessel(self) -> Vessel | None:
        vessels = Vessel.list_all(self.db)
        if not vessels:
            print("  No vessels in database. Generate demo data first (option 11).")
            return None
        print("\n  Available Vessels:")
        for v in vessels:
            print(f"    [{v.vessel_id}] {v.vessel_name} ({v.imo_number}) — {v.flag_state} — {v.propulsion_type}")
        try:
            vid = int(input("  Select vessel ID: "))
            return Vessel.get_by_id(self.db, vid)
        except (ValueError, TypeError):
            print("  Invalid selection.")
            return None

    def _select_voyage(self, vessel_id: int) -> Voyage | None:
        voyages = Voyage.list_by_vessel(self.db, vessel_id)
        if not voyages:
            print("  No voyages for this vessel.")
            return None
        print("\n  Voyages:")
        for v in voyages:
            print(f"    [{v.voyage_id}] {v.voyage_number}: {v.load_port} → {v.discharge_port} "
                  f"({v.status}) — {v.cargo_quantity_mt:.0f} mt")
        try:
            vid = int(input("  Select voyage ID: "))
            return Voyage.get_by_id(self.db, vid)
        except (ValueError, TypeError):
            print("  Invalid selection.")
            return None

    def _fleet_overview(self):
        print("\n" + "=" * 70)
        print("  FLEET OVERVIEW")
        print("=" * 70)
        overview = self.report.fleet_overview()
        if not overview:
            print("  No vessels found.")
            return
        print(f"\n  {'Name':<25} {'IMO':<10} {'Flag':<10} {'Type':<8} {'CII':<5} {'Voyages':<8}")
        print("  " + "-" * 70)
        for v in overview:
            print(f"  {v['name']:<25} {v['imo']:<10} {v['flag']:<10} "
                  f"{v['type']:<8} {v['latest_cii_rating'] or 'N/A':<5} "
                  f"{v['completed_voyages'] + v['active_voyages']:<8}")
        print()

    def _voyage_management(self):
        vessel = self._select_vessel()
        if not vessel:
            return
        voyages = Voyage.list_by_vessel(self.db, vessel.vessel_id)
        if not voyages:
            print("  No voyages found.")
            return
        for v in voyages:
            summary = self.report.voyage_summary(v.voyage_id)
            print(f"\n  Voyage {summary['voyage']}: {summary['route']}")
            print(f"    Status: {summary['status']}")
            print(f"    Distance: {summary['distance_nm']:.0f} nm")
            print(f"    Total Fuel: {summary['total_fuel_mt']:.1f} mt")
            print(f"    CO2 Emissions: {summary['co2_emissions_mt']:.1f} mt")
            print(f"    Avg BOR: {summary['avg_bor_pct_day']:.4f} %/day")
            print(f"    EU ETS: {'Yes' if summary['eu_ets_applicable'] else 'No'}")

    def _voyage_optimization(self):
        print("\n  === VOYAGE OPTIMIZATION ===")
        print("  1. Optimize route")
        print("  2. Speed-power analysis")
        print("  3. JIT arrival estimate")
        print("  4. Fuel consumption estimate")
        choice = input("  Select: ").strip()
        voy_opt = VoyageOptimization(self.db)
        if choice == "1":
            try:
                lat1 = float(input("  Start latitude: "))
                lon1 = float(input("  Start longitude: "))
                lat2 = float(input("  End latitude: "))
                lon2 = float(input("  End longitude: "))
                speed = float(input("  Speed (kn) [19.0]: ") or "19.0")
                result = voy_opt.optimize_route(lat1, lon1, lat2, lon2, speed)
                print(f"\n  Route Optimization Result:")
                print(f"    Waypoints: {len(result['waypoints'])}")
                print(f"    Total Distance: {result['total_distance_nm']:.0f} nm")
                print(f"    Total Time: {result['total_time_hours']:.1f} hours")
                print(f"    Total Fuel: {result['total_fuel_mt']:.2f} mt")
                print(f"    Avg Speed: {result['average_speed_kn']:.1f} kn")
                print(f"    ECA Time: {result['eca_time_hours']:.1f} hours")
            except ValueError:
                print("  Invalid input.")
        elif choice == "2":
            vessel = self._select_vessel()
            if vessel:
                voyage = self._select_voyage(vessel.vessel_id)
                if voyage:
                    result = voy_opt.speed_power_analysis(voyage.voyage_id)
                    self._print_dict(result)
        elif choice == "3":
            vessel = self._select_vessel()
            if vessel:
                voyage = self._select_voyage(vessel.vessel_id)
                if voyage:
                    result = voy_opt.jit_arrival_estimate(voyage.voyage_id)
                    self._print_dict(result)
        elif choice == "4":
            dist = float(input("  Distance (nm): "))
            speed = float(input("  Speed (kn) [19.0]: ") or "19.0")
            mcr = float(input("  Engine MCR (kW) [15000]: ") or "15000")
            mass = float(input("  Displacement (mt) [80000]: ") or "80000")
            result = voy_opt.fuel_consumption_estimate(dist, speed, mcr, mass)
            self._print_dict(result)

    def _cargo_monitoring(self):
        print("\n  === CARGO & BOR MONITORING ===")
        print("  1. BOR analysis (energy balance)")
        print("  2. Stratification analysis")
        print("  3. Rollover detection")
        print("  4. Reliquefaction performance")
        print("  5. Cargo condition forecast")
        choice = input("  Select: ").strip()
        cargo = CargoMonitoring(self.db)
        if choice == "1":
            q_in = float(input("  Heat ingress (kW) [50]: ") or "50")
            q_out = float(input("  Heat removal (kW) [30]: ") or "30")
            w_comp = float(input("  Compression work (kW) [100]: ") or "100")
            mass = float(input("  Cargo mass (mt) [80000]: ") or "80000")
            result = cargo.calculate_bor_energy_balance(1, q_in, q_out, w_comp, mass)
            self._print_dict(result)
        elif choice == "2":
            top = float(input("  Top temperature (K) [111.3]: ") or "111.3")
            mid = float(input("  Mid temperature (K) [111.0]: ") or "111.0")
            bot = float(input("  Bottom temperature (K) [110.8]: ") or "110.8")
            result = cargo.stratification_analysis(top, mid, bot)
            self._print_dict(result)
        elif choice == "3":
            top_t = float(input("  Top temp (K) [111.2]: ") or "111.2")
            bot_t = float(input("  Bottom temp (K) [111.0]: ") or "111.0")
            top_d = float(input("  Top density (kg/m3) [425]: ") or "425")
            bot_d = float(input("  Bottom density (kg/m3) [426]: ") or "426")
            result = cargo.rollover_detection(top_t, bot_t, top_d, bot_d)
            self._print_dict(result)
        elif choice == "4":
            bog = float(input("  BOG inlet (kg/h) [1200]: ") or "1200")
            power = float(input("  Power consumed (kW) [600]: ") or "600")
            reliq = float(input("  Reliquefied (kg/h) [1000]: ") or "1000")
            design = float(input("  Design capacity (kg/h) [1200]: ") or "1200")
            result = cargo.reliquefaction_performance(bog, power, reliq, design)
            self._print_dict(result)
        elif choice == "5":
            temp = float(input("  Current temp (K) [111.0]: ") or "111.0")
            pres = float(input("  Current pressure (bar) [1.05]: ") or "1.05")
            fill = float(input("  Fill level (%) [90]: ") or "90")
            sea = float(input("  Sea temp (K) [288]: ") or "288")
            days = float(input("  Days remaining [10]: ") or "10")
            result = cargo.cargo_condition_forecast(temp, pres, fill, sea, days)
            self._print_dict(result)

    def _hull_machinery(self):
        print("\n  === HULL & MACHINERY PERFORMANCE ===")
        print("  1. Engine performance index")
        print("  2. Hull fouling assessment")
        print("  3. Shaft power analysis")
        print("  4. Auxiliary engine load profile")
        choice = input("  Select: ").strip()
        hm = HullMachinery(self.db)
        if choice in ("1", "2", "3", "4"):
            vessel = self._select_vessel()
            if vessel:
                voyage = self._select_voyage(vessel.vessel_id)
                if voyage:
                    if choice == "1":
                        result = hm.engine_performance_index(voyage.voyage_id)
                    elif choice == "2":
                        result = hm.hull_fouling_assessment(vessel.vessel_id)
                    elif choice == "3":
                        result = hm.shaft_power_measurement(voyage.voyage_id)
                    else:
                        result = hm.auxiliary_engine_load_profile(voyage.voyage_id)
                    self._print_dict(result)

    def _cii_compliance(self):
        print("\n  === CII & REGULATORY COMPLIANCE ===")
        print("  1. Calculate CII")
        print("  2. CII what-if scenario")
        print("  3. EU ETS calculation")
        print("  4. FuelEU Maritime calculation")
        print("  5. View CII boundaries")
        choice = input("  Select: ").strip()
        cii = CIICompliance(self.db)
        if choice == "1":
            vessel = self._select_vessel()
            if vessel:
                result = cii.calculate_cii(vessel.vessel_id)
                self._print_dict(result)
        elif choice == "2":
            vessel = self._select_vessel()
            if vessel:
                spd = float(input("  Speed reduction (%) [5]: ") or "5")
                result = cii.cii_what_if(vessel.vessel_id, spd)
                self._print_dict(result)
        elif choice == "3":
            vessel = self._select_vessel()
            if vessel:
                voyage = self._select_voyage(vessel.vessel_id)
                if voyage:
                    eua = float(input("  EUA price (EUR) [80]: ") or "80")
                    result = cii.calculate_eu_ets(voyage.voyage_id, eua)
                    self._print_dict(result)
        elif choice == "4":
            vessel = self._select_vessel()
            if vessel:
                voyage = self._select_voyage(vessel.vessel_id)
                if voyage:
                    result = cii.calculate_fueleu(voyage.voyage_id)
                    self._print_dict(result)
        elif choice == "5":
            result = cii.get_boundaries()
            self._print_dict(result)

    def _digital_twin(self):
        print("\n  === DIGITAL TWIN & PREDICTIVE MAINTENANCE ===")
        print("  1. Fleet health summary")
        print("  2. Engine health assessment")
        print("  3. Hull health assessment")
        print("  4. Scenario simulation")
        choice = input("  Select: ").strip()
        dt = DigitalTwin(self.db)
        if choice in ("1", "2", "3", "4"):
            vessel = self._select_vessel()
            if vessel:
                if choice == "1":
                    result = dt.fleet_health_summary(vessel.vessel_id)
                elif choice == "2":
                    result = dt.engine_health_assessment(vessel.vessel_id)
                elif choice == "3":
                    result = dt.hull_health_assessment(vessel.vessel_id)
                else:
                    spd = float(input("  Speed change (%) [0]: ") or "0")
                    foul = float(input("  Fouling change (%) [0]: ") or "0")
                    temp = float(input("  Cargo temp change (K) [0]: ") or "0")
                    result = dt.scenario_simulation(vessel.vessel_id, spd, foul, temp)
                self._print_dict(result)

    def _charter_party(self):
        print("\n  === CHARTER PARTY VERIFICATION ===")
        print("  1. Verify speed & consumption")
        print("  2. Verify BOR")
        print("  3. Create audit trail")
        choice = input("  Select: ").strip()
        cp = CharterPartyVerification(self.db)
        if choice in ("1", "2", "3"):
            vessel = self._select_vessel()
            if vessel:
                voyage = self._select_voyage(vessel.vessel_id)
                if voyage:
                    if choice == "1":
                        result = cp.verify_speed_consumption(voyage.voyage_id)
                    elif choice == "2":
                        result = cp.verify_bor(voyage.voyage_id)
                    else:
                        result = cp.create_audit_trail(voyage.voyage_id)
                    self._print_dict(result)

    def _eca_emissions(self):
        print("\n  === ECA ZONE & EMISSIONS ===")
        print("  1. Check position compliance")
        print("  2. Optimize fuel switch")
        print("  3. SCR performance")
        print("  4. Multi-constraint optimization")
        choice = input("  Select: ").strip()
        eca = ECAOptimization(self.db)
        if choice == "1":
            lat = float(input("  Latitude: "))
            lon = float(input("  Longitude: "))
            fuel = input("  Current fuel type [VLSFO]: ") or "VLSFO"
            result = eca.check_position_compliance(lat, lon, fuel)
            self._print_dict(result)
        elif choice == "2":
            vessel = self._select_vessel()
            if vessel:
                lat = float(input("  Current latitude: "))
                lon = float(input("  Current longitude: "))
                fuel = input("  Current fuel [VLSFO]: ") or "VLSFO"
                speed = float(input("  Speed (kn) [19]: ") or "19")
                result = eca.optimize_fuel_switch(vessel.vessel_id, lat, lon, fuel, speed)
                self._print_dict(result)
        elif choice == "3":
            vessel = self._select_vessel()
            if vessel:
                voyage = self._select_voyage(vessel.vessel_id)
                if voyage:
                    result = eca.scr_performance(voyage.voyage_id)
                    self._print_dict(result)
        elif choice == "4":
            vessel = self._select_vessel()
            if vessel:
                eua = float(input("  EUA price (EUR) [80]: ") or "80")
                result = eca.multi_constraint_optimization(vessel.vessel_id, eua_price_eur=eua)
                self._print_dict(result)

    def _emissions_summary(self):
        vessel = self._select_vessel()
        if vessel:
            result = self.report.emissions_summary(vessel.vessel_id)
            self._print_dict(result)

    def _generate_demo_data(self):
        print("\n  Generating demo data (this may take a moment)...")
        gen = DemoDataGenerator(self.db)
        gen.generate_all()
        print("  Demo data generated successfully!\n")

    def _print_dict(self, data, indent=2):
        prefix = " " * indent
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    print(f"{prefix}{k}:")
                    self._print_dict(v, indent + 4)
                elif isinstance(v, list):
                    print(f"{prefix}{k}: [{len(v)} items]")
                    for item in v[:5]:
                        if isinstance(item, dict):
                            self._print_dict(item, indent + 4)
                        else:
                            print(f"{prefix}    - {item}")
                else:
                    print(f"{prefix}{k}: {v}")
        else:
            print(f"{prefix}{data}")


def main():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lng_fleet.db")
    cli = FleetPerformanceCLI(db_path)
    cli.run()


if __name__ == "__main__":
    main()
