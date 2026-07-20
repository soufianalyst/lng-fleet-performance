import math

PORT_COORDS = {
    "Ras Laffan": (25.9333, 51.5167),
    "Sabine Pass": (29.7333, -93.8667),
    "Gladstone": (-23.8431, 151.2542),
    "Bonny": (4.4333, 7.1667),
    "Snohvit": (70.6167, 22.0667),
    "Yamal": (71.0833, 72.6667),
    "Das Island": (25.1500, 52.8667),
    "Qalhat": (22.6833, 59.3667),
    "Kribi": (2.9333, 9.9167),
    "Tangguh": (-2.4167, 134.5000),
    "Bontang": (0.1333, 117.5000),
    "Darwin": (-12.4667, 130.8333),
    "Zeebrugge": (51.3333, 3.2000),
    "Isle of Grain": (51.4500, 0.7167),
    "Montoir": (47.2833, -2.1500),
    "Bilbao": (43.3333, -3.0167),
    "Barcelona": (41.3333, 2.1667),
    "Fos-sur-Mer": (43.4000, 4.8667),
    "Gate terminal": (51.9500, 4.1667),
    "Swinoujscie": (53.9167, 14.2500),
    "Krk": (45.0333, 14.5833),
    "Everett": (42.4083, -71.0500),
    "Cove Point": (38.3833, -76.3833),
    "Elba Island": (32.0833, -81.1000),
    "Freeport": (28.9500, -95.3000),
    "Corpus Christi": (27.8000, -97.4000),
    "Altamira": (22.4000, -97.8833),
    "Manzanillo": (19.0500, -104.3167),
    "Bahia Blanca": (-38.7167, -62.2667),
    "Pecem": (-3.5333, -38.8000),
    "Dahej": (21.7000, 72.5833),
    "Hazira": (21.1500, 72.6500),
    "Dabhol": (17.6000, 73.0333),
    "Kochi": (10.0000, 76.2833),
    "Shanghai": (31.2333, 121.4833),
    "Tianjin": (38.9833, 117.7833),
    "Ningbo": (29.8667, 121.5500),
    "Shenzhen": (22.5333, 114.1167),
    "Tokyo Bay": (35.4000, 139.7833),
    "Futtsu": (35.3167, 139.8333),
    "Sodegaura": (35.4333, 139.9833),
    "Incheon": (37.4500, 126.6000),
    "Pyeongtaek": (36.9833, 127.0833),
}


def deg2rad(deg):
    return deg * math.pi / 180.0


def rad2deg(rad):
    return rad * 180.0 / math.pi


def haversine_nm(lat1, lon1, lat2, lon2):
    lat1_r, lon1_r = deg2rad(lat1), deg2rad(lon1)
    lat2_r, lon2_r = deg2rad(lat2), deg2rad(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(min(a, 1.0)))
    return c * 3440.065


def great_circle_interpolate(lat1, lon1, lat2, lon2, num_points):
    lat1_r, lon1_r = deg2rad(lat1), deg2rad(lon1)
    lat2_r, lon2_r = deg2rad(lat2), deg2rad(lon2)
    dlon = lon2_r - lon1_r
    dlat = lat2_r - lat1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    d = 2 * math.asin(math.sqrt(min(a, 1.0)))
    if d < 1e-10:
        return [(lat1, lon1)] * num_points
    points = []
    for i in range(num_points):
        f = i / max(num_points - 1, 1)
        A = math.sin((1 - f) * d) / math.sin(d)
        B = math.sin(f * d) / math.sin(d)
        x = A * math.cos(lat1_r) * math.cos(lon1_r) + B * math.cos(lat2_r) * math.cos(lon2_r)
        y = A * math.cos(lat1_r) * math.sin(lon1_r) + B * math.cos(lat2_r) * math.sin(lon2_r)
        z = A * math.sin(lat1_r) + B * math.sin(lat2_r)
        lat_r = math.atan2(z, math.sqrt(x * x + y * y))
        lon_r = math.atan2(y, x)
        points.append((rad2deg(lat_r), rad2deg(lon_r)))
    return points


def course_between(lat1, lon1, lat2, lon2):
    lat1_r, lon1_r = deg2rad(lat1), deg2rad(lon1)
    lat2_r, lon2_r = deg2rad(lat2), deg2rad(lon2)
    dlon = lon2_r - lon1_r
    y = math.sin(dlon) * math.cos(lat2_r)
    x = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


