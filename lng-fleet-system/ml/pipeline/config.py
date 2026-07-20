from dataclasses import dataclass, field
from typing import Dict, Any
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")


@dataclass
class CIIForecasterConfig:
    model_path: str = field(default_factory=lambda: os.path.join(MODELS_DIR, "cii_forecaster.joblib"))
    n_estimators: int = 300
    max_depth: int = 6
    learning_rate: float = 0.08
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    early_stopping_rounds: int = 20
    quantile_alphas: tuple = (0.05, 0.5, 0.95)
    feature_cols: list = field(default_factory=lambda: [
        "cii_monthly", "transport_work", "vessel_age", "weather_deviation",
        "cii_roll12", "cii_roc", "cii_seasonal"
    ])


@dataclass
class AnomalyDetectionConfig:
    model_path: str = field(default_factory=lambda: os.path.join(MODELS_DIR, "anomaly_detection.joblib"))
    autoencoder_path: str = field(default_factory=lambda: os.path.join(MODELS_DIR, "autoencoder.pt"))
    isolation_forest_contamination: float = 0.05
    isolation_forest_n_estimators: int = 200
    anomaly_threshold: float = 0.7
    lstm_hidden_dim: int = 64
    lstm_num_layers: int = 2
    lstm_epochs: int = 50
    lstm_lr: float = 1e-3
    feature_cols: list = field(default_factory=lambda: [
        "shaft_power", "sfoc", "exhaust_temp", "rpm",
        "turbocharger_speed", "scavenge_air_pressure"
    ])


@dataclass
class BORPredictorConfig:
    model_path: str = field(default_factory=lambda: os.path.join(MODELS_DIR, "bor_predictor.joblib"))
    n_estimators: int = 300
    max_depth: int = 5
    learning_rate: float = 0.1
    subsample: float = 0.8
    poly_degree: int = 2
    feature_cols: list = field(default_factory=lambda: [
        "sea_temperature", "tank_fill_level", "tank_age_days",
        "vessel_speed", "ambient_temperature"
    ])


@dataclass
class HullFoulingConfig:
    model_path: str = field(default_factory=lambda: os.path.join(MODELS_DIR, "hull_fouling.joblib"))
    alpha: float = 1.0
    length_scale: float = 1.0
    cleaning_loss_threshold: float = 5.0
    n_restarts_optimizer: int = 10
    feature_cols: list = field(default_factory=lambda: ["speed", "power", "delta_friction"])


@dataclass
class RULEstimatorConfig:
    model_path: str = field(default_factory=lambda: os.path.join(MODELS_DIR, "rul_estimator.joblib"))
    components: list = field(default_factory=lambda: [
        "cylinder_liner", "piston_ring", "turbocharger_bearing",
        "fuel_pump", "compressor_valve"
    ])
    weibull_shapes: dict = field(default_factory=lambda: {
        "cylinder_liner": 2.5, "piston_ring": 3.0,
        "turbocharger_bearing": 2.0, "fuel_pump": 2.8,
        "compressor_valve": 1.8
    })
    weibull_scales: dict = field(default_factory=lambda: {
        "cylinder_liner": 365 * 5, "piston_ring": 365 * 3,
        "turbocharger_bearing": 365 * 4, "fuel_pump": 365 * 2,
        "compressor_valve": 365 * 1.5
    })


@dataclass
class PipelineConfig:
    cii: CIIForecasterConfig = field(default_factory=CIIForecasterConfig)
    anomaly: AnomalyDetectionConfig = field(default_factory=AnomalyDetectionConfig)
    bor: BORPredictorConfig = field(default_factory=BORPredictorConfig)
    hull: HullFoulingConfig = field(default_factory=HullFoulingConfig)
    rul: RULEstimatorConfig = field(default_factory=RULEstimatorConfig)
    random_seed: int = 42
    test_size: float = 0.2
    mlflow_experiment: str = "lng_fleet_performance"
    synthetic_samples: int = 5000
