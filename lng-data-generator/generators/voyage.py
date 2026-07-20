import math
import numpy as np
from simulator import VesselState
from utils.physics import haversine_nm, bearing_deg, interpolate_position


class VoyageGenerator:
    """Voyage lifecycle: sea_passage -> arrival -> discharging/loading ->
    port_stay -> departure -> sea_passage (return leg). Repeats indefinitely."""

    # Phase durations (hours)
    APPROACH_HOURS = 4.0
    PORT_STAY_HOURS = 24.0
    DEPARTURE_HOURS = 4.0

    def __init__(self, config):
        self.config = config

    def initialize_voyage(self, state: VesselState, route: dict):
        state.route_waypoints = route["waypoints"]
        state.waypoint_index = 0
        state.route_index = 0
        state.route_progress_nm = 0.0
        state.leg_type = "laden"
        wp = state.route_waypoints
        if len(wp) >= 2:
            state.lat = wp[0]["lat"]
            state.lon = wp[0]["lon"]
            state.total_route_distance_nm = sum(
                haversine_nm(wp[i]["lat"], wp[i]["lon"], wp[i+1]["lat"], wp[i+1]["lon"])
                for i in range(len(wp) - 1)
            )
            state.distance_to_go_nm = state.total_route_distance_nm
            state.heading = bearing_deg(wp[0]["lat"], wp[0]["lon"], wp[1]["lat"], wp[1]["lon"])
            state.cog = state.heading
            state.sog = state.service_speed_kn
            state.stw = state.service_speed_kn
            state.phase = "sea_passage"

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        if state.phase == "sea_passage":
            self._handle_sea_passage(state, dt_hours)
        elif state.phase == "arrival":
            self._handle_arrival(state, dt_hours)
        elif state.phase in ("discharging", "loading"):
            self._handle_cargo_ops(state, dt_hours)
        elif state.phase == "port_stay":
            self._handle_port_stay(state, dt_hours)
        elif state.phase == "departure":
            self._handle_departure(state, dt_hours)
        elif state.phase == "emergency_stop":
            self._handle_emergency_stop(state, dt_hours)
        elif state.phase == "engine_failure":
            self._handle_engine_failure(state, dt_hours)
        elif state.phase == "engine_restart":
            self._handle_engine_restart(state, dt_hours)

    def _handle_sea_passage(self, state: VesselState, dt_hours: float):
        state.engine_running = True
        # Weather penalty on speed (realistic: ships slow down in heavy weather)
        weather_penalty = 1.0
        if state.wave_height_m > 4.0:
            weather_penalty = max(0.6, 1.0 - (state.wave_height_m - 4.0) * 0.06)
        effective_speed = state.service_speed_kn * weather_penalty
        effective_speed = min(effective_speed, 21.0)
        if effective_speed < 0.5:
            effective_speed = 0.5

        distance_covered = effective_speed * dt_hours
        state.route_progress_nm += distance_covered
        state.distance_sailed_nm += distance_covered
        state.leg_distance_nm += distance_covered

        # Arrival check
        if state.route_progress_nm >= state.total_route_distance_nm:
            state.route_progress_nm = state.total_route_distance_nm
            state.phase = "arrival"
            state.port_timer = 0.0

        # Position along route
        lat, lon, heading = self._position_along_route(state)
        state.lat = lat
        state.lon = lon
        # Smooth heading toward track
        angle_diff = heading - state.heading
        while angle_diff > 180:
            angle_diff -= 360
        while angle_diff < -180:
            angle_diff += 360
        max_turn = 2.0
        state.heading = (state.heading + max(-max_turn, min(max_turn, angle_diff))) % 360
        state.cog = state.heading
        state.rudder_angle += (max(-35, min(35, angle_diff * 0.8)) - state.rudder_angle) * 0.1

        state.sog = effective_speed + np.random.normal(0, 0.05)
        state.stw = state.sog + np.random.normal(0, 0.15)  # current set/drift
        state.sog = max(0.0, min(21.0, state.sog))
        state.stw = max(0.0, min(21.0, state.stw))
        state.distance_to_go_nm = max(0.0, state.total_route_distance_nm - state.route_progress_nm)

    def _position_along_route(self, state: VesselState):
        """Interpolate position at route_progress_nm along waypoints."""
        wp = state.route_waypoints
        if len(wp) < 2:
            return state.lat, state.lon, state.heading
        accumulated = min(state.route_progress_nm, state.total_route_distance_nm)
        dist_so_far = 0.0
        for i in range(len(wp) - 1):
            seg = haversine_nm(wp[i]["lat"], wp[i]["lon"], wp[i+1]["lat"], wp[i+1]["lon"])
            if dist_so_far + seg >= accumulated and seg > 0.001:
                frac = (accumulated - dist_so_far) / seg
                lat, lon = interpolate_position(
                    wp[i]["lat"], wp[i]["lon"], wp[i+1]["lat"], wp[i+1]["lon"], frac
                )
                hdg = bearing_deg(wp[i]["lat"], wp[i]["lon"], wp[i+1]["lat"], wp[i+1]["lon"])
                return lat, lon, hdg
            dist_so_far += seg
        # At/past end
        last = wp[-1]
        prev = wp[-2]
        hdg = bearing_deg(prev["lat"], prev["lon"], last["lat"], last["lon"])
        return last["lat"], last["lon"], hdg

    def _handle_arrival(self, state: VesselState, dt_hours: float):
        """Approach and berthing: decelerate to stop."""
        state.port_timer += dt_hours
        state.sog = max(0.0, state.sog - 3.0 * dt_hours)
        state.stw = state.sog
        if state.sog < 0.5:
            state.engine_running = False
            state.rpm = 0.0
            state.shaft_power_kw = 0.0
        if state.port_timer >= self.APPROACH_HOURS:
            state.port_timer = 0.0
            state.sog = 0.0
            state.stw = 0.0
            state.cargo_operation_progress = 0.0
            if state.leg_type == "laden":
                state.phase = "discharging"
            else:
                state.phase = "loading"

    def _handle_cargo_ops(self, state: VesselState, dt_hours: float):
        """Wait for cargo generator to complete load/discharge (progress >= 95%)."""
        state.sog = 0.0
        state.stw = 0.0
        state.engine_running = False
        if state.cargo_operation_progress >= 95.0:
            state.phase = "port_stay"
            state.port_timer = 0.0

    def _handle_port_stay(self, state: VesselState, dt_hours: float):
        state.sog = 0.0
        state.stw = 0.0
        state.engine_running = False
        state.port_timer += dt_hours
        if state.port_timer >= self.PORT_STAY_HOURS:
            state.port_timer = 0.0
            state.phase = "departure"
            state.engine_running = True
            state.engine_load_pct = 40.0

    def _handle_departure(self, state: VesselState, dt_hours: float):
        """Unberth, ramp up speed, then start the return leg."""
        state.port_timer += dt_hours
        state.sog = min(6.0, state.sog + 1.5 * dt_hours)
        state.stw = state.sog
        if state.port_timer >= self.DEPARTURE_HOURS:
            self._start_return_voyage(state)

    def _start_return_voyage(self, state: VesselState):
        """Reverse the route for the return leg and toggle laden/ballast."""
        state.route_waypoints = list(reversed(state.route_waypoints))
        state.waypoint_index = 0
        state.route_index = 0
        state.route_progress_nm = 0.0
        state.port_timer = 0.0
        state.leg_type = "ballast" if state.leg_type == "laden" else "laden"
        state.leg_co2_mt = 0.0
        state.leg_distance_nm = 0.0
        wp = state.route_waypoints
        state.total_route_distance_nm = sum(
            haversine_nm(wp[i]["lat"], wp[i]["lon"], wp[i+1]["lat"], wp[i+1]["lon"])
            for i in range(len(wp) - 1)
        )
        state.distance_to_go_nm = state.total_route_distance_nm
        state.heading = bearing_deg(wp[0]["lat"], wp[0]["lon"], wp[1]["lat"], wp[1]["lon"])
        state.cog = state.heading
        state.phase = "sea_passage"

    def _handle_emergency_stop(self, state: VesselState, dt_hours: float):
        state.rpm = max(0, state.rpm - 20 * dt_hours)
        state.sog = max(0, state.sog - 8.0 * dt_hours)  # crash stop ~2-3 h to drift
        state.stw = state.sog
        state.shaft_power_kw = max(0, state.shaft_power_kw - state.engine_mcr_kw * 0.5 * dt_hours)
        state.engine_load_pct = 0.0
        state.engine_running = False
        if state.sog < 0.5:
            state.phase = "engine_restart"

    def _handle_engine_failure(self, state: VesselState, dt_hours: float):
        state.rpm = max(0, state.rpm - 30 * dt_hours)
        state.sog = max(0, state.sog - 5.0 * dt_hours)
        state.stw = state.sog
        state.shaft_power_kw = 0.0
        state.engine_load_pct = 0.0
        state.engine_running = False
        if state.sog < 0.5:
            state.phase = "engine_restart"

    def _handle_engine_restart(self, state: VesselState, dt_hours: float):
        if not state.engine_running:
            state.engine_running = True
            state.engine_load_pct = 10.0
        target_rpm = 80.0
        state.rpm += (target_rpm - state.rpm) * 0.05
        state.engine_load_pct = min(50.0, state.engine_load_pct + 5 * dt_hours)
        state.sog = min(state.service_speed_kn * 0.6, state.sog + 1.0 * dt_hours)
        state.stw = state.sog
        if state.engine_load_pct >= 50.0:
            state.phase = "sea_passage"
