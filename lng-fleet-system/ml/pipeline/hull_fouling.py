import numpy as np
import pandas as pd
import joblib
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
from sklearn.preprocessing import StandardScaler
import os

from .config import HullFoulingConfig


class HullFoulingDetector:
    def __init__(self, config: HullFoulingConfig = None):
        self.config = config or HullFoulingConfig()
        self.scaler = StandardScaler()
        kernel = (ConstantKernel(1.0) * RBF(length_scale=self.config.length_scale)
                  + WhiteKernel(noise_level=0.1))
        self.gpr = GaussianProcessRegressor(
            kernel=kernel,
            alpha=self.config.alpha,
            n_restarts_optimizer=self.config.n_restarts_optimizer,
            random_state=42,
        )
        self._reference_power = None
        self._y_scaler = StandardScaler()

    def fit_reference(self, df: pd.DataFrame) -> "HullFoulingDetector":
        X = df[["speed"]].values
        y = df["power"].values.reshape(-1, 1)

        X_scaled = self.scaler.fit_transform(X)
        y_scaled = self._y_scaler.fit_transform(y).ravel()

        self.gpr.fit(X_scaled, y_scaled)
        self._reference_power = self.gpr
        return self

    def compute_delta_friction(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[["speed"]].values
        y_actual = df["power"].values

        X_scaled = self.scaler.transform(X)
        y_pred_scaled, _ = self.gpr.predict(X_scaled, return_std=True)
        y_pred = self._y_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()

        df = df.copy()
        df["expected_power"] = y_pred
        df["delta_friction"] = ((y_actual - y_pred) / y_pred) * 100
        return df

    def detect(self, df: pd.DataFrame) -> dict:
        df = self.compute_delta_friction(df)
        recent = df.tail(30)
        mean_loss = recent["delta_friction"].mean()
        trend = recent["delta_friction"].diff().mean()

        needs_cleaning = mean_loss > self.config.cleaning_loss_threshold

        return {
            "mean_delta_friction_pct": float(round(mean_loss, 2)),
            "trend_pct_per_period": float(round(trend, 2)),
            "needs_cleaning": bool(needs_cleaning),
            "cleaning_recommended": bool(needs_cleaning),
            "estimated_fuel_penalty_pct": float(round(max(0, mean_loss), 2)),
            "recent_readings": recent[["speed", "power", "expected_power", "delta_friction"]].to_dict(orient="records"),
        }

    def save(self, path: str = None) -> str:
        path = path or self.config.model_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({
            "gpr": self.gpr,
            "scaler": self.scaler,
            "y_scaler": self._y_scaler,
            "config": self.config,
        }, path)
        return path

    def load(self, path: str = None) -> "HullFoulingDetector":
        path = path or self.config.model_path
        data = joblib.load(path)
        self.gpr = data["gpr"]
        self.scaler = data["scaler"]
        self._y_scaler = data["y_scaler"]
        self.config = data["config"]
        return self
