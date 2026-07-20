#!/usr/bin/env python3
"""Generate 50 vessel configs and 20+ routes for large-scale telemetry generation."""
import yaml
import random
import math

random.seed(42)

CITIES = [
    ("Ras Laffan", 25.93, 51.56), ("Hamad", 25.25, 51.55), ("Das Island", 25.17, 52.87),
    ("Sabine Pass", 29.73, -93.86), ("Cameron LNG", 29.68, -93.22), ("Freeport", 28.95, -95.26),
    ("Cove Point", 38.40, -76.38), ("Elba Island", 32.02, -80.84),
    ("Snovit", 70.79, 20.01), ("Hammerfest", 70.70, 23.80), ("Melkoya", 70.53, 25.57),
    ("Darwin", -12.46, 130.85), ("Gladstone", -23.85, 151.27), ("Ichthys", -12.28, 123.50),
    ("Sines", 37.95, -8.87), ("Barcelona", 41.39, 2.17), ("Zeebrugge", 51.33, 3.18),
    ("Rotterdam", 51.90, 4.00), ("Gate Terminal", 51.90, 4.02),
    ("Algeciras", 36.13, -5.45), ("Huelva", 37.13, -6.95),
    ("Naoshima", 34.46, 133.99), ("Chiba", 35.61, 140.11), ("Incheon", 37.46, 126.62),
    ("Qingdao", 36.07, 120.38), ("Fujian", 25.50, 119.58), ("Dapeng", 22.47, 114.50),
    ("Kaohsiung", 22.62, 120.30), ("Yungning", 24.85, 121.82),
    ("Tangguh", -2.83, 128.27), ("Bontang", 0.13, 117.53), ("MLNG", 4.39, 113.98),
    ("Bonny Island", 4.43, 7.17), ("Nigeria LNG", 4.45, 7.15),
    ("Taman", 45.10, 36.72), ("Sakhalin", 46.95, 143.23), ("Vladivostok", 43.12, 131.90),
    ("Sohar", 24.50, 56.73), ("Salalah", 16.93, 54.09),
    ("Puerto Rico", 18.47, -66.10), ("Sabadia", 10.00, -62.00),
    ("Ennore", 13.15, 80.32), ("Dahej", 21.70, 72.55),
    ("Gate LNG", 51.90, 4.02), ("Montoir", 47.26, -1.92),
    ("Dunkirk", 51.04, 2.38), ("Alexandria", 31.20, 29.90),
    ("Ain Sukhna", 29.60, 32.34), ("Idku", 31.55, 30.05),
]

FLAGS = ["SG", "PA", "NO", "HK", "MT", "LR", "BS", "MH", "KY", "JM", "GR", "CY", "IT", "GB", "DE", "NL"]
# Realistic twin-screw DF LNGC MCRs (2×X72DF or 2×5G70ME-GI ≈ 24-34 MW)
# 10 options preserved (same random-draw sequence as original config)
MCR_OPTIONS = [22000, 24000, 25000, 26000, 27000, 28000, 29000, 30000, 31000, 32000]
SPEED_OPTIONS = [18.5, 19.0, 19.5, 19.8, 20.0]
CAPACITY_OPTIONS = [(145000, 36), (150000, 37), (155000, 38), (160000, 39),
                     (165000, 40), (170000, 41), (174000, 43), (177000, 44),
                     (180000, 45), (185000, 46)]

