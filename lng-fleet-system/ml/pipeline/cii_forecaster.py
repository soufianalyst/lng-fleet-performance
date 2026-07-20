import numpy as np
import pandas as pd
import joblib
from xgboost import XGBRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from .config import CIIForecasterConfig, MODELS_DIR
import os


CII_RATING_BOUNDARIES = {
    "A": (0, 3.5),
    "B": (3.5, 5.0),
    "C": (5.0, 7.0),
    "D": (7.0, 9.5),
    "E": (9.5, float("inf")),
}


def _cii_rating(cii_value: float) -> str:
    for rating, (lo, hi) in CII_RATING_BOUNDARIES.items():
        if lo <= cii_value < hi:
            return rating
    return "E"


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["cii_roll12"] = result["cii_monthly"].rolling(window=12, min_periods=1).mean()
    result["cii_roc"] = result["cii_monthly"].diff().fillna(0)
    periods = 12
    result["cii_seasonal"] = (
        result["cii_monthly"].rolling(window=periods, min_periods=1).mean()
        - result["cii_monthly"].rolling(window=periods * 3, min_periods=1).mean().fillna(method="bfill")
    )
    result.fillna(0, inplace=True)
    return result


class CIIConformalPredictor:
    def __init__(self, config: CIIForecasterConfig = None):
        self.config = config or CIIForecasterConfig()
        self.scaler = StandardScaler()
        self.model = None
        self._quantile_models = {}

    def fit(self, df: pd.DataFrame, target_col: str = "cii_yearly") -> "CIIConformalPredictor":
        df = _engineer_features(df)
        X = df[self.config.feature_cols].values
        y = df[target_col].values

        X_scaled = self.scaler.fit_transform(X)

        self.model = XGBRegressor(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            learning_rate=self.config.learning_rate,
            subsample=self.config.subsample,
            colsample_bytree=self.config.colsample_bytree,
            random_state=42,
            verbosity=0,
        )
        self.model.fit(X_scaled, y)

        for alpha in self.config.quantile_alphas:
            q_model = XGBRegressor(
                n_estimators=self.config.n_estimators // 2,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                subsample=self.config.subsample,
                colsample_bytree=self.config.colsample_bytree,
                random_state=42,
                verbosity=0,
            )
            q_model.set_params(**{"objective": "reg:quantileerror", "quantile_alpha": alpha})
            q_model.fit(X_scaled, y)
            self._quantile_models[alpha] = q_model

        return self

    def predict(self, vessel_features: pd.DataFrame) -> dict:
        df = _engineer_features(vessel_features)
        X = df[self.config.feature_cols].values
        X_scaled = self.scaler.transform(X)

        y_pred = self.model.predict(X_scaled)
        rating = _cii_rating(float(y_pred[0]))

        quantiles = {}
        for alpha in self.config.quantile_alphas:
            q_pred = self._quantile_models[alpha].predict(X_scaled)
            quantiles[f"q_{int(alpha*100)}"] = float(q_pred[0])

        return {
            "predicted_cii": float(y_pred[0]),
            "rating": rating,
            "confidence_interval": {
                "lower": quantiles.get("q_5", y_pred[0] * 0.9),
                "upper": quantiles.get("q_95", y_pred[0] * 1.1),
            },
        }

    def save(self, path: str = None) -> str:
        path = path or self.config.model_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"model": self.model, "scaler": self.scaler,
                      "quantile_models": self._quantile_models, "config": self.config}, path)
        return path

    def load(self, path: str = None) -> "CIIConformalPredictor":
        path = path or self.config.model_path
        data = joblib.load(path)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self._quantile_models = data["quantile_models"]
        self.config = data["config"]
        return self
