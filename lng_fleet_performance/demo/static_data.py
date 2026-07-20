"""Hardcoded static data for 50 LNG vessels.

No database reads needed — all data generated inline for reliable seeding.
"""
import random
import math
from datetime import datetime, timedelta, timezone

VESSELS = [
    {"id": 1, "imo": "9800001", "name": "LNG Atlantic Eagle", "prop": "ME-GI", "cap": 174000, "mcr": 25200, "speed": 19.5, "flag": "MH"},
    {"id": 2, "imo": "9800002", "name": "LNG Pacific Titan", "prop": "X-DF", "cap": 172000, "mcr": 24800, "speed": 19.2, "flag": "PA"},
    {"id": 3, "imo": "9800003", "name": "LNG Nordic Voyager", "prop": "ME-GI", "cap": 170000, "mcr": 25000, "speed": 19.0, "flag": "NO"},
    {"id": 4, "imo": "9800004", "name": "LNG Silk Route", "prop": "X-DF", "cap": 173000, "mcr": 24500, "speed": 19.3, "flag": "SG"},
    {"id": 5, "imo": "9800005", "name": "LNG Desert Star", "prop": "ME-GI", "cap": 175000, "mcr": 25500, "speed": 19.7, "flag": "GB"},
    {"id": 6, "imo": "9800006", "name": "LNG Arctic Pioneer", "prop": "ME-GI", "cap": 171000, "mcr": 25100, "speed": 19.1, "flag": "BS"},
    {"id": 7, "imo": "9800007", "name": "LNG Coral Spirit", "prop": "X-DF", "cap": 176000, "mcr": 24700, "speed": 19.4, "flag": "HK"},
    {"id": 8, "imo": "9800008", "name": "LNG Golden Phoenix", "prop": "ME-GI", "cap": 169000, "mcr": 25300, "speed": 18.9, "flag": "MT"},
    {"id": 9, "imo": "9800009", "name": "LNG Nordic Aurora", "prop": "X-DF", "cap": 174500, "mcr": 24600, "speed": 19.6, "flag": "LR"},
    {"id": 10, "imo": "9800010", "name": "LNG Emerald Bay", "prop": "ME-GI", "cap": 172500, "mcr": 25400, "speed": 19.2, "flag": "IT"},
    {"id": 11, "imo": "9800011", "name": "LNG Northern Lights", "prop": "ME-GI", "cap": 173500, "mcr": 25000, "speed": 19.3, "flag": "NL"},
    {"id": 12, "imo": "9800012", "name": "LNG Triton Wave", "prop": "X-DF", "cap": 171500, "mcr": 24900, "speed": 19.0, "flag": "DE"},
    {"id": 13, "imo": "9800013", "name": "LNG Sapphire Coast", "prop": "ME-GI", "cap": 170500, "mcr": 25200, "speed": 18.8, "flag": "JM"},
    {"id": 14, "imo": "9800014", "name": "LNG Poseidon Grace", "prop": "X-DF", "cap": 175500, "mcr": 24400, "speed": 19.5, "flag": "GR"},
    {"id": 15, "imo": "9800015", "name": "LNG Crimson Tide", "prop": "ME-GI", "cap": 168000, "mcr": 25600, "speed": 18.7, "flag": "KY"},
    {"id": 16, "imo": "9800016", "name": "LNG Ocean Herald", "prop": "ME-GI", "cap": 174200, "mcr": 25100, "speed": 19.4, "flag": "MH"},
    {"id": 17, "imo": "9800017", "name": "LNG Borealis Star", "prop": "X-DF", "cap": 172800, "mcr": 24800, "speed": 19.1, "flag": "PA"},
    {"id": 18, "imo": "9800018", "name": "LNG Wind Chaser", "prop": "ME-GI", "cap": 170800, "mcr": 25300, "speed": 18.9, "flag": "NO"},
    {"id": 19, "imo": "9800019", "name": "LNG Azure Dragon", "prop": "X-DF", "cap": 175200, "mcr": 24600, "speed": 19.6, "flag": "SG"},
    {"id": 20, "imo": "9800020", "name": "LNG Crystal River", "prop": "ME-GI", "cap": 171800, "mcr": 25000, "speed": 19.0, "flag": "GB"},
    {"id": 21, "imo": "9800021", "name": "LNG Meridian Sun", "prop": "ME-GI", "cap": 173200, "mcr": 25400, "speed": 19.3, "flag": "BS"},
    {"id": 22, "imo": "9800022", "name": "LNG Voltaic Storm", "prop": "X-DF", "cap": 174800, "mcr": 24500, "speed": 19.5, "flag": "HK"},
    {"id": 23, "imo": "9800023", "name": "LNG Ember Frontier", "prop": "ME-GI", "cap": 170200, "mcr": 25200, "speed": 18.8, "flag": "MT"},
    {"id": 24, "imo": "9800024", "name": "LNG Neptune Grace", "prop": "X-DF", "cap": 176200, "mcr": 24700, "speed": 19.7, "flag": "LR"},
    {"id": 25, "imo": "9800025", "name": "LNG Iron Horizon", "prop": "ME-GI", "cap": 169500, "mcr": 25500, "speed": 18.6, "flag": "IT"},
    {"id": 26, "imo": "9800026", "name": "LNG Quantum Leap", "prop": "X-DF", "cap": 172200, "mcr": 24800, "speed": 19.2, "flag": "NL"},
    {"id": 27, "imo": "9800027", "name": "LNG Polar Vortex", "prop": "ME-GI", "cap": 173800, "mcr": 25100, "speed": 19.4, "flag": "DE"},
    {"id": 28, "imo": "9800028", "name": "LNG Jade Emperor", "prop": "X-DF", "cap": 171200, "mcr": 24600, "speed": 19.0, "flag": "JM"},
    {"id": 29, "imo": "9800029", "name": "LNG Sterling Current", "prop": "ME-GI", "cap": 175800, "mcr": 25300, "speed": 19.6, "flag": "GR"},
    {"id": 30, "imo": "9800030", "name": "LNG Crimson Arrow", "prop": "X-DF", "cap": 168800, "mcr": 24900, "speed": 18.7, "flag": "KY"},
    {"id": 31, "imo": "9800031", "name": "LNG Indigo Dawn", "prop": "ME-GI", "cap": 174600, "mcr": 25000, "speed": 19.5, "flag": "MH"},
    {"id": 32, "imo": "9800032", "name": "LNG Solaris Wind", "prop": "X-DF", "cap": 172600, "mcr": 24400, "speed": 19.1, "flag": "PA"},
    {"id": 33, "imo": "9800033", "name": "LNG Titan Forge", "prop": "ME-GI", "cap": 170600, "mcr": 25600, "speed": 18.9, "flag": "NO"},
    {"id": 34, "imo": "9800034", "name": "LNG Zephyr Trail", "prop": "X-DF", "cap": 175400, "mcr": 24700, "speed": 19.7, "flag": "SG"},
    {"id": 35, "imo": "9800035", "name": "LNG Opal Horizon", "prop": "ME-GI", "cap": 171600, "mcr": 25200, "speed": 19.0, "flag": "GB"},
    {"id": 36, "imo": "9800036", "name": "LNG Falcon Crest", "prop": "X-DF", "cap": 173600, "mcr": 24500, "speed": 19.3, "flag": "BS"},
    {"id": 37, "imo": "9800037", "name": "LNG Glacier Peak", "prop": "ME-GI", "cap": 174400, "mcr": 25100, "speed": 19.5, "flag": "HK"},
    {"id": 38, "imo": "9800038", "name": "LNG Obsidian Force", "prop": "X-DF", "cap": 170400, "mcr": 24800, "speed": 18.8, "flag": "MT"},
    {"id": 39, "imo": "9800039", "name": "LNG Coral Blaze", "prop": "ME-GI", "cap": 176400, "mcr": 25400, "speed": 19.8, "flag": "LR"},
    {"id": 40, "imo": "9800040", "name": "LNG Tidal Force", "prop": "X-DF", "cap": 169200, "mcr": 24600, "speed": 18.6, "flag": "IT"},
    {"id": 41, "imo": "9800041", "name": "LNG Sapphire Dawn", "prop": "ME-GI", "cap": 172400, "mcr": 25300, "speed": 19.2, "flag": "NL"},
    {"id": 42, "imo": "9800042", "name": "LNG Aurora Borealis", "prop": "X-DF", "cap": 174000, "mcr": 24900, "speed": 19.4, "flag": "DE"},
    {"id": 43, "imo": "9800043", "name": "LNG Neptune's Fury", "prop": "ME-GI", "cap": 171000, "mcr": 25000, "speed": 19.0, "flag": "JM"},
    {"id": 44, "imo": "9800044", "name": "LNG Solar Wind", "prop": "X-DF", "cap": 175000, "mcr": 24700, "speed": 19.6, "flag": "GR"},
    {"id": 45, "imo": "9800045", "name": "LNG Ironclad Spirit", "prop": "ME-GI", "cap": 169800, "mcr": 25500, "speed": 18.7, "flag": "KY"},
    {"id": 46, "imo": "9800046", "name": "LNG Crystal Voyager", "prop": "X-DF", "cap": 173400, "mcr": 24800, "speed": 19.3, "flag": "MH"},
    {"id": 47, "imo": "9800047", "name": "LNG Eclipse Runner", "prop": "ME-GI", "cap": 171400, "mcr": 25200, "speed": 19.1, "flag": "PA"},
    {"id": 48, "imo": "9800048", "name": "LNG Phantom Tide", "prop": "X-DF", "cap": 175600, "mcr": 24400, "speed": 19.7, "flag": "NO"},
    {"id": 49, "imo": "9800049", "name": "LNG Thunder Hawk", "prop": "ME-GI", "cap": 170000, "mcr": 25600, "speed": 18.8, "flag": "SG"},
    {"id": 50, "imo": "9800050", "name": "LNG Serenity Star", "prop": "X-DF", "cap": 172000, "mcr": 24600, "speed": 19.2, "flag": "GB"},
]

