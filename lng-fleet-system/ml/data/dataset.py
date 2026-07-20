import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from ..pipeline.config import DATA_DIR
import os


def generate_synthetic_data(n_samples: int = 5000, random_seed: int = 42) -> dict:
    rng = np.random.default_rng(random_seed)

    n_vessels = 10
    months = n_samples // n_vessels
    total = n_vessels * months

    vessels = [f"LNG-{chr(65+i)}" for i in range(n_vessels)]
    dates = pd.date_range("2020-01-01", periods=months, freq="ME")

    vessel_list = np.repeat(vessels, months)
    date_list = np.tile(dates, n_vessels)

    cii_df = pd.DataFrame({
        "vessel_id": vessel_list[:total],
        "date": date_list[:total],
        "cii_monthly": rng.uniform(2, 10, total) + rng.normal(0, 0.5, total),
        "transport_work": rng.uniform(50, 200, total),
        "vessel_age": np.tile(np.linspace(1, 20, months), n_vessels)[:total],
        "weather_deviation": rng.exponential(0.5, total),
    })
    cii_df["cii_yearly"] = (cii_df["cii_monthly"].rolling(12, min_periods=1).mean()
                            + rng.normal(0, 0.3, total))

    eng_df = pd.DataFrame({
        "vessel_id": np.repeat(vessels, months)[:total],
        "timestamp": date_list[:total],
        "shaft_power": rng.normal(25000, 3000, total),
        "sfoc": rng.normal(170, 10, total),
        "exhaust_temp": rng.normal(380, 40, total),
        "rpm": rng.normal(78, 5, total),
        "turbocharger_speed": rng.normal(18000, 1500, total),
        "scavenge_air_pressure": rng.normal(2.5, 0.4, total),
    })

    bor_df = pd.DataFrame({
        "vessel_id": np.repeat(vessels, months)[:total],
        "date": date_list[:total],
        "sea_temperature": rng.uniform(5, 32, total),
        "tank_fill_level": rng.uniform(20, 95, total),
        "tank_age_days": rng.uniform(1, 365, total),
        "vessel_speed": rng.normal(14, 2, total),
        "ambient_temperature": rng.uniform(-5, 40, total),
        "bor": rng.normal(0.10, 0.03, total),
    })

    hull_df = pd.DataFrame({
        "vessel_id": np.repeat(vessels, months)[:total],
        "date": date_list[:total],
        "speed": rng.uniform(8, 18, total),
        "power": rng.normal(20000, 4000, total),
        "delta_friction": rng.normal(2, 3, total),
    })

    sens_df = pd.DataFrame({
        "vessel_id": np.repeat(vessels, months)[:total],
        "date": date_list[:total],
        "exhaust_temp": eng_df["exhaust_temp"],
        "sfoc": eng_df["sfoc"],
        "shaft_power": eng_df["shaft_power"],
        "turbocharger_speed": eng_df["turbocharger_speed"],
        "scavenge_air_pressure": eng_df["scavenge_air_pressure"],
    })

    dfs = {
        "cii": cii_df,
        "engine": eng_df,
        "bor": bor_df,
        "hull": hull_df,
        "sensor": sens_df,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    for name, df in dfs.items():
        path = os.path.join(DATA_DIR, f"{name}.csv")
        df.to_csv(path, index=False)

    return dfs


def load_dataset(name: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"{name}.csv")
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=True)
    return None


def temporal_train_test_split(df: pd.DataFrame, test_size: float = 0.2,
                              date_col: str = "date"):
    if date_col in df.columns:
        df = df.sort_values(date_col)
    split_idx = int(len(df) * (1 - test_size))
    train = df.iloc[:split_idx].copy()
    test = df.iloc[split_idx:].copy()
    return train, test


def get_pytorch_dataloaders(X_train, y_train, X_test, y_test,
                            batch_size: int = 32):
    train_dataset = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32),
    )
    test_dataset = TensorDataset(
        torch.tensor(X_test, dtype=torch.float32),
        torch.tensor(y_test, dtype=torch.float32),
    )
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    return train_loader, test_loader
