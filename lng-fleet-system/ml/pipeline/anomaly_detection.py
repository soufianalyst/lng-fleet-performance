import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os

from .config import AnomalyDetectionConfig


class LSTMEncoder(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.decoder = nn.Linear(hidden_dim, input_dim)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        return self.decoder(out)


class EngineAnomalyDetector:
    def __init__(self, config: AnomalyDetectionConfig = None):
        self.config = config or AnomalyDetectionConfig()
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(
            n_estimators=self.config.isolation_forest_n_estimators,
            contamination=self.config.isolation_forest_contamination,
            random_state=42,
        )
        self.autoencoder = None
        self.input_dim = len(self.config.feature_cols)
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "EngineAnomalyDetector":
        X = df[self.config.feature_cols].values
        X_scaled = self.scaler.fit_transform(X)

        self.isolation_forest.fit(X_scaled)

        device = torch.device("cpu")
        self.autoencoder = LSTMEncoder(
            input_dim=self.input_dim,
            hidden_dim=self.config.lstm_hidden_dim,
            num_layers=self.config.lstm_num_layers,
        ).to(device)

        seq_len = 10
        n_samples = len(X_scaled) - seq_len + 1
        if n_samples < 10:
            seq_len = max(1, len(X_scaled) // 2)
            n_samples = len(X_scaled) - seq_len + 1

        sequences = np.lib.stride_tricks.sliding_window_view(X_scaled, seq_len, axis=0)
        if sequences.ndim == 3:
            sequences = sequences.transpose(0, 2, 1)
        else:
            sequences = sequences.reshape(-1, seq_len, self.input_dim)

        if sequences.shape[0] == 0:
            sequences = X_scaled.reshape(1, 1, -1)

        tensor_data = torch.tensor(sequences, dtype=torch.float32)
        loader = DataLoader(tensor_data, batch_size=32, shuffle=True)

        optimizer = optim.Adam(self.autoencoder.parameters(), lr=self.config.lstm_lr)
        criterion = nn.MSELoss()

        self.autoencoder.train()
        for epoch in range(self.config.lstm_epochs):
            total_loss = 0
            for batch in loader:
                optimizer.zero_grad()
                recon = self.autoencoder(batch)
                loss = criterion(recon, batch[:, -1, :])
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

        self._fitted = True
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.config.feature_cols].values
        X_scaled = self.scaler.transform(X)

        if_scores = self.isolation_forest.score_samples(X_scaled)
        if_anomaly = (if_scores < np.percentile(if_scores, 5)).astype(float)

        device = torch.device("cpu")
        self.autoencoder.eval()
        seq_len = min(10, len(X_scaled))
        if seq_len < 1:
            seq_len = 1
        pad = np.tile(X_scaled[:1], (seq_len - 1, 1)) if len(X_scaled) < seq_len else X_scaled[:seq_len]
        sequences = np.lib.stride_tricks.sliding_window_view(
            np.vstack([pad, X_scaled]), seq_len, axis=0
        )
        if sequences.ndim == 3:
            sequences = sequences.transpose(0, 2, 1)
        else:
            sequences = sequences.reshape(-1, seq_len, self.input_dim)

        tensor_seq = torch.tensor(sequences, dtype=torch.float32)
        with torch.no_grad():
            recon = self.autoencoder(tensor_seq).numpy()

        ae_errors = np.mean((X_scaled[-len(recon):] - recon) ** 2, axis=1)

        if len(ae_errors) < len(X_scaled):
            ae_errors = np.pad(ae_errors, (len(X_scaled) - len(ae_errors), 0), mode="edge")
        elif len(ae_errors) > len(X_scaled):
            ae_errors = ae_errors[:len(X_scaled)]

        ae_anomaly = (ae_errors - ae_errors.min()) / max(ae_errors.ptp(), 1e-8)

        combined = 0.5 * if_anomaly + 0.5 * ae_anomaly
        combined = np.clip(combined, 0, 1)
        return combined

    def flag(self, scores: np.ndarray) -> np.ndarray:
        return (scores > self.config.anomaly_threshold).astype(int)

    def explain(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[self.config.feature_cols].values
        scores = self.predict(df)
        flags = self.flag(scores)

        X_scaled = self.scaler.transform(X)
        baseline = np.mean(X_scaled, axis=0)
        contributions = np.abs(X_scaled - baseline) * scores[:, np.newaxis]
        top_sensor_idx = np.argmax(contributions, axis=1)

        result = df.copy()
        result["anomaly_score"] = scores
        result["anomaly_flag"] = flags
        result["top_contributing_sensor"] = [self.config.feature_cols[i] for i in top_sensor_idx]
        return result

    def save(self, path: str = None) -> str:
        path = path or self.config.model_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(self.autoencoder.state_dict(), self.config.autoencoder_path)
        joblib.dump({
            "isolation_forest": self.isolation_forest,
            "scaler": self.scaler,
            "config": self.config,
            "autoencoder_path": self.config.autoencoder_path,
        }, path)
        return path

    def load(self, path: str = None) -> "EngineAnomalyDetector":
        path = path or self.config.model_path
        data = joblib.load(path)
        self.isolation_forest = data["isolation_forest"]
        self.scaler = data["scaler"]
        self.config = data["config"]
        self.autoencoder = LSTMEncoder(
            input_dim=self.input_dim,
            hidden_dim=self.config.lstm_hidden_dim,
            num_layers=self.config.lstm_num_layers,
        )
        self.autoencoder.load_state_dict(torch.load(data["autoencoder_path"], map_location="cpu"))
        self._fitted = True
        return self
