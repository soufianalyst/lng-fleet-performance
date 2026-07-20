from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Vessel:
    imo_number: str
    vessel_name: str
    flag_state: str
    vessel_type: str = "LNG Carrier"
    classification_society: str = ""
    gross_tonnage: float = 0
    deadweight_tonnage: float = 0
    cargo_capacity_m3: float = 0
    number_of_tanks: int = 4
    propulsion_type: str = "ME-GI"
    engine_manufacturer: str = ""
    engine_model: str = ""
    engine_mcr_kw: float = 0
    service_speed_kn: float = 0
    design_speed_kn: float = 0
    eexi_value: float = 0
    eedi_value: float = 0
    cii_reference_value: float = 0
    year_of_build: int = 2020
    ice_class: str = ""
    scrubber_equipped: bool = False
    reliquefaction_plant: bool = True
    shaft_power_meter: bool = True
    vessel_id: Optional[int] = None

    def save(self, db):
        if self.vessel_id:
            db.execute(
                """UPDATE vessels SET vessel_name=?, vessel_type=?, flag_state=?,
                   classification_society=?, gross_tonnage=?, deadweight_tonnage=?,
                   cargo_capacity_m3=?, number_of_tanks=?, propulsion_type=?,
                   engine_manufacturer=?, engine_model=?, engine_mcr_kw=?,
                   service_speed_kn=?, design_speed_kn=?, eexi_value=?, eedi_value=?,
                   cii_reference_value=?, year_of_build=?, ice_class=?,
                   scrubber_equipped=?, reliquefaction_plant=?, shaft_power_meter=?,
                   updated_at=datetime('now')
                   WHERE vessel_id=?""",
                (self.vessel_name, self.vessel_type, self.flag_state,
                 self.classification_society, self.gross_tonnage, self.deadweight_tonnage,
                 self.cargo_capacity_m3, self.number_of_tanks, self.propulsion_type,
                 self.engine_manufacturer, self.engine_model, self.engine_mcr_kw,
                 self.service_speed_kn, self.design_speed_kn, self.eexi_value, self.eedi_value,
                 self.cii_reference_value, self.year_of_build, self.ice_class,
                 int(self.scrubber_equipped), int(self.reliquefaction_plant),
                 int(self.shaft_power_meter), self.vessel_id),
            )
        else:
            existing = db.fetchone(
                "SELECT vessel_id FROM vessels WHERE imo_number=?", (self.imo_number,))
            if existing:
                self.vessel_id = existing["vessel_id"]
                db.execute(
                    """UPDATE vessels SET vessel_name=?, vessel_type=?, flag_state=?,
                       classification_society=?, gross_tonnage=?, deadweight_tonnage=?,
                       cargo_capacity_m3=?, number_of_tanks=?, propulsion_type=?,
                       engine_manufacturer=?, engine_model=?, engine_mcr_kw=?,
                       service_speed_kn=?, design_speed_kn=?, eexi_value=?, eedi_value=?,
                       cii_reference_value=?, year_of_build=?, ice_class=?,
                       scrubber_equipped=?, reliquefaction_plant=?, shaft_power_meter=?,
                       updated_at=datetime('now')
                       WHERE vessel_id=?""",
                    (self.vessel_name, self.vessel_type, self.flag_state,
                     self.classification_society, self.gross_tonnage, self.deadweight_tonnage,
                     self.cargo_capacity_m3, self.number_of_tanks, self.propulsion_type,
                     self.engine_manufacturer, self.engine_model, self.engine_mcr_kw,
                     self.service_speed_kn, self.design_speed_kn, self.eexi_value, self.eedi_value,
                     self.cii_reference_value, self.year_of_build, self.ice_class,
                     int(self.scrubber_equipped), int(self.reliquefaction_plant),
                     int(self.shaft_power_meter), self.vessel_id),
                )
            else:
                cur = db.execute(
                    """INSERT INTO vessels (imo_number, vessel_name, vessel_type, flag_state,
                       classification_society, gross_tonnage, deadweight_tonnage,
                       cargo_capacity_m3, number_of_tanks, propulsion_type,
                       engine_manufacturer, engine_model, engine_mcr_kw,
                       service_speed_kn, design_speed_kn, eexi_value, eedi_value,
                       cii_reference_value, year_of_build, ice_class,
                       scrubber_equipped, reliquefaction_plant, shaft_power_meter)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (self.imo_number, self.vessel_name, self.vessel_type, self.flag_state,
                     self.classification_society, self.gross_tonnage, self.deadweight_tonnage,
                     self.cargo_capacity_m3, self.number_of_tanks, self.propulsion_type,
                     self.engine_manufacturer, self.engine_model, self.engine_mcr_kw,
                     self.service_speed_kn, self.design_speed_kn, self.eexi_value, self.eedi_value,
                     self.cii_reference_value, self.year_of_build, self.ice_class,
                     int(self.scrubber_equipped), int(self.reliquefaction_plant),
                     int(self.shaft_power_meter)),
                )
                self.vessel_id = cur.lastrowid
        return self.vessel_id

    @classmethod
    def from_row(cls, row) -> "Vessel":
        return cls(
            vessel_id=row["vessel_id"],
            imo_number=row["imo_number"],
            vessel_name=row["vessel_name"],
            vessel_type=row["vessel_type"],
            flag_state=row["flag_state"],
            classification_society=row["classification_society"] or "",
            gross_tonnage=row["gross_tonnage"] or 0,
            deadweight_tonnage=row["deadweight_tonnage"] or 0,
            cargo_capacity_m3=row["cargo_capacity_m3"] or 0,
            number_of_tanks=row["number_of_tanks"] or 4,
            propulsion_type=row["propulsion_type"] or "ME-GI",
            engine_manufacturer=row["engine_manufacturer"] or "",
            engine_model=row["engine_model"] or "",
            engine_mcr_kw=row["engine_mcr_kw"] or 0,
            service_speed_kn=row["service_speed_kn"] or 0,
            design_speed_kn=row["design_speed_kn"] or 0,
            eexi_value=row["eexi_value"] or 0,
            eedi_value=row["eedi_value"] or 0,
            cii_reference_value=row["cii_reference_value"] or 0,
            year_of_build=row["year_of_build"] or 2020,
            ice_class=row["ice_class"] or "",
            scrubber_equipped=bool(row["scrubber_equipped"]),
            reliquefaction_plant=bool(row["reliquefaction_plant"]),
            shaft_power_meter=bool(row["shaft_power_meter"]),
        )

    @classmethod
    def get_by_id(cls, db, vessel_id: int) -> Optional["Vessel"]:
        row = db.fetchone("SELECT * FROM vessels WHERE vessel_id=?", (vessel_id,))
        return cls.from_row(row) if row else None

    @classmethod
    def get_by_imo(cls, db, imo: str) -> Optional["Vessel"]:
        row = db.fetchone("SELECT * FROM vessels WHERE imo_number=?", (imo,))
        return cls.from_row(row) if row else None

    @classmethod
    def list_all(cls, db) -> list["Vessel"]:
        rows = db.fetchall("SELECT * FROM vessels ORDER BY vessel_name")
        return [cls.from_row(r) for r in rows]

    def __repr__(self):
        return f"<Vessel {self.vessel_name} ({self.imo_number})>"


@dataclass
class VesselTank:
    vessel_id: int
    tank_name: str
    capacity_m3: float
    tank_id: Optional[int] = None
    tank_position: str = ""
    design_pressure_bar: float = 0
    design_temperature_k: float = 111.0
    insulation_type: str = "membrane"
    sensor_count: int = 12

    def save(self, db):
        cur = db.execute(
            """INSERT OR REPLACE INTO vessel_tanks
               (vessel_id, tank_name, tank_position, capacity_m3,
                design_pressure_bar, design_temperature_k, insulation_type, sensor_count)
               VALUES (?,?,?,?,?,?,?,?)""",
            (self.vessel_id, self.tank_name, self.tank_position, self.capacity_m3,
             self.design_pressure_bar, self.design_temperature_k,
             self.insulation_type, self.sensor_count),
        )
        if not self.tank_id:
            self.tank_id = cur.lastrowid
        return self.tank_id

    @classmethod
    def get_by_vessel(cls, db, vessel_id: int) -> list["VesselTank"]:
        rows = db.fetchall(
            "SELECT * FROM vessel_tanks WHERE vessel_id=? ORDER BY tank_name",
            (vessel_id,),
        )
        tanks = []
        for r in rows:
            t = cls(
                tank_id=r["tank_id"], vessel_id=r["vessel_id"],
                tank_name=r["tank_name"], tank_position=r["tank_position"] or "",
                capacity_m3=r["capacity_m3"],
                design_pressure_bar=r["design_pressure_bar"] or 0,
                design_temperature_k=r["design_temperature_k"] or 111,
                insulation_type=r["insulation_type"] or "membrane",
                sensor_count=r["sensor_count"] or 12,
            )
            tanks.append(t)
        return tanks