PORTS = [
    ("Ras Laffan", 25.93, 51.56), ("Qatar", 25.29, 51.53),
    ("Ain Sukhna", 29.60, 32.34), ("Dahej", 21.71, 72.56),
    ("Mumbai", 18.95, 72.84), ("Kochi", 9.97, 76.27),
    ("Arzew", 35.85, -0.29), ("Sines", 37.97, -8.87),
    ("Zeebrugge", 51.33, 3.18), ("Soyo", -6.13, 12.37),
    ("Sabine Pass", 29.73, -93.86), ("Freeport TX", 28.95, -95.31),
    ("Ichthys", -12.44, 130.44), ("Gorgon", -20.80, 115.36),
    ("Tangguh", -2.80, 132.38), ("Gladstone", -23.84, 151.27),
    ("Hamad", 25.29, 51.53), ("Basrah", 30.51, 47.81),
]

CHARTERERS = ["Shell International", "BP Gas Marketing", "TotalEnergies LNG",
              "Qatargas Marketing", "Cheniere Marketing"]

ENGINE_MFR = {"ME-GI": "MAN Energy Solutions", "X-DF": "WinGD"}
ENGINE_MODEL = {"ME-GI": "ME-GI 7G80", "X-DF": "X-DF 7G80"}


def generate_all_vessel_rows():
    """Generate all 50 vessel rows for INSERT."""
    rows = []
    for v in VESSELS:
        vid = v["id"]
        prop = v["prop"]
        gt = v["cap"] * 0.48
        dwt = v["cap"] * 1.01
        rows.append((
            vid, v["imo"], v["name"], "LNG Carrier", v["flag"], "DNV",
            round(gt, 0), round(dwt, 0), v["cap"], 4, prop,
            ENGINE_MFR.get(prop), ENGINE_MODEL.get(prop), v["mcr"],
            v["speed"], v["speed"] + 0.5,
            round(4.80 + (vid % 10) * 0.01, 2),
            round(4.80 + (vid % 10) * 0.01 * 0.95, 2),
            round(4.80 + (vid % 10) * 0.01 * 0.95, 2),
            2020, 0, 1,
        ))
    return rows