LNG_NAMES = [
    "Atlantic Eagle", "Pacific Titan", "Nordic Voyager", "Silk Route", "Desert Star",
    "Arctic Pioneer", "Oriental Spirit", "Mediterranean Sun", "Gulf Explorer", "Polar Bear",
    "Crystal Wave", "Golden Horizon", "Silver Arrow", "Iron Mountain", "Blue Ocean",
    "Red Phoenix", "Green Valley", "White Cloud", "Black Pearl", "Coral Sea",
    "Jade Dragon", "Ruby Moon", "Sapphire Coast", "Emerald Bay", "Diamond Head",
    "Amber Dawn", "Opal Star", "Onyx Storm", "Topaz Wind", "Garnet Tide",
    "Pearl Harbor", "Ivory Coast", "Copper Canyon", "Bronze Age", "Platinum Sky",
    "Neptune's Grace", "Poseidon's Fury", "Trident Force", "Compass Rose", "Star Navigator",
    "Sea Venture", "Wind Chaser", "Tide Runner", "Storm Rider", "Sun Chase",
    "Moon Voyager", "Dawn Walker", "Dusk Rider", "Midnight Sun", "Northern Lights",
]

def gen_vessel(idx, name):
    propulsion = random.choice(["ME-GI", "X-DF"])
    cap_m3, beam = random.choice(CAPACITY_OPTIONS)
    mcr = random.choice(MCR_OPTIONS)
    sfoc = random.uniform(155.0, 167.0) if propulsion == "X-DF" else random.uniform(160.0, 170.0)
    speed = random.choice(SPEED_OPTIONS)
    loa = random.randint(285, 305)
    draft = round(random.uniform(11.2, 11.9), 1)
    gt = random.randint(105000, 125000)
    dwt = gt - random.randint(28000, 35000)
    flag = random.choice(FLAGS)
    lng_cap = random.randint(3800, 5500)
    lng_init = int(lng_cap * random.uniform(0.78, 0.92))
    mgo_cap = random.randint(1800, 2800)
    mgo_init = int(mgo_cap * random.uniform(0.75, 0.90))

    tank_cap = cap_m3 // 4
    cargo_tanks = []
    for tname in ["Port Forward", "Port Aft", "Starboard Forward", "Starboard Aft"]:
        variation = random.randint(-500, 500)
        cargo_tanks.append({"name": tname, "capacity_m3": tank_cap + variation})

    return {
        "id": f"LNG-{idx+1:03d}",
        "name": f"LNG {name}",
        "imo": 9801000 + idx + 1,
        "flag": flag,
        "type": propulsion,
        "propulsion": "dual_fuel_megi" if propulsion == "ME-GI" else "dual_fuel_xdf",
        "gt": gt,
        "dwt": dwt,
        "cargo_capacity_m3": cap_m3,
        "loa_m": loa,
        "beam_m": beam,
        "draft_design_m": draft,
        "engine_mcr_kw": mcr,
        "engine_sfoc_g_kwh": round(sfoc, 1),
        "service_speed_kn": speed,
        "fuel_tanks": {
            "lng_capacity_m3": lng_cap,
            "lng_level_init_m3": lng_init,
            "mgo_capacity_mt": mgo_cap,
            "mgo_level_init_mt": mgo_init,
            "vlsfo_capacity_mt": 0,
            "vlsfo_level_init_mt": 0,
            "pilot_fuel_capacity_mt": 100,
            "pilot_fuel_level_init_mt": random.randint(65, 90),
        },
        "cargo_tanks": cargo_tanks,
        "aux_generators": 3,
        "aux_mcr_kw": random.randint(4800, 6000),
        "scrubber": False,
        "egr": False,
    }