ROUTE_WAYPOINTS = {
    "mideast_europe": [
        (25.9333, 51.5167),
        (24.0, 57.0), (22.0, 62.0), (15.0, 55.0), (12.0, 44.0),
        (15.0, 42.0), (20.0, 39.0), (25.0, 36.0), (28.0, 34.0),
        (31.0, 33.0), (33.5, 28.0), (35.0, 22.0), (36.0, 15.0),
        (36.0, 8.0), (36.0, 0.0), (36.0, -5.0),
        (38.0, -8.0), (42.0, -10.0), (46.0, -10.0), (49.0, -6.0),
        (51.5, 2.0),
    ],
    "mideast_asia": [
        (25.9333, 51.5167),
        (24.0, 57.0), (22.0, 62.0), (18.0, 68.0), (12.0, 75.0),
        (8.0, 78.0), (5.0, 95.0), (3.5, 99.0), (2.0, 102.0),
        (1.2, 104.0), (3.0, 105.0), (8.0, 108.0), (15.0, 111.0),
        (20.0, 115.0), (25.0, 119.0), (30.0, 122.0), (33.0, 127.0),
        (35.0, 135.0), (35.4, 139.8),
    ],
    "us_europe": [
        (29.7333, -93.8667),
        (27.0, -92.0), (26.0, -90.0), (25.5, -85.0), (25.5, -80.0),
        (27.0, -78.0), (30.0, -75.0), (35.0, -70.0), (40.0, -65.0),
        (45.0, -55.0), (48.0, -45.0), (50.0, -35.0), (51.0, -25.0),
        (51.0, -15.0), (50.0, -10.0),
        (49.5, -6.0), (51.0, -2.0), (51.5, 2.0),
    ],
    "us_asia_panama": [
        (29.7333, -93.8667),
        (27.0, -92.0), (25.0, -90.0), (22.0, -87.0), (20.0, -85.0),
        (15.0, -83.0), (10.0, -81.0), (9.0, -80.0),
        (8.0, -79.5), (7.0, -79.0), (5.0, -80.0), (3.0, -82.0),
        (2.0, -85.0), (1.0, -90.0), (0.5, -95.0), (2.0, -100.0),
        (5.0, -105.0), (8.0, -110.0), (12.0, -115.0), (15.0, -120.0),
        (18.0, -125.0), (20.0, -130.0), (22.0, -140.0), (25.0, -150.0),
        (28.0, -160.0), (30.0, -165.0), (32.0, -170.0),
        (34.0, 175.0), (35.0, 165.0), (35.5, 155.0),
        (35.4, 145.0), (35.4, 139.8),
    ],
    "australia_japan": [
        (-23.8431, 151.2542),
        (-22.0, 153.0), (-18.0, 155.0), (-14.0, 153.0),
        (-10.0, 150.0), (-8.0, 147.0), (-5.0, 144.0),
        (-3.0, 142.0), (0.0, 140.0), (3.0, 138.0),
        (5.0, 135.0), (7.0, 132.0), (8.0, 128.0),
        (9.0, 125.0), (12.0, 122.0), (15.0, 120.0),
        (18.0, 121.0), (20.0, 123.0), (22.0, 124.0),
        (25.0, 126.0), (28.0, 130.0), (30.0, 133.0),
        (32.0, 136.0), (34.0, 138.0), (35.4, 139.8),
    ],
    "westafrica_europe": [
        (4.4333, 7.1667),
        (5.0, 6.0), (8.0, 2.0), (10.0, -2.0),
        (12.0, -5.0), (15.0, -8.0), (18.0, -12.0),
        (20.0, -15.0), (22.0, -17.0), (25.0, -18.0),
        (28.0, -17.0), (30.0, -16.0), (32.0, -15.0),
        (34.0, -14.0), (36.0, -12.0), (38.0, -10.0),
        (40.0, -9.0), (43.0, -9.0), (45.0, -8.0),
        (47.0, -6.0), (49.0, -4.0), (51.0, -1.0),
        (51.5, 2.0),
    ],
    "westafrica_americas": [
        (4.4333, 7.1667),
        (4.0, 5.0), (3.0, 0.0), (2.0, -5.0),
        (1.0, -10.0), (0.0, -15.0), (-1.0, -20.0),
        (-2.0, -25.0), (-3.0, -30.0), (-3.5, -35.0),
        (-3.5, -38.0), (0.0, -40.0), (5.0, -42.0),
        (10.0, -44.0), (15.0, -46.0), (18.0, -48.0),
        (20.0, -55.0), (22.0, -70.0), (22.5, -80.0),
        (22.4, -97.88),
    ],
    "norway_europe": [
        (70.6167, 22.0667),
        (68.0, 20.0), (66.0, 18.0), (64.0, 15.0),
        (62.0, 12.0), (60.0, 8.0), (58.0, 5.0),
        (56.0, 3.0), (54.0, 3.0), (52.5, 3.5),
        (51.95, 4.17),
    ],
    "yamal_europe": [
        (71.0833, 72.6667),
        (70.0, 65.0), (69.0, 55.0), (68.0, 45.0),
        (67.0, 38.0), (66.0, 30.0), (65.0, 25.0),
        (64.0, 20.0), (63.0, 15.0), (62.0, 10.0),
        (60.0, 8.0), (58.0, 5.0), (56.0, 5.0),
        (54.5, 8.0), (53.0, 12.0), (53.9, 14.25),
    ],
    "indonesia_china": [
        (-2.4167, 134.5000),
        (-2.0, 132.0), (0.0, 130.0), (2.0, 128.0),
        (4.0, 126.0), (5.0, 124.0), (5.5, 122.0),
        (5.5, 120.0), (5.0, 118.0), (4.0, 116.0),
        (4.0, 114.0), (5.0, 112.0), (6.0, 110.0),
        (8.0, 108.0), (10.0, 108.0), (12.0, 109.0),
        (15.0, 110.0), (18.0, 111.0), (20.0, 113.0),
        (22.5, 114.5), (25.0, 117.0), (28.0, 120.0),
        (30.0, 121.5),
    ],
    "us_southamerica": [
        (27.8, -97.4),
        (26.0, -96.0), (25.0, -94.0), (24.0, -92.0),
        (23.0, -90.0), (22.0, -88.0), (21.5, -86.0),
        (21.0, -84.0), (20.5, -82.0), (20.0, -80.0),
        (19.5, -78.0), (19.0, -76.0), (18.5, -74.0),
        (18.0, -72.0), (17.0, -70.0), (16.0, -68.0),
        (15.0, -66.0), (14.0, -64.0), (13.0, -62.0),
        (12.0, -60.0), (11.0, -58.0), (10.0, -56.0),
        (8.0, -54.0), (6.0, -52.0), (4.0, -50.0),
        (2.0, -48.0), (0.0, -46.0), (-2.0, -44.0),
        (-3.5, -42.0), (-3.5, -38.8),
    ],
    "us_gulf_mexico": [
        (27.8, -97.4),
        (26.0, -96.0), (25.0, -95.0),
        (24.0, -94.0), (23.0, -93.0),
        (22.4, -97.88),
    ],
    "bonny_brazil": [
        (4.4333, 7.1667),
        (4.0, 5.0), (3.0, 0.0), (2.0, -5.0),
        (1.0, -10.0), (0.0, -15.0), (-1.0, -20.0),
        (-2.0, -25.0), (-3.0, -30.0), (-3.5, -35.0),
        (-3.5, -38.8),
    ],
}