def generate_all_tank_rows():
    """Generate 4 tanks per vessel = 200 rows."""
    rows = []
    for v in VESSELS:
        vid = v["id"]
        tc = v["cap"] / 4
        for i in range(1, 5):
            rows.append((
                vid, f"Tank {i}",
                "port" if i <= 2 else "starboard",
                round(tc, 1), 1.2, 111.0, "membrane",
            ))
    return rows


def generate_all_voyage_rows():
    """Generate 3 voyages per vessel = 150 rows. Returns (voyage_rows, waypoint_data)."""
    now = datetime.now(timezone.utc)
    voyages = []
    wp_data = []

    for v in VESSELS:
        vid = v["id"]
        for vi in range(3):
            days_ago = 30 + vi * 35
            dep = now - timedelta(days=days_ago)
            arr = dep + timedelta(days=12 + vi * 2)
            li = (vid + vi) % len(PORTS)
            di = (vid + vi + 3) % len(PORTS)
            ll, ln = PORTS[li][1], PORTS[li][2]
            dl, dn = PORTS[di][1], PORTS[di][2]
            dist = math.sqrt((dl - ll) ** 2 + (dn - ln) ** 2) * 60
            cargo = 70000 + (vid * 1000) % 15000
            fuel = cargo * 0.0012 * (dist / 1000) * 8
            bog = cargo * 0.0004 * ((arr - dep).total_seconds() / 86400)
            status = "completed" if vi > 0 else "in_progress"
            vn = f"V-{vid:03d}-2025-{vi + 1:03d}"

            voyages.append((
                vid, vn, f"Charterer {vid % 5 + 1}",
                PORTS[li][0], PORTS[di][0], cargo, "LNG",
                dep.isoformat(), dep.isoformat(), arr.isoformat(),
                arr.isoformat() if status == "completed" else None,
                status, "weather_optimized",
                round(dist, 0), round(fuel, 1), round(bog, 1), round(fuel * 2.75, 1),
                12.0 if vi % 3 == 0 else 0,
                1 if PORTS[di][0] in ("Sines", "Zeebrugge", "Arzew", "Ain Sukhna") else 0,
            ))
            wp_data.append((ll, ln, dl, dn, 10 + vi * 2))

    return voyages, wp_data