# ─── Sea-lane waypoints for realistic routes ───
# All coordinates are open water / recognized shipping lanes
W = {
    "hormuz": (26.5, 56.8), "gulf_oman": (24.5, 59.5), "arabian_sea": (15.0, 65.0),
    "bab_el_mandeb": (12.6, 43.3), "red_sea_mid": (20.0, 38.5),
    "suez_south": (29.5, 32.5), "suez_north": (31.5, 32.3),
    "east_med": (33.5, 30.0), "malta_channel": (36.5, 15.0), "west_med": (37.5, 4.0),
    "gibraltar": (35.9, -5.7), "finisterre": (43.5, -9.5),
    "channel_west": (49.5, -3.0), "dover": (51.0, 1.8), "rotterdam_app": (52.2, 3.5),
    "zeebrugge": (51.35, 3.2), "dunkirk": (51.05, 2.4),
    "sri_lanka_s": (5.5, 81.0), "malacca": (5.5, 96.0), "singapore": (1.2, 104.0),
    "scs_mid": (12.0, 112.0), "taiwan_strait": (24.5, 119.5), "east_china_sea": (28.0, 125.0),
    "korea_strait": (34.0, 129.5), "yellow_sea": (35.5, 123.0), "incheon_app": (37.3, 126.3),
    "japan_south": (31.0, 132.0), "chiba_app": (35.0, 140.5),
    "philippine_sea": (20.0, 135.0), "philippine_sea_s": (10.0, 130.0),
    "makassar": (0.0, 118.5), "banda_sea": (-5.0, 128.0), "timor_sea": (-11.0, 129.0),
    "coral_sea": (-15.0, 152.0), "coral_sea_n": (-10.0, 148.0),
    "gulf_guinea": (0.0, 0.0), "atlantic_w": (30.0, -60.0), "florida_strait": (24.5, -81.5),
    "caribbean": (15.0, -72.0), "gulf_mexico": (25.0, -90.0),
    "la_perouse": (45.5, 142.0), "japan_sea": (40.0, 135.0),
    "norwegian_sea": (65.0, 10.0), "north_sea": (57.0, 4.0), "biscay": (46.0, -6.0),
}


def _wps(*points):
    return [{"lat": round(p[0], 2), "lon": round(p[1], 2)} for p in points]