ROUTE_MAP = {
    "mideast_europe": {
        "loading": ["Ras Laffan", "Das Island", "Qalhat"],
        "discharge": [
            "Zeebrugge", "Isle of Grain", "Montoir", "Bilbao",
            "Barcelona", "Fos-sur-Mer", "Gate terminal",
            "Swinoujscie", "Krk",
        ],
    },
    "mideast_asia": {
        "loading": ["Ras Laffan", "Das Island", "Qalhat"],
        "discharge": [
            "Dahej", "Hazira", "Dabhol", "Kochi",
            "Shanghai", "Tianjin", "Ningbo", "Shenzhen",
            "Tokyo Bay", "Futtsu", "Sodegaura",
            "Incheon", "Pyeongtaek",
        ],
    },
    "us_europe": {
        "loading": ["Sabine Pass", "Cove Point", "Elba Island", "Freeport", "Corpus Christi"],
        "discharge": [
            "Zeebrugge", "Isle of Grain", "Montoir", "Bilbao",
            "Barcelona", "Fos-sur-Mer", "Gate terminal",
            "Swinoujscie", "Krk",
        ],
    },
    "us_asia_panama": {
        "loading": ["Sabine Pass", "Freeport", "Corpus Christi"],
        "discharge": [
            "Shanghai", "Tianjin", "Ningbo", "Shenzhen",
            "Tokyo Bay", "Futtsu", "Sodegaura",
            "Incheon", "Pyeongtaek",
        ],
    },
    "australia_japan": {
        "loading": ["Gladstone", "Darwin"],
        "discharge": [
            "Shanghai", "Tianjin", "Ningbo", "Shenzhen",
            "Tokyo Bay", "Futtsu", "Sodegaura",
            "Incheon", "Pyeongtaek",
        ],
    },
    "westafrica_europe": {
        "loading": ["Bonny", "Kribi"],
        "discharge": [
            "Zeebrugge", "Isle of Grain", "Montoir", "Bilbao",
            "Barcelona", "Fos-sur-Mer", "Gate terminal",
            "Swinoujscie", "Krk",
        ],
    },
    "westafrica_americas": {
        "loading": ["Bonny", "Kribi"],
        "discharge": [
            "Altamira", "Manzanillo",
            "Everett", "Cove Point", "Elba Island", "Freeport",
        ],
    },
    "norway_europe": {
        "loading": ["Snohvit"],
        "discharge": [
            "Zeebrugge", "Isle of Grain", "Montoir",
            "Gate terminal",
        ],
    },
    "yamal_europe": {
        "loading": ["Yamal"],
        "discharge": [
            "Zeebrugge", "Isle of Grain", "Montoir",
            "Gate terminal", "Swinoujscie", "Krk",
        ],
    },
    "indonesia_china": {
        "loading": ["Tangguh", "Bontang"],
        "discharge": [
            "Shanghai", "Tianjin", "Ningbo", "Shenzhen",
            "Tokyo Bay", "Futtsu", "Sodegaura",
            "Incheon", "Pyeongtaek",
        ],
    },
    "us_southamerica": {
        "loading": ["Sabine Pass", "Freeport", "Corpus Christi"],
        "discharge": [
            "Bahia Blanca", "Pecem",
        ],
    },
    "us_gulf_mexico": {
        "loading": ["Sabine Pass", "Freeport", "Corpus Christi"],
        "discharge": [
            "Altamira", "Manzanillo",
        ],
    },
    "westafrica_southamerica": {
        "loading": ["Bonny", "Kribi"],
        "discharge": ["Bahia Blanca", "Pecem"],
    },
}

