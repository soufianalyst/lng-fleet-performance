import os
from typing import List, Dict, Any

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class ParquetWriter:
    def __init__(self, output_dir: str):
        self.output_dir = os.path.join(output_dir, "parquet")
        os.makedirs(self.output_dir, exist_ok=True)
        self.buffers = {}
        self._counts = {}

    def write_batch(self, vessel_id: str, records: List[Dict[str, Any]]):
        if not records:
            return
        if not HAS_PANDAS:
            return
        if vessel_id not in self.buffers:
            self.buffers[vessel_id] = []
        self.buffers[vessel_id].extend(records)
        self._counts[vessel_id] = self._counts.get(vessel_id, 0) + len(records)
        if len(self.buffers[vessel_id]) >= 50000:
            self._flush(vessel_id)

    def _flush(self, vessel_id: str):
        if not HAS_PANDAS or vessel_id not in self.buffers or not self.buffers[vessel_id]:
            return
        df = pd.DataFrame(self.buffers[vessel_id])
        filepath = os.path.join(self.output_dir, f"{vessel_id}_telemetry.parquet")
        if os.path.exists(filepath):
            existing = pd.read_parquet(filepath)
            df = pd.concat([existing, df], ignore_index=True)
        df.to_parquet(filepath, index=False, engine="pyarrow")
        self.buffers[vessel_id] = []

    def finalize(self):
        for vessel_id in list(self.buffers.keys()):
            self._flush(vessel_id)

    def get_counts(self) -> Dict[str, int]:
        return dict(self._counts)