def gen_routes(n=25):
    """Hand-crafted LNG trade routes via real sea lanes (no overland tracks)."""
    R = [
        ("Ras Laffan", "Gate Terminal", [
            (25.93, 51.56), W["hormuz"], W["gulf_oman"], W["arabian_sea"],
            W["bab_el_mandeb"], W["red_sea_mid"], W["suez_south"], W["suez_north"],
            W["east_med"], W["malta_channel"], W["west_med"], W["gibraltar"],
            W["finisterre"], W["channel_west"], W["dover"], W["rotterdam_app"], (51.90, 4.02)]),
        ("Ras Laffan", "Chiba", [
            (25.93, 51.56), W["hormuz"], W["gulf_oman"], (12.0, 62.0),
            W["sri_lanka_s"], W["malacca"], W["singapore"], W["scs_mid"],
            W["taiwan_strait"], W["east_china_sea"], W["japan_south"], W["chiba_app"], (35.61, 140.11)]),
        ("Ras Laffan", "Dahej", [
            (25.93, 51.56), W["hormuz"], W["gulf_oman"], (20.0, 65.0), (21.70, 72.55)]),
        ("Ras Laffan", "Incheon", [
            (25.93, 51.56), W["hormuz"], W["gulf_oman"], (12.0, 62.0),
            W["sri_lanka_s"], W["malacca"], W["singapore"], W["scs_mid"],
            W["taiwan_strait"], W["east_china_sea"], W["yellow_sea"], W["incheon_app"], (37.46, 126.62)]),
        ("Sabine Pass", "Zeebrugge", [
            (29.73, -93.86), W["gulf_mexico"], W["florida_strait"], (30.0, -75.0),
            (35.0, -60.0), (40.0, -45.0), (45.0, -30.0), (49.0, -12.0),
            W["channel_west"], W["dover"], W["zeebrugge"]]),
        ("Cameron LNG", "Barcelona", [
            (29.68, -93.22), W["gulf_mexico"], W["florida_strait"], (30.0, -75.0),
            (35.0, -60.0), (40.0, -40.0), (43.0, -20.0), W["gibraltar"],
            W["west_med"], (41.39, 2.17)]),
        ("Freeport", "Ain Sukhna", [
            (28.95, -95.26), W["gulf_mexico"], W["florida_strait"], (30.0, -75.0),
            (35.0, -60.0), (40.0, -40.0), (43.0, -20.0), W["gibraltar"],
            W["west_med"], W["malta_channel"], W["east_med"], W["suez_north"],
            W["suez_south"], (29.60, 32.34)]),
        ("Cove Point", "Sines", [
            (38.40, -76.38), (37.0, -70.0), (37.0, -50.0), (37.0, -30.0),
            (38.0, -12.0), (37.95, -8.87)]),
        ("Hammerfest", "Gate Terminal", [
            (70.70, 23.80), (69.0, 17.0), W["norwegian_sea"], (60.0, 4.5),
            W["north_sea"], (53.5, 3.8), W["rotterdam_app"], (51.90, 4.02)]),
        ("Hammerfest", "Sines", [
            (70.70, 23.80), (68.0, 14.0), W["norwegian_sea"], (59.0, 2.0),
            (53.0, -3.0), W["biscay"], (43.0, -9.5), (39.0, -10.0), (37.95, -8.87)]),
        ("Darwin", "Chiba", [
            (-12.46, 130.85), W["timor_sea"], (-8.0, 128.0), (-2.0, 132.0),
            (5.0, 135.0), (12.0, 135.0), W["philippine_sea"], (27.0, 130.0),
            W["japan_south"], W["chiba_app"], (35.61, 140.11)]),
        ("Gladstone", "Dapeng", [
            (-23.85, 151.27), W["coral_sea"], W["coral_sea_n"], (-5.0, 140.0),
            (2.0, 136.0), (10.0, 130.0), (16.0, 126.0), (20.0, 121.0), (22.47, 114.50)]),
        ("Ichthys", "Incheon", [
            (-12.28, 123.50), (-8.0, 126.0), (-2.0, 130.0), (5.0, 133.0),
            (12.0, 132.0), (20.0, 128.0), W["east_china_sea"], W["yellow_sea"],
            W["incheon_app"], (37.46, 126.62)]),
        ("Bontang", "Chiba", [
            (0.13, 117.53), W["makassar"], (5.0, 122.0), W["philippine_sea_s"],
            (15.0, 132.0), (22.0, 130.0), W["japan_south"], W["chiba_app"], (35.61, 140.11)]),
        ("Tangguh", "Qingdao", [
            (-2.83, 128.27), (2.0, 130.0), W["philippine_sea_s"], (15.0, 128.0),
            (20.0, 124.0), W["taiwan_strait"], W["east_china_sea"], (32.0, 123.5),
            (35.5, 121.5), (36.07, 120.38)]),
        ("MLNG", "Chiba", [
            (4.39, 113.98), (8.0, 112.0), (15.0, 115.0), (20.0, 120.5),
            (25.0, 125.0), (30.0, 130.0), W["japan_south"], W["chiba_app"], (35.61, 140.11)]),
        ("MLNG", "Kaohsiung", [
            (4.39, 113.98), (10.0, 113.0), (16.0, 116.0), (20.0, 119.0), (22.62, 120.30)]),
        ("Bonny Island", "Sines", [
            (4.43, 7.17), W["gulf_guinea"], (5.0, -5.0), (12.0, -12.0),
            (20.0, -17.0), (28.0, -16.0), (35.0, -10.0), (37.95, -8.87)]),
        ("Bonny Island", "Dunkirk", [
            (4.43, 7.17), W["gulf_guinea"], (5.0, -8.0), (12.0, -15.0),
            (22.0, -18.0), (32.0, -15.0), (40.0, -12.0), W["biscay"],
            W["channel_west"], W["dover"], W["dunkirk"]]),
        ("Sakhalin", "Chiba", [
            (46.95, 143.23), W["la_perouse"], (42.0, 141.5), (38.0, 141.0),
            W["chiba_app"], (35.61, 140.11)]),
        ("Sakhalin", "Qingdao", [
            (46.95, 143.23), W["la_perouse"], (42.0, 138.0), W["japan_sea"],
            W["korea_strait"], W["yellow_sea"], (36.07, 120.38)]),
        ("Das Island", "Fujian", [
            (25.17, 52.87), W["hormuz"], W["gulf_oman"], (12.0, 62.0),
            W["sri_lanka_s"], W["malacca"], W["singapore"], W["scs_mid"],
            W["taiwan_strait"], (25.50, 119.58)]),
        ("Sohar", "Ennore", [
            (24.50, 56.73), W["gulf_oman"], (20.0, 62.0), (15.0, 70.0),
            (12.5, 76.0), (13.15, 80.32)]),
        ("Gladstone", "Incheon", [
            (-23.85, 151.27), W["coral_sea"], W["coral_sea_n"], (-5.0, 142.0),
            (4.0, 138.0), (12.0, 132.0), (20.0, 130.0), W["east_china_sea"],
            W["yellow_sea"], W["incheon_app"], (37.46, 126.62)]),
        ("Sabine Pass", "Puerto Rico", [
            (29.73, -93.86), W["gulf_mexico"], (22.0, -87.0), (18.5, -80.0),
            W["caribbean"], (18.47, -66.10)]),
        ("Tangguh", "Chiba", [
            (-2.83, 128.27), (2.0, 131.0), W["philippine_sea_s"], (12.0, 132.0),
            W["philippine_sea"], (27.0, 130.0), W["japan_south"], W["chiba_app"], (35.61, 140.11)]),
    ]
    routes = []
    for i, (load_name, disp_name, waypoints) in enumerate(R[:n]):
        load = next(c for c in CITIES if c[0] == load_name)
        disp = next(c for c in CITIES if c[0] == disp_name)
        dist = 0.0
        for j in range(len(waypoints) - 1):
            dist += math.sqrt(
                ((waypoints[j+1][0] - waypoints[j][0]) * 60) ** 2
                + ((waypoints[j+1][1] - waypoints[j][1]) * 60
                   * math.cos(math.radians(waypoints[j][0]))) ** 2
            )
        eca = []
        if disp_name in ("Gate Terminal", "Zeebrugge", "Dunkirk", "Barcelona", "Sines"):
            eca.append("NORTH_SEA_ECA")
        if load_name in ("Sabine Pass", "Cameron LNG", "Freeport", "Cove Point"):
            eca.append("NORTH_AMERICAN_ECA")
        if disp_name == "Puerto Rico":
            eca.append("US_CARIBBEAN_ECA")
        routes.append({
            "id": f"ROUTE-{i+1:03d}",
            "name": f"{load_name} to {disp_name}",
            "load_port": {"name": load_name, "lat": load[1], "lon": load[2]},
            "discharge_port": {"name": disp_name, "lat": disp[1], "lon": disp[2]},
            "distance_nm": int(dist),
            "waypoints": _wps(*waypoints),
            "eca_zones": eca,
        })
    return routes


vessels = [gen_vessel(i, LNG_NAMES[i]) for i in range(50)]
routes = gen_routes(25)

with open("config/vessels.yaml", "w") as f:
    yaml.dump({"vessels": vessels}, f, default_flow_style=False, sort_keys=False, width=120)

with open("config/routes.yaml", "w") as f:
    yaml.dump({"routes": routes}, f, default_flow_style=False, sort_keys=False, width=120)

print(f"Generated {len(vessels)} vessels, {len(routes)} routes")
print(f"Vessel types: {sum(1 for v in vessels if v['type']=='ME-GI')} ME-GI, {sum(1 for v in vessels if v['type']=='X-DF')} X-DF")
print(f"Capacity range: {min(v['cargo_capacity_m3'] for v in vessels):,} - {max(v['cargo_capacity_m3'] for v in vessels):,} m3")
