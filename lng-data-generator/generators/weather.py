import numpy as np
from simulator import VesselState
from utils.random_utils import AR1Process, StormEvent


class WeatherGenerator:
    def __init__(self, config):
        self.config = config
        self.weather_cfg = config.get("weather", {})
        self.storm_cfg = self.weather_cfg.get("storm", {})
        self.ac_cfg = self.weather_cfg.get("autocorrelation", {})
        self.regions = self.weather_cfg.get("regions", {})
        self.storm_timer = 0.0

    def initialize(self, state: VesselState):
        region = self._get_region(state.lat)
        state.weather_region = region
        r = self.regions.get(region, self.regions.get("temperate"))
        ac_wind = self.ac_cfg.get("wind", 0.95)
        ac_wave = self.ac_cfg.get("wave", 0.97)
        ac_swell = self.ac_cfg.get("swell", 0.98)
        ac_temp = self.ac_cfg.get("temperature", 0.999)
        ac_press = self.ac_cfg.get("pressure", 0.998)
        ac_vis = self.ac_cfg.get("visibility", 0.93)
        state.ar1_wind = AR1Process(r["wind_mean_kn"], r["wind_std_kn"], ac_wind, 1)
        state.ar1_wave = AR1Process(r["wave_mean_m"], r["wave_mean_m"] * 0.45, ac_wave, 1, min_val=0.0)
        state.ar1_swell = AR1Process(r["wave_mean_m"] * 0.3, r["wave_mean_m"] * 0.1, ac_swell, 1, min_val=0.0)
        state.ar1_sea_temp = AR1Process(r["sea_temp_c"], 1.0, ac_temp, 1)
        state.ar1_air_temp = AR1Process(r["air_temp_c"], 2.0, ac_temp, 1)
        state.ar1_pressure = AR1Process(1013.0, 8.0, ac_press, 1, min_val=970.0, max_val=1045.0)
        state.ar1_visibility = AR1Process(r["visibility_nm"], 3.0, ac_vis, 1, min_val=0.1, max_val=12.0)
        state.wind_speed_kn = state.ar1_wind.step()
        state.wave_height_m = state.ar1_wave.step()
        state.swell_height_m = state.ar1_swell.step()
        state.sea_temp_c = state.ar1_sea_temp.step()
        state.air_temp_c = state.ar1_air_temp.step()
        state.pressure_hpa = state.ar1_pressure.step()
        state.visibility_nm = state.ar1_visibility.step()
        state.wind_direction_deg = np.random.uniform(0, 360)
        state.wave_direction_deg = state.wind_direction_deg + np.random.normal(0, 20)

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        if state.ar1_wind is None:
            self.initialize(state)
        # Re-evaluate weather region as vessel crosses latitude bands
        current_region = self._get_region(state.lat)
        if current_region != getattr(state, "weather_region", None):
            self.initialize(state)
        # Storm check: once per 24h window, probability from region config
        region = self.regions.get(getattr(state, "weather_region", "temperate"),
                                  self.regions.get("temperate"))
        daily_storm_prob = region.get("storm_probability", 0.05)
        self.storm_timer += dt_hours
        if not state.storm.active and self.storm_timer >= 24.0:
            if np.random.random() < daily_storm_prob:
                state.storm.trigger(
                    duration_hours=self.storm_cfg.get("duration_hours", 8),
                    ramp_up_hours=self.storm_cfg.get("ramp_up_hours", 3),
                    ramp_down_hours=self.storm_cfg.get("ramp_down_hours", 5),
                )
            self.storm_timer = 0.0
        storm_intensity = state.storm.update(dt_hours)
        base_wind = state.ar1_wind.step()
        wind_mult = self.storm_cfg.get("wind_multiplier", 3.5)
        state.wind_speed_kn = base_wind * (1.0 + storm_intensity * (wind_mult - 1.0))
        state.wind_speed_kn = max(0.0, state.wind_speed_kn + np.random.normal(0, 0.3))
        state.wind_direction_deg = (state.wind_direction_deg + np.random.normal(0, 5)) % 360
        base_wave = state.ar1_wave.step()
        wave_mult = self.storm_cfg.get("wave_multiplier", 4.0)
        state.wave_height_m = base_wave * (1.0 + storm_intensity * (wave_mult - 1.0))
        state.wave_height_m = max(0.1, state.wave_height_m + np.random.normal(0, 0.05))
        state.wave_direction_deg = (state.wind_direction_deg + np.random.normal(0, 15)) % 360
        state.swell_height_m = state.ar1_swell.step() * (1.0 + storm_intensity * 1.5)
        state.swell_height_m = max(0.0, state.swell_height_m)
        state.sea_temp_c = state.ar1_sea_temp.step()
        state.air_temp_c = state.ar1_air_temp.step()
        wind_cooling = min(3.0, state.wind_speed_kn * 0.05)
        state.air_temp_c -= wind_cooling
        state.pressure_hpa = state.ar1_pressure.step()
        if storm_intensity > 0.5:
            state.pressure_hpa -= storm_intensity * 15.0
        state.visibility_nm = state.ar1_visibility.step()
        if storm_intensity > 0.3:
            state.visibility_nm *= max(0.1, 1.0 - storm_intensity * 0.7)
        state.visibility_nm = max(0.1, min(12.0, state.visibility_nm))

    def _get_region(self, lat):
        for name, region in self.regions.items():
            lat_range = region.get("lat_range", [-90, 90])
            if lat_range[0] <= lat <= lat_range[1]:
                return name
        return "temperate"
