import csv
import os
from typing import List, Dict, Any


class CSVWriter:
    def __init__(self, output_dir: str, chunk_size: int = 10000):
        self.output_dir = os.path.join(output_dir, "csv")
        os.makedirs(self.output_dir, exist_ok=True)
        self.chunk_size = chunk_size
        self.files = {}
        self._headers = {}
        self._writer_obj = {}
        self.counters = {}

    def write_batch(self, vessel_id: str, records: List[Dict[str, Any]]):
        if not records:
            return
        if vessel_id not in self.files:
            filepath = os.path.join(self.output_dir, f"{vessel_id}_telemetry.csv")
            self.files[vessel_id] = open(filepath, "w", newline="")
            self.counters[vessel_id] = 0
            self._headers[vessel_id] = []
            self._writer_obj[vessel_id] = None
        all_keys = self._headers[vessel_id]
        for r in records:
            for k in r:
                if k not in all_keys:
                    all_keys.append(k)
        if self._writer_obj.get(vessel_id) is None:
            self._writer_obj[vessel_id] = csv.DictWriter(
                self.files[vessel_id], fieldnames=all_keys, extrasaction='ignore'
            )
            self._writer_obj[vessel_id].writeheader()
        for record in records:
            padded = {k: record.get(k, "") for k in self._headers[vessel_id]}
            self._writer_obj[vessel_id].writerow(padded)
            self.counters[vessel_id] += 1
        self.files[vessel_id].flush()

    def finalize(self):
        for f in self.files.values():
            f.close()
        self.files.clear()
        self._writer_obj.clear()

    def get_counts(self) -> Dict[str, int]:
        return dict(self.counters)
