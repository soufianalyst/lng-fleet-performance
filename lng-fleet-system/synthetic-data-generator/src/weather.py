import math
import random


class WeatherSimulator:
    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()

    def get_weather(self, lat, lon, timestamp):
        month = timestamp.month
        lat_abs = abs(lat)
        lat_sign = "north" if lat >= 0 else "south"

        sea_temp = self._sea_temperature(lat, month)
        air_temp = self._air_temperature(lat, month, lat_abs)
        wind_speed, wind_dir = self._wind(lat, lon, month, lat_abs, lat_sign)
        wave_height, wave_period = self._waves(wind_speed)
        current_speed, current_dir = self._currents(lat, lon, month, lat_abs)
        air_pressure = self._air_pressure(wind_speed, lat_abs, month)

        return {
            "wind_speed_kn": round(wind_speed, 1),
            "wind_direction_deg": round(wind_dir, 1),
            "wave_height_m": round(wave_height, 2),
            "wave_period_s": round(wave_period, 1),
            "air_temp_c": round(air_temp, 1),
            "sea_temp_c": round(sea_temp, 1),
            "current_speed_kn": round(current_speed, 2),
            "current_direction_deg": round(current_dir, 1),
            "air_pressure_hpa": round(air_pressure, 1),
        }

    def _sea_temperature(self, lat, month):
        lat_abs = abs(lat)
        if lat_abs < 10:
            base = 28.0
        elif lat_abs < 20:
            base = 25.0
        elif lat_abs < 30:
            base = 22.0
        elif lat_abs < 40:
            base = 18.0
        elif lat_abs < 50:
            base = 12.0
        elif lat_abs < 60:
            base = 7.0
        else:
            base = 3.0
        nh_summer = month in (5, 6, 7, 8, 9)
        sh_summer = month in (11, 12, 1, 2, 3)
        if (lat >= 0 and nh_summer) or (lat < 0 and sh_summer):
            base += 3.0
        else:
            base -= 2.0
        if lat_abs > 65 and month not in (6, 7, 8):
            base = max(base, -1.0)
        noise = self.rng.gauss(0, 1.5)
        return max(-2.0, min(32.0, base + noise))

    def _air_temperature(self, lat, month, lat_abs):
        if lat_abs < 10:
            base = 29.0
        elif lat_abs < 20:
            base = 26.0
        elif lat_abs < 30:
            base = 22.0
        elif lat_abs < 40:
            base = 17.0
        elif lat_abs < 50:
            base = 10.0
        elif lat_abs < 60:
            base = 4.0
        else:
            base = -5.0
        nh_summer = month in (5, 6, 7, 8, 9)
        sh_summer = month in (11, 12, 1, 2, 3)
        if (lat >= 0 and nh_summer) or (lat < 0 and sh_summer):
            base += 6.0
        else:
            base -= 4.0
        if lat_abs > 70 and month not in (6, 7, 8):
            base = max(base, -25.0)
        noise = self.rng.gauss(0, 2.0)
        return base + noise

    def _wind(self, lat, lon, month, lat_abs, lat_sign):
        lat_abs = abs(lat)
        if lat_abs < 10:
            base_wind = 8.0
            base_dir = self.rng.uniform(60, 120) if lat >= 0 else self.rng.uniform(240, 300)
        elif lat_abs < 30:
            base_wind = 12.0
            base_dir = self.rng.uniform(80, 130) if lat >= 0 else self.rng.uniform(250, 310)
        elif lat_abs < 45:
            base_wind = 16.0
            base_dir = self.rng.uniform(240, 300)
        elif lat_abs < 60:
            base_wind = 20.0
            base_dir = self.rng.uniform(240, 290)
        else:
            base_wind = 15.0
            base_dir = self.rng.uniform(200, 260)
        winter_months = [12, 1, 2, 3]
        summer_months = [5, 6, 7, 8, 9]
        if month in winter_months and lat_abs > 30:
            base_wind *= 1.5
        elif month in summer_months and lat_abs < 30:
            base_wind *= 0.7

        lon_abs = abs(lon)
        if lon_abs > 140 and lat_abs < 30:
            if month in (6, 7, 8, 9, 10):
                base_wind += self.rng.uniform(10, 30)
                base_dir = self.rng.uniform(200, 280)
        if lat_abs < 20 and lon > 50 and lon < 80:
            if month in (6, 7, 8, 9):
                base_wind += self.rng.uniform(8, 20)
                base_dir = self.rng.uniform(220, 280)

        noise = self.rng.gauss(0, 0.3 * base_wind)
        wind_speed = max(1.0, base_wind + noise)
        dir_noise = self.rng.gauss(0, 20)
        wind_dir = (base_dir + dir_noise) % 360
        return wind_speed, wind_dir

    def _waves(self, wind_speed):
        h = 0.03 * wind_speed ** 1.5
        h_noise = self.rng.gauss(0, 0.15 * h)
        wave_height = max(0.2, min(14.0, h + h_noise))
        if wave_height < 1.0:
            period = 3.0 + wave_height * 2.0
        else:
            period = 4.0 + 1.5 * math.sqrt(wave_height)
        period_noise = self.rng.gauss(0, 0.5)
        wave_period = max(2.0, period + period_noise)
        return wave_height, wave_period

    def _currents(self, lat, lon, month, lat_abs):
        lat_abs_f = abs(lat)
        if lat_abs_f < 10:
            speed = 1.5
            direction = 270 if lat >= 0 else 90
        elif lat_abs_f < 20:
            speed = 1.0
            direction = 270 if lat >= 0 else 90
        elif lat_abs_f < 40:
            direction = 90
            speed = 0.5
        elif lat_abs_f < 55:
            if lon > -30 and lon < 10:
                direction = 0
                speed = 1.0
            else:
                direction = 90
                speed = 0.5
        else:
            if lon > -20 and lon < 30:
                direction = 0
                speed = 1.2
            else:
                direction = 90
                speed = 0.3

        if lat_abs_f < 15 and lon > 50 and lon < 80:
            if month in (6, 7, 8, 9):
                direction = 90
                speed = 2.0
            else:
                direction = 270
                speed = 1.0

        noise = self.rng.gauss(0, 0.2)
        speed = max(0.1, speed + noise)
        dir_noise = self.rng.gauss(0, 15)
        return speed, (direction + dir_noise) % 360

    def _air_pressure(self, wind_speed, lat_abs, month):
        if wind_speed < 10:
            base = 1020
        elif wind_speed < 20:
            base = 1015
        elif wind_speed < 30:
            base = 1008
        else:
            base = 998
        if lat_abs < 10:
            base -= 5
        if month in (6, 7, 8) and lat_abs > 30:
            base += 3
        noise = self.rng.gauss(0, 3)
        return base + noise

    def beaufort_from_wind(self, wind_speed_kn):
        if wind_speed_kn < 1:
            return 0
        if wind_speed_kn < 4:
            return 1
        if wind_speed_kn < 7:
            return 2
        if wind_speed_kn < 11:
            return 3
        if wind_speed_kn < 16:
            return 4
        if wind_speed_kn < 22:
            return 5
        if wind_speed_kn < 28:
            return 6
        if wind_speed_kn < 34:
            return 7
        if wind_speed_kn < 41:
            return 8
        if wind_speed_kn < 48:
            return 9
        if wind_speed_kn < 56:
            return 10
        if wind_speed_kn < 64:
            return 11
        return 12

    def speed_loss_factor(self, wind_speed_kn, wave_height_m, heading_rel_wind_deg=135):
        bf = self.beaufort_from_wind(wind_speed_kn)
        if bf <= 3:
            return 1.0
        if bf == 4:
            factor = 0.97
        elif bf == 5:
            factor = 0.93
        elif bf == 6:
            factor = 0.86
        elif bf == 7:
            factor = 0.78
        elif bf == 8:
            factor = 0.70
        elif bf == 9:
            factor = 0.60
        elif bf == 10:
            factor = 0.50
        else:
            factor = 0.40

        waves_factor = max(0.0, 1.0 - 0.08 * wave_height_m)
        combined = factor * (0.7 + 0.3 * waves_factor)

        return max(0.35, min(1.0, combined))