def generate_all_waypoint_rows(voyage_id_map, voyage_meta):
    """Generate waypoints for all voyages."""
    now = datetime.now(timezone.utc)
    rows = []
    now_str = now.isoformat()

    idx = 0
    for v in VESSELS:
        vid = v["id"]
        for vi in range(3):
            vn = f"V-{vid:03d}-2025-{vi + 1:03d}"
            voyage_id = voyage_id_map.get((vid, vn))
            if not voyage_id:
                continue
            ll, ln, dl, dn, nwp = voyage_meta[idx]
            for i in range(nwp):
                frac = i / (nwp - 1) if nwp > 1 else 0
                lat = ll + frac * (dl - ll) + random.uniform(-0.5, 0.5)
                lon = ln + frac * (dn - ln) + random.uniform(-0.5, 0.5)
                spd = v["speed"] + random.uniform(-1.5, 2.0)
                crs = math.degrees(math.atan2(dn - ln, dl - ll)) % 360
                rows.append((
                    voyage_id, i + 1, round(lat, 4), round(lon, 4),
                    f"WP-{i + 1:03d}", round(spd, 1),
                    round(spd + random.uniform(-0.5, 0.5), 1),
                    round(crs, 1), 1 if abs(lat) > 35 else 0,
                    round(random.uniform(0.5, 4.0), 1),
                    round(random.uniform(5, 25), 1),
                ))
            idx += 1

    return rows


def generate_all_certificate_rows():
    """Generate 6 certs per vessel = 300 rows."""
    now = datetime.now(timezone.utc)
    cert_types = [
        ("IAPP", "International Air Pollution Prevention Certificate"),
        ("EIAPP", "Engine International Air Pollution Prevention Certificate"),
        ("IEE", "International Energy Efficiency Certificate"),
        ("IGC", "International Gas Carrier Code Certificate"),
        ("ISM", "International Safety Management Certificate"),
        ("ISPS", "International Ship Security Certificate"),
    ]
    rows = []
    for v in VESSELS:
        vid = v["id"]
        for ct, cn in cert_types:
            iss = now - timedelta(days=random.randint(100, 700))
            exp = iss + timedelta(days=365 * 5)
            if (exp - now).days < 120:
                exp = now + timedelta(days=random.randint(30, 200))
            st = "valid" if (exp - now).days > 0 else "expired"
            rows.append((
                vid, ct, f"{ct}-{vid:03d}-{random.randint(1000, 9999)}",
                "DNV", iss.strftime("%Y-%m-%d"), exp.strftime("%Y-%m-%d"),
                st, f"{cn} - auto-generated",
            ))
    return rows


