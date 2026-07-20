from datetime import datetime

RANDOM_SEED = 42

NUM_VESSELS = 10
DEFAULT_START_DATE = datetime(2025, 6, 1)
DEFAULT_NUM_DAYS = 30
TELEMETRY_INTERVAL_MINUTES = 5
BOG_INTERVAL_MINUTES = 60

LOGGING_LOAD_PORTS = [
    "Ras Laffan", "Sabine Pass", "Gladstone", "Bonny", "Snohvit",
    "Yamal", "Das Island", "Qalhat", "Kribi", "Tangguh", "Bontang", "Darwin",
]

DISCHARGE_PORTS = [
    "Zeebrugge", "Isle of Grain", "Montoir", "Bilbao", "Barcelona",
    "Fos-sur-Mer", "Gate terminal", "Swinoujscie", "Krk",
    "Everett", "Cove Point", "Elba Island", "Freeport", "Corpus Christi",
    "Altamira", "Manzanillo", "Bahia Blanca", "Pecem",
    "Dahej", "Hazira", "Dabhol", "Kochi",
    "Shanghai", "Tianjin", "Ningbo", "Shenzhen",
    "Tokyo Bay", "Futtsu", "Sodegaura",
    "Incheon", "Pyeongtaek",
]

ECA_SOX_LIMIT = 0.001
ECA_SULFUR_LIMIT_PCT = 0.10
ECA_FUEL_TYPE = "ULSFO"
OPEN_SEA_FUEL_TYPE = "LNG"
VLSFO_SULFUR_PCT = 0.50
ULSFO_SULFUR_PCT = 0.10
MGO_SULFUR_PCT = 0.10
LNG_SULFUR_PCT = 0.0

LNG_CO2_FACTOR = 2.75
MGO_CO2_FACTOR = 3.15
VLSFO_CO2_FACTOR = 3.11

LNG_SOX_FACTOR_KG_PER_TON = 0.0
VLSFO_SOX_FACTOR_KG_PER_TON = 10.0
ULSFO_SOX_FACTOR_KG_PER_TON = 2.0
MGO_SOX_FACTOR_KG_PER_TON = 2.0

SFOC_GAS_RANGE = (165, 185)
SFOC_DIESEL_RANGE = (175, 195)

BOR_MIN = 0.08
BOR_MAX = 0.15

SERVICE_SPEED_RANGE = (16.0, 19.5)

CII_RATING_BOUNDARIES = {
    "A": 0.85,
    "B": 0.95,
    "C": 1.05,
    "D": 1.15,
}

ENGINE_TYPES = ["ME-GI", "X-DF", "TFDE", "ST"]
METHANE_SLIP_RANGES = {
    "ME-GI": (0.2, 0.5),
    "X-DF": (0.5, 1.5),
    "TFDE": (1.5, 2.5),
    "ST": (0.0, 0.0),
}

SHAFT_POWER_RANGE = {
    138000: (25000, 32000),
    145000: (28000, 35000),
    155000: (30000, 38000),
    160000: (32000, 40000),
    170000: (33000, 41000),
    174000: (35000, 42000),
    180000: (36000, 45000),
}

ENGINE_RPM_RANGE = (70, 95)

TANK_TEMP_RANGE = (-163, -158)
TANK_PRESSURE_RANGE = (1.01, 1.10)
NUM_CARGO_TANKS = 4

HIRE_RATE_RANGE = (35000, 80000)
DEMURRAGE_RATE_RANGE = (40000, 90000)
CHARTERER_NAMES = [
    "Shell", "BP", "TotalEnergies", "Chevron", "ExxonMobil",
    "QatarEnergy", "Cheniere", "Knutsen", "Mitsui", "MOL",
    "NYK Line", "KLine", "GasLog", "Flex LNG", "BW LNG",
]

MAINTENANCE_COMPONENTS = [
    "Main Engine", "Aux Engine", "Turbocharger", "GCU",
    "Cargo Pump", "Vaporizer", "Reliquefaction Unit",
    "Boiler", "Propeller", "Rudder", "Hull Coating",
    "Shaft Generator", "SCR System", "EGR System",
    "Fuel Gas Supply System", "Ballast Water Treatment",
]

PORT_TIME_HOURS_MIN = 12
PORT_TIME_HOURS_MAX = 36
BUFFER_DAYS_BETWEEN_VOYAGES = (0, 3)
