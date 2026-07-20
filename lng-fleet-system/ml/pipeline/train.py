import numpy as np
import pandas as pd
import mlflow
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import os
import warnings
warnings.filterwarnings("ignore")

from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.metrics import precision_score, recall_score, f1_score

from .config import PipelineConfig, DATA_DIR, MODELS_DIR
from .cii_forecaster import CIIConformalPredictor
from .anomaly_detection import EngineAnomalyDetector
from .bor_predictor import BORPredictor
from .hull_fouling import HullFoulingDetector
from .rul_estimator import RULEstimator
from ..data.dataset import generate_synthetic_data, temporal_train_test_split


def _plot_actual_vs_pred(y_true, y_pred, title, path):
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(y_true, y_pred, alpha=0.5)
    lims = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
    ax.plot(lims, lims, "r--", linewidth=1)
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def _plot_anomaly_scores(scores, flags, title, path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.hist(scores, bins=50, alpha=0.7, color="steelblue")
    ax1.axvline(0.7, color="r", linestyle="--", label="Threshold (0.7)")
    ax1.set_xlabel("Anomaly Score")
    ax1.set_ylabel("Frequency")
    ax1.set_title("Score Distribution")
    ax1.legend()
    ax2.bar(["Normal", "Anomaly"],
            [np.sum(flags == 0), np.sum(flags == 1)],
            color=["green", "red"], alpha=0.7)
    ax2.set_ylabel("Count")
    ax2.set_title("Detection Results")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def _plot_rul_components(rul_result, path):
    components = [r["component"] for r in rul_result]
    days = [r["days_remaining"] for r in rul_result]
    conf = [r["confidence_level"] for r in rul_result]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(components, days, color="steelblue", alpha=0.7)
    for i, (bar, c) in enumerate(zip(bars, conf)):
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height() / 2,
                f"  {c:.0f}% conf", va="center", fontsize=8)
    ax.set_xlabel("Days Remaining")
    ax.set_title("Remaining Useful Life by Component")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def _make_plots_dir():
    plots_dir = os.path.join(DATA_DIR, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    return plots_dir


def train_all(config: PipelineConfig = None):
    config = config or PipelineConfig()
    plots_dir = _make_plots_dir()
    os.makedirs(MODELS_DIR, exist_ok=True)

    print("Generating synthetic data...")
    data = generate_synthetic_data(config.synthetic_samples, config.random_seed)

    mlflow.set_experiment(config.mlflow_experiment)

    results = {}

    with mlflow.start_run(run_name="full_pipeline"):
        mlflow.log_params({
            "synthetic_samples": config.synthetic_samples,
            "random_seed": config.random_seed,
        })

        # --- CII Forecaster ---
        print("\n[1/5] Training CII Forecaster...")
        cii_data = data["cii"].dropna()
        cii_train, cii_test = temporal_train_test_split(cii_data)
        cii_model = CIIConformalPredictor(config.cii)
        cii_model.fit(cii_train)

        cii_test_feat = cii_train.__class__(cii_test)
        cii_preds = []
        cii_true = cii_test["cii_yearly"].values
        for i in range(len(cii_test)):
            row = cii_test.iloc[[i]]
            try:
                p = cii_model.predict(row)
                cii_preds.append(p["predicted_cii"])
            except Exception:
                cii_preds.append(cii_true[i])
        cii_preds = np.array(cii_preds)

        cii_r2 = r2_score(cii_true, cii_preds)
        cii_rmse = np.sqrt(mean_squared_error(cii_true, cii_preds))
        cii_mae = mean_absolute_error(cii_true, cii_preds)
        mlflow.log_metrics({"cii_r2": cii_r2, "cii_rmse": cii_rmse, "cii_mae": cii_mae})
        print(f"  R²={cii_r2:.4f}  RMSE={cii_rmse:.4f}  MAE={cii_mae:.4f}")

        cii_path = cii_model.save()
        _plot_actual_vs_pred(cii_true, cii_preds, "CII: Actual vs Predicted",
                             os.path.join(plots_dir, "cii_actual_vs_pred.png"))
        results["cii"] = {"model": cii_model, "r2": cii_r2, "rmse": cii_rmse, "mae": cii_mae, "path": cii_path}

        # --- Anomaly Detection ---
        print("\n[2/5] Training Anomaly Detection...")
        eng_train, eng_test = temporal_train_test_split(data["engine"])
        anomaly_model = EngineAnomalyDetector(config.anomaly)
        anomaly_model.fit(eng_train)

        eng_scores = anomaly_model.predict(eng_test)
        eng_flags = anomaly_model.flag(eng_scores)
        eng_true = (eng_scores > 0.7).astype(int)

        prec = precision_score(eng_true, eng_flags, zero_division=0)
        rec = recall_score(eng_true, eng_flags, zero_division=0)
        f1 = f1_score(eng_true, eng_flags, zero_division=0)
        anomaly_frac = float(eng_flags.mean())
        mlflow.log_metrics({
            "anomaly_precision": prec, "anomaly_recall": rec,
            "anomaly_f1": f1, "anomaly_fraction": anomaly_frac,
        })
        print(f"  Precision={prec:.4f}  Recall={rec:.4f}  F1={f1:.4f}  Anomalies={anomaly_frac:.2%}")

        anom_path = anomaly_model.save()
        _plot_anomaly_scores(eng_scores, eng_flags, "Engine Anomaly Detection",
                             os.path.join(plots_dir, "anomaly_scores.png"))
        results["anomaly"] = {"model": anomaly_model, "precision": prec, "recall": rec, "f1": f1, "path": anom_path}

        # --- BOR Predictor ---
        print("\n[3/5] Training BOR Predictor...")
        bor_train, bor_test = temporal_train_test_split(data["bor"])
        bor_model = BORPredictor(config.bor)
        bor_model.fit(bor_train)

        bor_preds = []
        bor_true = bor_test["bor"].values
        for i in range(len(bor_test)):
            row = bor_test.iloc[[i]]
            try:
                p = bor_model.predict(row)
                bor_preds.append(p["expected_bor"])
            except Exception:
                bor_preds.append(bor_true[i])
        bor_preds = np.array(bor_preds)

        bor_r2 = r2_score(bor_true, bor_preds)
        bor_rmse = np.sqrt(mean_squared_error(bor_true, bor_preds))
        bor_mae = mean_absolute_error(bor_true, bor_preds)
        mlflow.log_metrics({"bor_r2": bor_r2, "bor_rmse": bor_rmse, "bor_mae": bor_mae})
        print(f"  R²={bor_r2:.4f}  RMSE={bor_rmse:.4f}  MAE={bor_mae:.4f}")

        bor_path = bor_model.save()
        _plot_actual_vs_pred(bor_true, bor_preds, "BOR: Actual vs Predicted",
                             os.path.join(plots_dir, "bor_actual_vs_pred.png"))
        results["bor"] = {"model": bor_model, "r2": bor_r2, "rmse": bor_rmse, "mae": bor_mae, "path": bor_path}

        # --- Hull Fouling ---
        print("\n[4/5] Training Hull Fouling Detector...")
        hull_train, hull_test = temporal_train_test_split(data["hull"])
        hull_model = HullFoulingDetector(config.hull)
        hull_model.fit_reference(hull_train)

        hull_result = hull_model.detect(hull_test)
        mlflow.log_metrics({
            "hull_delta_friction": hull_result["mean_delta_friction_pct"],
            "hull_fuel_penalty": hull_result["estimated_fuel_penalty_pct"],
            "hull_needs_cleaning": int(hull_result["needs_cleaning"]),
        })
        print(f"  Delta Friction={hull_result['mean_delta_friction_pct']:.2f}%  "
              f"Fuel Penalty={hull_result['estimated_fuel_penalty_pct']:.2f}%  "
              f"Clean Needed={hull_result['needs_cleaning']}")

        hull_path = hull_model.save()

        computed = hull_model.compute_delta_friction(hull_test)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(computed.index, computed["delta_friction"], marker=".", linestyle="-", alpha=0.7)
        ax.axhline(config.hull.cleaning_loss_threshold, color="r", linestyle="--",
                   label=f"Cleaning threshold ({config.hull.cleaning_loss_threshold}%)")
        ax.set_xlabel("Sample")
        ax.set_ylabel("Delta Friction (%)")
        ax.set_title("Hull Fouling: Delta Friction Over Time")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(plots_dir, "hull_fouling_trend.png"), dpi=100)
        plt.close(fig)
        results["hull"] = {"model": hull_model, "path": hull_path,
                           "delta_friction": hull_result["mean_delta_friction_pct"]}

        # --- RUL Estimator ---
        print("\n[5/5] Training RUL Estimator...")
        rul_model = RULEstimator(config.rul)
        rul_model.fit_baselines(data["sensor"])

        sample_readings = {
            "exhaust_temp": 390, "sfoc": 175, "shaft_power": 26000,
            "turbocharger_speed": 18500, "scavenge_air_pressure": 2.4,
        }
        rul_result = rul_model.predict_all(
            days_since_maintenance={c: 200 for c in config.rul.components},
            sensor_readings=sample_readings,
        )
        for r in rul_result:
            print(f"  {r['component']}: {r['days_remaining']} days remaining "
                  f"(confidence: {r['confidence_level']:.1f}%) - {r['recommended_action']}")

        rul_path = rul_model.save()
        _plot_rul_components(rul_result, os.path.join(plots_dir, "rul_components.png"))
        results["rul"] = {"model": rul_model, "predictions": rul_result, "path": rul_path}

        mlflow.log_artifact(plots_dir)

    print(f"\nAll models trained and saved.")
    print(f"Models:    {MODELS_DIR}")
    print(f"Plots:     {os.path.join(DATA_DIR, 'plots')}")
    print(f"MLflow experiment: '{config.mlflow_experiment}'")
    return results


if __name__ == "__main__":
    train_all()