def generate_all_cii_rows():
    """Generate CII assessment for each vessel."""
    now = datetime.now(timezone.utc)
    boundaries = {"A": 5.05, "B": 5.70, "C": 6.40, "D": 7.15}
    rows = []
    for v in VESSELS:
        vid = v["id"]
        dwt = v["cap"] * 1.01
        total_co2 = random.uniform(6000, 15000)
        total_dist = random.uniform(40000, 80000)
        aer = (total_co2 * 1e6) / (dwt * max(total_dist, 1))
        cv = round(aer, 2)
        r = "A" if cv <= boundaries["A"] else "B" if cv <= boundaries["B"] else "C" if cv <= boundaries["C"] else "D" if cv <= boundaries["D"] else "E"
        rows.append((
            vid, now.strftime("%Y-%m-%d"), round(total_co2, 1),
            round(total_dist * dwt * 0.001, 0), cv, r,
            round(total_dist, 0), round(total_dist * dwt * 0.001 * 0.85, 0),
            round(random.uniform(500, 1500), 0), round(random.uniform(1500, 4000), 0),
            round(total_co2 * 0.15, 1), round(total_co2 * 0.002, 1),
        ))
    return rows


def generate_all_hull_rows():
    """Generate hull performance for each vessel, 4 records = 200 rows."""
    now = datetime.now(timezone.utc)
    rows = []
    for v in VESSELS:
        vid = v["id"]
        spd = v["speed"]
        pwr = random.uniform(18000, 26000)
        trm = random.uniform(1.5, 3.5)
        rp = 75 * (spd ** 3)
        dp = ((pwr - rp) / max(rp, 1)) * 100
        rough = 0.20 + max(0, dp) * 0.002
        fouling = "clean" if dp < 5 else ("light" if dp < 15 else "moderate")
        for da in [0, 30, 60, 90]:
            d = now - timedelta(days=da)
            rows.append((
                vid, d.strftime("%Y-%m-%d"),
                round(spd + random.uniform(-0.5, 0.5), 1),
                round(pwr + random.uniform(-500, 500), 0),
                round(random.uniform(5, 20), 1), round(random.uniform(0, 360), 0),
                random.randint(3, 6), round(288 + random.uniform(-3, 3), 1),
                round(8.5 + random.uniform(-0.3, 0.3), 2),
                round(9.5 + random.uniform(-0.3, 0.3), 2),
                round(trm + random.uniform(-0.2, 0.2), 2),
                round(rp, 0), round(dp, 1),
                round(rough + random.uniform(-0.02, 0.02), 3),
                fouling, round(0.70 + random.uniform(-0.05, 0.05), 3),
            ))
    return rows


def generate_all_digital_twin_rows():
    """Generate digital twin for each vessel, 4 records = 200 rows."""
    now = datetime.now(timezone.utc)
    rows = []
    for v in VESSELS:
        vid = v["id"]
        for da in [0, 7, 14, 30]:
            d = now - timedelta(days=da)
            rows.append((
                vid, d.isoformat(),
                round(0.82 + random.uniform(-0.1, 0.15), 3),
                round(0.88 + random.uniform(-0.08, 0.1), 3),
                round(0.85 + random.uniform(-0.1, 0.12), 3),
                round(random.uniform(180, 600), 0),
                round(random.uniform(200, 800), 0),
                round(random.uniform(0, 0.3), 3), "v2.1",
            ))
    return rows


def generate_all_alert_rows():
    """Generate 1 alert for 15 vessels = 15 rows."""
    now = datetime.now(timezone.utc)
    alert_types = [
        ("hull_fouling", "medium", "hull", "Hull fouling degradation detected"),
        ("bor_increase", "low", "cargo", "BOR rate slightly elevated"),
        ("engine_efficiency", "low", "engine", "SFOC deviation above baseline"),
        ("cii_projection", "high", "compliance", "CII rating projected to fall to D"),
        ("certificate_expiry", "medium", "certificates", "IEE certificate expiring within 90 days"),
    ]
    rows = []
    for v in VESSELS[:15]:
        at, se, cp, de = random.choice(alert_types)
        rows.append((
            v["id"], now.isoformat(), at, se, cp, de,
            random.randint(30, 180), round(random.uniform(60, 95), 1),
            f"Schedule inspection for {cp}", 0, 0,
        ))
    return rows


def generate_all_charter_party_rows(voyage_ids):
    """Generate charter party for each voyage."""
    now = datetime.now(timezone.utc)
    rows = []
    for vid in voyage_ids:
        rows.append((
            vid, random.choice(CHARTERERS), "voyage",
            round(18.5 + random.uniform(0, 2), 1),
            85.0, 3.0, 0.06, 1.5, 15.0, 6, 35000,
            "Speed and consumption warranty per BIMCO SHELLTIME4",
            (now - timedelta(days=60)).isoformat(),
            (now + timedelta(days=300)).isoformat(),
        ))
    return rows
