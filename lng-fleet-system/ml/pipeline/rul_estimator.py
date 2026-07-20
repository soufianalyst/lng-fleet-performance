import numpy as np
import pandas as pd
import joblib
from scipy.stats import weibull_min, norm
import os

from .config import RULEstimatorConfig


_WEAR_FACTORS = {
    "cylinder_liner": ["exhaust_temp", "sfoc"],
    "piston_ring": ["sfoc", "shaft_power"],
    "turbocharger_bearing": ["turbocharger_speed", "exhaust_temp"],
    "fuel_pump": ["sfoc", "scavenge_air_pressure"],
    "compressor_valve": ["scavenge_air_pressure", "turbocharger_speed"],
}


class RULEstimator:
    def __init__(self, config: RULEstimatorConfig = None):
        self.config = config or RULEstimatorConfig()
        self._degradation_baselines = {}

    def fit_baselines(self, df: pd.DataFrame) -> "RULEstimator":
        for component, sensors in _WEAR_FACTORS.items():
            available = [s for s in sensors if s in df.columns]
            if available:
                self._degradation_baselines[component] = {
                    s: float(df[s].mean()) for s in available
                }
        return self

    def _degradation_score(self, component: str, sensor_readings: dict) -> float:
        baselines = self._degradation_baselines.get(component, {})
        if not baselines:
            return 0.5
        deviations = []
        for sensor, baseline in baselines.items():
            current = sensor_readings.get(sensor, baseline)
            if baseline != 0:
                deviations.append(abs(current - baseline) / abs(baseline))
        return float(np.clip(np.mean(deviations) if deviations else 0.5, 0, 2))

    def predict(self, component: str,
                days_since_last_maintenance: int = 0,
                sensor_readings: dict = None) -> dict:
        if component not in self.config.components:
            raise ValueError(f"Unknown component: {component}. Choose from {self.config.components}")

        shape = self.config.weibull_shapes[component]
        scale = self.config.weibull_scales[component]
        degradation = self._degradation_score(component, sensor_readings or {})

        adjusted_scale = scale * (1.0 / (1.0 + degradation))
        base_rul = weibull_min.mean(shape, scale=adjusted_scale)
        remaining = max(0, base_rul - days_since_last_maintenance)

        current_time = days_since_last_maintenance
        reliability = 1.0 - weibull_min.cdf(current_time, shape, scale=adjusted_scale)
        confidence = float(np.clip(reliability * 100, 0, 100))

        p10 = weibull_min.ppf(0.1, shape, scale=adjusted_scale) - current_time
        p90 = weibull_min.ppf(0.9, shape, scale=adjusted_scale) - current_time

        if confidence < 20:
            action = f"Immediate inspection required for {component.replace('_', ' ')}"
        elif confidence < 50:
            action = f"Plan maintenance for {component.replace('_', ' ')} within next {int(remaining * 0.3)} days"
        else:
            action = f"Continue monitoring {component.replace('_', ' ')}"

        return {
            "component": component,
            "days_remaining": int(round(remaining)),
            "confidence_level": float(round(confidence, 1)),
            "prediction_interval_days": {"p10": int(round(max(0, p10))), "p90": int(round(max(0, p90)))},
            "degradation_score": float(round(degradation, 3)),
            "recommended_action": action,
        }

    def predict_all(self, days_since_maintenance: dict = None,
                    sensor_readings: dict = None) -> list:
        results = []
        for component in self.config.components:
            days = (days_since_maintenance or {}).get(component, 0)
            result = self.predict(component, days, sensor_readings)
            results.append(result)
        return results

    def save(self, path: str = None) -> str:
        path = path or self.config.model_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({
            "config": self.config,
            "degradation_baselines": self._degradation_baselines,
        }, path)
        return path

    def load(self, path: str = None) -> "RULEstimator":
        path = path or self.config.model_path
        data = joblib.load(path)
        self.config = data["config"]
        self._degradation_baselines = data.get("degradation_baselines", {})
        return self
