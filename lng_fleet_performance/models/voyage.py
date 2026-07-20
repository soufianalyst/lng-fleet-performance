from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Voyage:
    vessel_id: int
    voyage_number: str
    load_port: str
    discharge_port: str
    voyage_id: Optional[int] = None
    charterer: str = ""
    cargo_quantity_mt: float = 0
    cargo_type: str = "LNG"
    planned_departure: str = ""
    actual_departure: str = ""
    planned_arrival: str = ""
    actual_arrival: str = ""
    status: str = "planned"
    route_type: str = "weather_optimized"
    total_distance_nm: float = 0
    total_fuel_hfo_mt: float = 0
    total_fuel_vlsfo_mt: float = 0
    total_fuel_ulsfo_mt: float = 0
    total_fuel_mgo_mt: float = 0
    total_fuel_lng_mt: float = 0
    total_bog_mt: float = 0
    co2_total_mt: float = 0
    cii_voyage_value: float = 0
    eca_time_hours: float = 0
    eu_ets_applicable: bool = False

    def save(self, db):
        if self.voyage_id:
            db.execute(
                """UPDATE voyages SET charterer=?, load_port=?, discharge_port=?,
                   cargo_quantity_mt=?, cargo_type=?, planned_departure=?, actual_departure=?,
                   planned_arrival=?, actual_arrival=?, status=?, route_type=?,
                   total_distance_nm=?, total_fuel_hfo_mt=?, total_fuel_vlsfo_mt=?,
                   total_fuel_ulsfo_mt=?, total_fuel_mgo_mt=?, total_fuel_lng_mt=?,
                   total_bog_mt=?, co2_total_mt=?, cii_voyage_value=?,
                   eca_time_hours=?, eu_ets_applicable=?, updated_at=datetime('now')
                   WHERE voyage_id=?""",
                (self.charterer, self.load_port, self.discharge_port,
                 self.cargo_quantity_mt, self.cargo_type, self.planned_departure,
                 self.actual_departure, self.planned_arrival, self.actual_arrival,
                 self.status, self.route_type, self.total_distance_nm,
                 self.total_fuel_hfo_mt, self.total_fuel_vlsfo_mt,
                 self.total_fuel_ulsfo_mt, self.total_fuel_mgo_mt,
                 self.total_fuel_lng_mt, self.total_bog_mt, self.co2_total_mt,
                 self.cii_voyage_value, self.eca_time_hours,
                 int(self.eu_ets_applicable), self.voyage_id),
            )
        else:
            cur = db.execute(
                """INSERT INTO voyages (vessel_id, voyage_number, charterer,
                   load_port, discharge_port, cargo_quantity_mt, cargo_type,
                   planned_departure, actual_departure, planned_arrival, actual_arrival,
                   status, route_type, total_distance_nm, total_fuel_hfo_mt,
                   total_fuel_vlsfo_mt, total_fuel_ulsfo_mt, total_fuel_mgo_mt,
                   total_fuel_lng_mt, total_bog_mt, co2_total_mt, cii_voyage_value,
                   eca_time_hours, eu_ets_applicable)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (self.vessel_id, self.voyage_number, self.charterer,
                 self.load_port, self.discharge_port, self.cargo_quantity_mt,
                 self.cargo_type, self.planned_departure, self.actual_departure,
                 self.planned_arrival, self.actual_arrival, self.status,
                 self.route_type, self.total_distance_nm, self.total_fuel_hfo_mt,
                 self.total_fuel_vlsfo_mt, self.total_fuel_ulsfo_mt,
                 self.total_fuel_mgo_mt, self.total_fuel_lng_mt, self.total_bog_mt,
                 self.co2_total_mt, self.cii_voyage_value, self.eca_time_hours,
                 int(self.eu_ets_applicable)),
            )
            self.voyage_id = cur.lastrowid
        return self.voyage_id

    @classmethod
    def from_row(cls, row) -> "Voyage":
        return cls(
            voyage_id=row["voyage_id"], vessel_id=row["vessel_id"],
            voyage_number=row["voyage_number"], charterer=row["charterer"] or "",
            load_port=row["load_port"], discharge_port=row["discharge_port"],
            cargo_quantity_mt=row["cargo_quantity_mt"] or 0,
            cargo_type=row["cargo_type"] or "LNG",
            planned_departure=row["planned_departure"] or "",
            actual_departure=row["actual_departure"] or "",
            planned_arrival=row["planned_arrival"] or "",
            actual_arrival=row["actual_arrival"] or "",
            status=row["status"] or "planned",
            route_type=row["route_type"] or "weather_optimized",
            total_distance_nm=row["total_distance_nm"] or 0,
            total_fuel_hfo_mt=row["total_fuel_hfo_mt"] or 0,
            total_fuel_vlsfo_mt=row["total_fuel_vlsfo_mt"] or 0,
            total_fuel_ulsfo_mt=row["total_fuel_ulsfo_mt"] or 0,
            total_fuel_mgo_mt=row["total_fuel_mgo_mt"] or 0,
            total_fuel_lng_mt=row["total_fuel_lng_mt"] or 0,
            total_bog_mt=row["total_bog_mt"] or 0,
            co2_total_mt=row["co2_total_mt"] or 0,
            cii_voyage_value=row["cii_voyage_value"] or 0,
            eca_time_hours=row["eca_time_hours"] or 0,
            eu_ets_applicable=bool(row["eu_ets_applicable"]),
        )

    @classmethod
    def get_by_id(cls, db, voyage_id: int) -> Optional["Voyage"]:
        row = db.fetchone("SELECT * FROM voyages WHERE voyage_id=?", (voyage_id,))
        return cls.from_row(row) if row else None

    @classmethod
    def list_by_vessel(cls, db, vessel_id: int) -> list["Voyage"]:
        rows = db.fetchall(
            "SELECT * FROM voyages WHERE vessel_id=? ORDER BY actual_departure DESC",
            (vessel_id,),
        )
        return [cls.from_row(r) for r in rows]

    @classmethod
    def list_active(cls, db) -> list["Voyage"]:
        rows = db.fetchall(
            "SELECT * FROM voyages WHERE status='in_progress' ORDER BY actual_departure DESC"
        )
        return [cls.from_row(r) for r in rows]

    def __repr__(self):
        return f"<Voyage {self.voyage_number}: {self.load_port} → {self.discharge_port}>"


@dataclass
class VoyageWaypoint:
    voyage_id: int
    sequence_num: int
    latitude: float
    longitude: float
    waypoint_id: Optional[int] = None
    waypoint_name: str = ""
    eta_utc: str = ""
    ata_utc: str = ""
    speed_planned_kn: float = 0
    speed_actual_kn: float = 0
    course_deg: float = 0
    in_eca: bool = False
    eca_zone_name: str = ""
    water_depth_m: float = 0
    weather_hs_m: float = 0
    weather_tp_s: float = 0
    weather_direction_deg: float = 0
    wind_speed_kn: float = 0
    wind_direction_deg: float = 0
    current_speed_kn: float = 0
    current_direction_deg: float = 0
    fuel_consumption_mt: float = 0
    shaft_power_kw: float = 0

    def save(self, db):
        cur = db.execute(
            """INSERT INTO voyage_waypoints
               (voyage_id, sequence_num, latitude, longitude, waypoint_name,
                eta_utc, ata_utc, speed_planned_kn, speed_actual_kn, course_deg,
                in_eca, eca_zone_name, water_depth_m, weather_hs_m, weather_tp_s,
                weather_direction_deg, wind_speed_kn, wind_direction_deg,
                current_speed_kn, current_direction_deg, fuel_consumption_mt, shaft_power_kw)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.voyage_id, self.sequence_num, self.latitude, self.longitude,
             self.waypoint_name, self.eta_utc, self.ata_utc,
             self.speed_planned_kn, self.speed_actual_kn, self.course_deg,
             int(self.in_eca), self.eca_zone_name, self.water_depth_m,
             self.weather_hs_m, self.weather_tp_s, self.weather_direction_deg,
             self.wind_speed_kn, self.wind_direction_deg,
             self.current_speed_kn, self.current_direction_deg,
             self.fuel_consumption_mt, self.shaft_power_kw),
        )
        self.waypoint_id = cur.lastrowid
        return self.waypoint_id

    @classmethod
    def list_by_voyage(cls, db, voyage_id: int) -> list["VoyageWaypoint"]:
        rows = db.fetchall(
            "SELECT * FROM voyage_waypoints WHERE voyage_id=? ORDER BY sequence_num",
            (voyage_id,),
        )
        waypoints = []
        for r in rows:
            waypoints.append(cls(
                waypoint_id=r["waypoint_id"], voyage_id=r["voyage_id"],
                sequence_num=r["sequence_num"], latitude=r["latitude"],
                longitude=r["longitude"], waypoint_name=r["waypoint_name"] or "",
                eta_utc=r["eta_utc"] or "", ata_utc=r["ata_utc"] or "",
                speed_planned_kn=r["speed_planned_kn"] or 0,
                speed_actual_kn=r["speed_actual_kn"] or 0,
                course_deg=r["course_deg"] or 0,
                in_eca=bool(r["in_eca"]),
                eca_zone_name=r["eca_zone_name"] or "",
                water_depth_m=r["water_depth_m"] or 0,
                weather_hs_m=r["weather_hs_m"] or 0,
                weather_tp_s=r["weather_tp_s"] or 0,
                weather_direction_deg=r["weather_direction_deg"] or 0,
                wind_speed_kn=r["wind_speed_kn"] or 0,
                wind_direction_deg=r["wind_direction_deg"] or 0,
                current_speed_kn=r["current_speed_kn"] or 0,
                current_direction_deg=r["current_direction_deg"] or 0,
                fuel_consumption_mt=r["fuel_consumption_mt"] or 0,
                shaft_power_kw=r["shaft_power_kw"] or 0,
            ))
        return waypoints
