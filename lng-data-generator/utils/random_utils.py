import numpy as np


class AR1Process:
    def __init__(self, mean, std, autocorrelation, dt, min_val=None, max_val=None):
        self.mean = mean
        self.std = std
        self.ac = autocorrelation
        self.dt = dt
        self.min_val = min_val
        self.max_val = max_val
        self.state = mean
        self.noise_std = std * math.sqrt(1 - autocorrelation ** 2) if autocorrelation < 1.0 else 0.01 * std

    def step(self):
        innovation = np.random.normal(0, self.noise_std)
        self.state = self.ac * self.state + (1 - self.ac) * self.mean + innovation
        if self.min_val is not None:
            self.state = max(self.min_val, self.state)
        if self.max_val is not None:
            self.state = min(self.max_val, self.state)
        return self.state

    def reset(self, value=None):
        self.state = value if value is not None else self.mean


class StormEvent:
    def __init__(self):
        self.active = False
        self.intensity = 0.0
        self.time_in_storm = 0.0
        self.total_duration = 0.0
        self.ramp_up = 0.0
        self.ramp_down = 0.0
        self.peak_time = 0.0

    def update(self, dt_hours):
        if not self.active:
            return 0.0
        self.time_in_storm += dt_hours
        if self.time_in_storm < self.ramp_up:
            self.intensity = self.time_in_storm / max(self.ramp_up, 0.1)
        elif self.time_in_storm < self.peak_time:
            self.intensity = 1.0
        elif self.time_in_storm < self.total_duration:
            remaining = self.total_duration - self.time_in_storm
            self.intensity = remaining / max(self.total_duration - self.peak_time, 0.1)
        else:
            self.active = False
            self.intensity = 0.0
        return self.intensity

    def trigger(self, duration_hours=8, ramp_up_hours=3, ramp_down_hours=5):
        self.active = True
        self.intensity = 0.0
        self.time_in_storm = 0.0
        self.total_duration = duration_hours
        self.ramp_up = ramp_up_hours
        self.ramp_down = ramp_down_hours
        self.peak_time = duration_hours - ramp_down_hours


import math
