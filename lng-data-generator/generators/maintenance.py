import numpy as np
from simulator import VesselState


class MaintenanceGenerator:
    def __init__(self, config):
        self.config = config
        self.work_orders = []
        self.spare_parts = {}
        self.last_preventive = 0.0
        self.preventive_interval = 2000.0

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        if state.engine_running:
            state.running_hours_engine += dt_hours
        if state.running_hours_engine - self.last_preventive > self.preventive_interval:
            if np.random.random() < 0.3:
                self.work_orders.append({
                    "type": "preventive",
                    "component": np.random.choice(["turbocharger", "cylinder_head", "fuel_injector", "valve"]),
                    "status": "scheduled",
                    "due_hours": state.running_hours_engine + 100,
                })
            self.last_preventive = state.running_hours_engine
        if np.random.random() < 0.0001 * dt_hours:
            component = np.random.choice(["bearing", "pump_seal", "compressor_valve", "heat_exchanger"])
            self.work_orders.append({
                "type": "corrective",
                "component": component,
                "status": "open",
                "severity": np.random.choice(["low", "medium", "high"]),
            })
        for wo in self.work_orders:
            if wo["status"] == "scheduled" and state.running_hours_engine >= wo.get("due_hours", 99999):
                wo["status"] = "in_progress"
            elif wo["status"] == "in_progress" and np.random.random() < 0.01 * dt_hours:
                wo["status"] = "completed"
        self.work_orders = [wo for wo in self.work_orders if wo["status"] != "completed"]
