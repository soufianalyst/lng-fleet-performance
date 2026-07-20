import numpy as np
import pandas as pd
import json
import os
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify

from .config import PipelineConfig, MODELS_DIR
from .cii_forecaster import CIIConformalPredictor
from .anomaly_detection import EngineAnomalyDetector
from .bor_predictor import BORPredictor
from .hull_fouling import HullFoulingDetector
from .rul_estimator import RULEstimator


class FleetInferenceServer:
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.models = {}
        self._loaded = False

    def load_all(self) -> "FleetInferenceServer":
        self.models["cii"] = CIIConformalPredictor(self.config.cii).load()
        self.models["anomaly"] = EngineAnomalyDetector(self.config.anomaly).load()
        self.models["bor"] = BORPredictor(self.config.bor).load()
        self.models["hull"] = HullFoulingDetector(self.config.hull).load()
        self.models["rul"] = RULEstimator(self.config.rul).load()
        self._loaded = True
        return self

    def predict_cii(self, features: pd.DataFrame) -> dict:
        return self.models["cii"].predict(features)

    def predict_anomaly(self, features: pd.DataFrame) -> dict:
        scores = self.models["anomaly"].predict(features)
        flags = self.models["anomaly"].flag(scores)
        explanation = self.models["anomaly"].explain(features)
        return {
            "scores": scores.tolist(),
            "flags": flags.tolist(),
            "top_contributors": explanation["top_contributing_sensor"].tolist(),
        }

    def predict_bor(self, features: pd.DataFrame) -> dict:
        return self.models["bor"].predict(features)

    def predict_hull(self, features: pd.DataFrame) -> dict:
        return self.models["hull"].detect(features)

    def predict_rul(self, days_since_maintenance: dict = None,
                    sensor_readings: dict = None) -> list:
        return self.models["rul"].predict_all(days_since_maintenance, sensor_readings)

    def predict_all(self, vessel_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        results = {}
        if "cii" in vessel_data:
            results["cii"] = self.predict_cii(vessel_data["cii"])
        if "engine" in vessel_data:
            results["anomaly"] = self.predict_anomaly(vessel_data["engine"])
        if "bor" in vessel_data:
            results["bor"] = self.predict_bor(vessel_data["bor"])
        if "hull" in vessel_data:
            results["hull"] = self.predict_hull(vessel_data["hull"])
        if "rul" in vessel_data:
            ds = vessel_data["rul"].get("days_since_maintenance", {})
            sr = vessel_data["rul"].get("sensor_readings", {})
            results["rul"] = self.predict_rul(ds, sr)
        return results

    def predict_batch(self, fleet_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        if not isinstance(next(iter(fleet_data.values())), list):
            return [self.predict_all(fleet_data)]
        n = len(fleet_data[list(fleet_data.keys())[0]])
        results = []
        for i in range(n):
            vessel_slice = {k: v[i] if isinstance(v, list) else v.iloc[[i]]
                            for k, v in fleet_data.items()}
            results.append(self.predict_all(vessel_slice))
        return results


def create_flask_app(server: FleetInferenceServer = None) -> Flask:
    app = Flask(__name__)
    if server is None:
        server = FleetInferenceServer()
        server.load_all()

    @app.route("/predict", methods=["POST"])
    def predict():
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload"}), 400

        results = {}
        if "cii" in data:
            df = pd.DataFrame([data["cii"]])
            results["cii"] = server.predict_cii(df)
        if "engine" in data:
            df = pd.DataFrame([data["engine"]])
            results["anomaly"] = server.predict_anomaly(df)
        if "bor" in data:
            df = pd.DataFrame([data["bor"]])
            results["bor"] = server.predict_bor(df)
        if "hull" in data:
            df = pd.DataFrame([data["hull"]])
            results["hull"] = server.predict_hull(df)
        if "rul" in data:
            rul_data = data["rul"]
            results["rul"] = server.predict_rul(
                rul_data.get("days_since_maintenance", {}),
                rul_data.get("sensor_readings", {}),
            )
        return jsonify(results)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "models_loaded": server._loaded})

    return app


if __name__ == "__main__":
    server = FleetInferenceServer()
    server.load_all()
    app = create_flask_app(server)
    print("Fleet Inference API running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
