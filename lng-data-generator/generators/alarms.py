import numpy as np
from simulator import VesselState, AlarmState


class AlarmGenerator:
    def __init__(self, config):
        self.config = config
        self.alarm_timers = {}

    def step(self, state: VesselState, dt_seconds: float):
        self._check_pressure_alarm(state)
        self._check_exhaust_temp(state)
        self._check_sfoc_degradation(state)
        self._check_bog_level(state)
        self._check_visibility(state)
        self._check_wave_severity(state)
        self._check_generator(state)
        self._check_fuel_level(state)
        self._check_random_failure(state, dt_seconds)

    def _check_pressure_alarm(self, state):
        for tank in state.cargo_tanks:
            if tank.pressure_bar > 1.30:
                self._set_alarm(state, f"high_pressure_{tank.name}", "critical",
                                f"Tank {tank.name} pressure {tank.pressure_bar:.3f} bar exceeds limit")
            elif tank.pressure_bar > 1.25:
                self._set_alarm(state, f"high_pressure_{tank.name}", "warning",
                                f"Tank {tank.name} pressure {tank.pressure_bar:.3f} bar approaching limit")
            else:
                self._clear_alarm(state, f"high_pressure_{tank.name}")

    def _check_exhaust_temp(self, state):
        if state.exhaust_temp_c > 410:
            self._set_alarm(state, "high_exhaust_temp", "critical",
                            f"Exhaust temp {state.exhaust_temp_c:.0f}C exceeds limit")
        elif state.exhaust_temp_c > 390:
            self._set_alarm(state, "high_exhaust_temp", "warning",
                            f"Exhaust temp {state.exhaust_temp_c:.0f}C elevated")
        else:
            self._clear_alarm(state, "high_exhaust_temp")

    def _check_sfoc_degradation(self, state):
        if state.sfoc_actual > state.engine_sfoc_rated * 1.15:
            self._set_alarm(state, "sfoc_degradation", "warning",
                            f"SFOC {state.sfoc_actual:.1f} g/kWh degraded from rated {state.engine_sfoc_rated:.1f}")

    def _check_bog_level(self, state):
        if state.bog_generation_kg_h > 4000:
            self._set_alarm(state, "high_bog_rate", "warning",
                            f"BOG rate {state.bog_generation_kg_h:.0f} kg/h elevated")

    def _check_visibility(self, state):
        if state.visibility_nm < 1.0:
            self._set_alarm(state, "low_visibility", "critical",
                            f"Visibility {state.visibility_nm:.1f} nm very low")
        elif state.visibility_nm < 3.0:
            self._set_alarm(state, "low_visibility", "warning",
                            f"Visibility {state.visibility_nm:.1f} nm reduced")

    def _check_wave_severity(self, state):
        if state.wave_height_m > 6.0:
            self._set_alarm(state, "heavy_weather", "critical",
                            f"Wave height {state.wave_height_m:.1f}m - heavy weather")

    def _check_generator(self, state):
        # Standby gensets are normally OFF — only alarm on blackout (all units down)
        online = [a for a in state.aux_engines if a.running]
        if not online:
            self._set_alarm(state, "blackout", "critical",
                            "All auxiliary generators offline")
        else:
            self._clear_alarm(state, "blackout")

    def _check_fuel_level(self, state):
        if state.fuel.lng_level_m3 < state.fuel.lng_capacity_m3 * 0.15:
            self._set_alarm(state, "low_lng_fuel", "warning",
                            f"LNG fuel level {state.fuel.lng_level_m3:.0f}m3 low")

    def _check_random_failure(self, state, dt_seconds):
        dt_hours = dt_seconds / 3600.0
        key = "pump_seal"
        self.alarm_timers.setdefault(key, 0.0)
        self.alarm_timers[key] += dt_hours
        if self.alarm_timers[key] > 500 and np.random.random() < 0.0005 * dt_hours:
            self._set_alarm(state, key, "warning", "Pump seal leakage detected")
            self.alarm_timers[key] = 0.0

    def _set_alarm(self, state, alarm_type, severity, description):
        for a in state.alarms:
            if a.alarm_type == alarm_type:
                a.active = True
                a.severity = severity
                a.description = description
                return
        state.alarms.append(AlarmState(
            alarm_type=alarm_type, severity=severity,
            active=True, timestamp=state.time, description=description,
        ))

    def _clear_alarm(self, state, alarm_type):
        for a in state.alarms:
            if a.alarm_type == alarm_type:
                a.active = False
                return
