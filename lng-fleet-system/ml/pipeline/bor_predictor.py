import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
import os

from .config import BORPredictorConfig


class BORPredictor:
    def __init__(self, config: BORPredictorConfig = None):
        self.config = config or BORPredictorConfig()
        self.pipeline = Pipeline([
            ("poly", PolynomialFeatures(degree=self.config.poly_degree, include_bias=False)),
            ("scaler", StandardScaler()),
            ("model", GradientBoostingRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                subsample=self.config.subsample,
                random_state=42,
            )),
        ])
        self._residuals = None
        self._residual_std = None

    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        pairs = [("sea_temperature", "tank_fill_level"),
                 ("vessel_speed", "sea_temperature"),
                 ("ambient_temperature", "tank_age_days")]
        for a, b in pairs:
            if a in result.columns and b in result.columns:
                result[f"{a}_x_{b}"] = result[a] * result[b]
        return result

    def fit(self, df: pd.DataFrame, target_col: str = "bor") -> "BORPredictor":
        df = self._add_interaction_features(df)
        feature_cols = self.config.feature_cols + [c for c in df.columns if "_x_" in c]
        X = df[feature_cols].values
        y = df[target_col].values

        self.pipeline.fit(X, y)

        y_pred = self.pipeline.predict(X)
        self._residuals = y - y_pred
        self._residual_std = np.std(self._residuals)
        return self

    def predict(self, voyage_conditions: pd.DataFrame) -> dict:
        df = self._add_interaction_features(voyage_conditions)
        feature_cols = self.config.feature_cols + [c for c in df.columns if "_x_" in c]
        X = df[feature_cols].values

        y_pred = self.pipeline.predict(X)
        pi = 1.96 * self._residual_std

        return {
            "expected_bor": float(y_pred[0]),
            "prediction_interval": {
                "lower": float(y_pred[0] - pi),
                "upper": float(y_pred[0] + pi),
            },
        }

    def save(self, path: str = None) -> str:
        path = path or self.config.model_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({
            "pipeline": self.pipeline,
            "residual_std": self._residual_std,
            "config": self.config,
        }, path)
        return path

    def load(self, path: str = None) -> "BORPredictor":
        path = path or self.config.model_path
        data = joblib.load(path)
        self.pipeline = data["pipeline"]
        self._residual_std = data["residual_std"]
        self.config = data["config"]
        return self