ECA_ZONE_BOUNDS = {
    "Baltic Sea": {
        "lat_min": 53.5, "lat_max": 66.0,
        "lon_min": 10.0, "lon_max": 30.0,
    },
    "North Sea": {
        "lat_min": 48.0, "lat_max": 62.0,
        "lon_min": -5.0, "lon_max": 9.0,
    },
    "North American ECA": {
        "lat_min": 25.0, "lat_max": 60.0,
        "lon_min": -100.0, "lon_max": -50.0,
    },
    "Mediterranean Sea": {
        "lat_min": 35.0, "lat_max": 46.0,
        "lon_min": -6.0, "lon_max": 36.0,
    },
    "US Caribbean Sea ECA": {
        "lat_min": 8.0, "lat_max": 25.0,
        "lon_min": -90.0, "lon_max": -60.0,
    },
    "California ECA": {
        "lat_min": 32.0, "lat_max": 42.0,
        "lon_min": -125.0, "lon_max": -117.0,
    },
}


def get_route_waypoints(load_port_name, discharge_port_name):
    for route_name, route_info in ROUTE_MAP.items():
        if load_port_name in route_info["loading"] and discharge_port_name in route_info["discharge"]:
            wps = ROUTE_WAYPOINTS.get(route_name)
            if wps:
                return _adjust_route_endpoints(wps, load_port_name, discharge_port_name)
    fallback = _generate_great_circle_route(load_port_name, discharge_port_name)
    return fallback


def _adjust_route_endpoints(waypoints, load_port_name, discharge_port_name):
    load_coords = PORT_COORDS.get(load_port_name)
    disch_coords = PORT_COORDS.get(discharge_port_name)
    result = list(waypoints)
    if load_coords:
        result[0] = load_coords
    if disch_coords:
        result[-1] = disch_coords
    return result


def _generate_great_circle_route(load_port_name, discharge_port_name):
    l = PORT_COORDS.get(load_port_name)
    d = PORT_COORDS.get(discharge_port_name)
    if not l or not d:
        return [(0.0, 0.0), (0.0, 0.0)]
    steps = 10
    lat1, lon1 = l
    lat2, lon2 = d
    points = great_circle_interpolate(lat1, lon1, lat2, lon2, steps)
    points[0] = l
    points[-1] = d
    return points


def route_distance_nm(waypoints):
    total = 0.0
    for i in range(len(waypoints) - 1):
        total += haversine_nm(
            waypoints[i][0], waypoints[i][1],
            waypoints[i + 1][0], waypoints[i + 1][1],
        )
    return total


def check_in_any_eca(lat, lon):
    for zone_name, bounds in ECA_ZONE_BOUNDS.items():
        if (bounds["lat_min"] <= lat <= bounds["lat_max"]
                and bounds["lon_min"] <= lon <= bounds["lon_max"]):
            return zone_name
    return None
