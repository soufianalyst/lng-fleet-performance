SCHEMA_SQL = """
-- ============================================================
-- LNG CARRIER FLEET PERFORMANCE MANAGEMENT SYSTEM
-- Database Schema (SQLite)
-- ============================================================

-- ============================================================
-- CORE VESSEL DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS vessels (
    vessel_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    imo_number           TEXT UNIQUE NOT NULL,
    vessel_name          TEXT NOT NULL,
    vessel_type          TEXT NOT NULL DEFAULT 'LNG Carrier',
    flag_state           TEXT NOT NULL,
    classification_society TEXT,
    gross_tonnage        REAL,
    deadweight_tonnage   REAL,
    cargo_capacity_m3    REAL,
    number_of_tanks      INTEGER DEFAULT 4,
    propulsion_type      TEXT NOT NULL DEFAULT 'ME-GI',
    engine_manufacturer  TEXT,
    engine_model         TEXT,
    engine_mcr_kw        REAL,
    service_speed_kn     REAL,
    design_speed_kn      REAL,
    eexi_value           REAL,
    eedi_value           REAL,
    cii_reference_value  REAL,
    year_of_build        INTEGER,
    ice_class            TEXT,
    scrubber_equipped    INTEGER DEFAULT 0,
    reliquefaction_plant INTEGER DEFAULT 0,
    shaft_power_meter    INTEGER DEFAULT 1,
    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS vessel_tanks (
    tank_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    tank_name            TEXT NOT NULL,
    tank_position        TEXT,
    capacity_m3          REAL NOT NULL,
    design_pressure_bar  REAL,
    design_temperature_k REAL,
    insulation_type      TEXT DEFAULT 'membrane',
    sensor_count         INTEGER DEFAULT 12,
    UNIQUE(vessel_id, tank_name)
);

-- ============================================================
-- VOYAGE DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS voyages (
    voyage_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    voyage_number        TEXT NOT NULL,
    charterer            TEXT,
    load_port            TEXT NOT NULL,
    discharge_port       TEXT NOT NULL,
    cargo_quantity_mt    REAL,
    cargo_type           TEXT DEFAULT 'LNG',
    planned_departure    TEXT,
    actual_departure     TEXT,
    planned_arrival      TEXT,
    actual_arrival       TEXT,
    status               TEXT DEFAULT 'planned',
    route_type           TEXT DEFAULT 'weather_optimized',
    total_distance_nm    REAL,
    total_fuel_hfo_mt    REAL DEFAULT 0,
    total_fuel_vlsfo_mt  REAL DEFAULT 0,
    total_fuel_ulsfo_mt  REAL DEFAULT 0,
    total_fuel_mgo_mt    REAL DEFAULT 0,
    total_fuel_lng_mt    REAL DEFAULT 0,
    total_bog_mt         REAL DEFAULT 0,
    co2_total_mt         REAL,
    cii_voyage_value     REAL,
    eca_time_hours       REAL DEFAULT 0,
    eu_ets_applicable    INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now')),
    UNIQUE(vessel_id, voyage_number)
);

CREATE TABLE IF NOT EXISTS voyage_waypoints (
    waypoint_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    sequence_num         INTEGER NOT NULL,
    latitude             REAL NOT NULL,
    longitude            REAL NOT NULL,
    waypoint_name        TEXT,
    eta_utc              TEXT,
    ata_utc              TEXT,
    speed_planned_kn     REAL,
    speed_actual_kn      REAL,
    course_deg           REAL,
    in_eca               INTEGER DEFAULT 0,
    eca_zone_name        TEXT,
    water_depth_m        REAL,
    weather_hs_m         REAL,
    weather_tp_s         REAL,
    weather_direction_deg REAL,
    wind_speed_kn        REAL,
    wind_direction_deg   REAL,
    current_speed_kn     REAL,
    current_direction_deg REAL,
    fuel_consumption_mt  REAL,
    shaft_power_kw       REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- CARGO & BOR DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS cargo_records (
    cargo_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    tank_id              INTEGER NOT NULL REFERENCES vessel_tanks(tank_id),
    record_timestamp     TEXT NOT NULL,
    cargo_level_pct      REAL,
    cargo_volume_m3      REAL,
    cargo_mass_mt        REAL,
    cargo_temperature_k  REAL,
    cargo_pressure_bar   REAL,
    cargo_composition_methane REAL DEFAULT 0.87,
    cargo_composition_ethane REAL DEFAULT 0.08,
    cargo_composition_propane REAL DEFAULT 0.03,
    cargo_composition_butane REAL DEFAULT 0.01,
    cargo_composition_nitrogen REAL DEFAULT 0.01,
    bog_generation_rate_kg_h REAL,
    tank_top_temp_k      REAL,
    tank_mid_temp_k      REAL,
    tank_bottom_temp_k   REAL,
    stratification_index REAL,
    rollover_risk_level  TEXT DEFAULT 'low',
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bor_daily_summary (
    bor_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    summary_date         TEXT NOT NULL,
    avg_bor_pct_day      REAL,
    measured_bor_pct_day REAL,
    energy_balance_bor   REAL,
    bog_to_engine_mt     REAL DEFAULT 0,
    bog_to_reliquefaction_mt REAL DEFAULT 0,
    bog_to_gcu_mt        REAL DEFAULT 0,
    reliquefaction_power_kw REAL,
    reliquefaction_cop   REAL,
    tank_avg_temp_k      REAL,
    sea_water_temp_k     REAL,
    ambient_temp_k       REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- ENGINE & MACHINERY DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS engine_performance (
    engine_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    engine_mode          TEXT DEFAULT 'gas',
    engine_speed_rpm     REAL,
    shaft_power_kw       REAL,
    mcr_pct              REAL,
    sfoc_actual_g_kwh    REAL,
    sfoc_reference_g_kwh REAL,
    sfoc_delta           REAL,
    thermal_efficiency_pct REAL,
    cylinder_pmax_bar    REAL,
    cylinder_pcomp_bar   REAL,
    exhaust_temp_cyl_avg REAL,
    turbocharger_speed_rpm REAL,
    turbocharger_surge_margin REAL,
    scavenge_air_temp_c  REAL,
    scavenge_air_pressure_bar REAL,
    fuel_injection_timing_deg REAL,
    pilot_fuel_pct       REAL,
    gas_admission_valve_timing REAL,
    methane_slip_g_kwh   REAL,
    specific_bog_consumption REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS engine_cylinder_data (
    cyl_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    engine_perf_id       INTEGER NOT NULL REFERENCES engine_performance(engine_id),
    cylinder_number      INTEGER NOT NULL,
    pmax_bar             REAL,
    pcomp_bar            REAL,
    exhaust_temp_c       REAL,
    fuel_pressure_bar    REAL,
    deviation_pmax_pct   REAL,
    deviation_exhaust_pct REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS auxiliary_engines (
    aux_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    aux_engine_number    INTEGER DEFAULT 1,
    load_kw              REAL,
    load_pct             REAL,
    sfoc_g_kwh           REAL,
    fuel_type            TEXT DEFAULT 'VLSFO',
    running_hours        REAL,
    exhaust_temp_c       REAL,
    oil_pressure_bar     REAL,
    coolant_temp_c       REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS hull_performance (
    hull_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    record_date          TEXT NOT NULL,
    speed_kn             REAL,
    shaft_power_kw       REAL,
    wind_speed_kn        REAL,
    wind_direction_deg   REAL,
    current_speed_kn     REAL,
    current_direction_deg REAL,
    sea_state            INTEGER,
    water_temp_k         REAL,
    water_depth_m        REAL,
    displacement_mt      REAL,
    draft_fwd_m          REAL,
    draft_aft_m          REAL,
    trim_m               REAL,
    reference_power_kw   REAL,
    power_deviation_pct  REAL,
    friction_coeff_delta REAL,
    equivalent_roughness_mm REAL,
    fouling_level        TEXT DEFAULT 'clean',
    qpc_trending         REAL,
    hull_cleaning_due    INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- CII & COMPLIANCE DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS cii_assessment (
    cii_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    assessment_year      INTEGER NOT NULL,
    assessment_date      TEXT NOT NULL,
    annual_co2_mt        REAL,
    annual_cargo_mt_nm   REAL,
    cii_calculated       REAL,
    cii_required         REAL,
    cii_rating           TEXT,
    rating_boundary_a    REAL,
    rating_boundary_b    REAL,
    rating_boundary_c    REAL,
    rating_boundary_d    REAL,
    projected_year_end_cii REAL,
    projected_rating     TEXT,
    distance_sailed_nm   REAL,
    cargo_carried_mt     REAL,
    port_time_hours      REAL,
    sea_time_hours       REAL,
    fuel_hfo_mt          REAL,
    fuel_vlsfo_mt        REAL,
    fuel_ulsfo_mt        REAL,
    fuel_mgo_mt          REAL,
    fuel_lng_mt          REAL,
    bog_consumed_mt      REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS eu_ets_records (
    ets_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_type          TEXT NOT NULL,
    eu_port_call         TEXT,
    voyage_leg_from      TEXT,
    voyage_leg_to        TEXT,
    emission_factor_mt   REAL,
    emissions_mt_co2     REAL,
    allocation_pct       REAL,
    allocated_emissions_mt REAL,
    eu_allowance_cost_eur REAL,
    verification_status  TEXT DEFAULT 'pending',
    verification_body    TEXT,
    surrender_deadline   TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fueleu_records (
    fueleu_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_date          TEXT NOT NULL,
    fuel_type            TEXT NOT NULL,
    fuel_mass_mt         REAL,
    energy_mj            REAL,
    ghg_wtw_co2e_mt      REAL,
    ghg_intensity_g_mj   REAL,
    reference_value_g_mj REAL DEFAULT 91.16,
    compliance_balance   REAL,
    penalty_cost_eur     REAL DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- EMISSIONS & ECA DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS emissions_log (
    emission_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    position_lat         REAL,
    position_lon         REAL,
    in_eca               INTEGER DEFAULT 0,
    eca_zone_name        TEXT,
    fuel_type            TEXT NOT NULL,
    fuel_consumption_mt_h REAL,
    co2_emissions_kg_h   REAL,
    sox_emissions_kg_h   REAL,
    nox_emissions_kg_h   REAL,
    ch4_emissions_kg_h   REAL,
    pm_emissions_kg_h    REAL,
    co2e_wtw_kg_h        REAL,
    sox_limit_ppm        REAL,
    nox_limit_g_kwh      REAL,
    compliance_status    TEXT DEFAULT 'compliant',
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS eca_events (
    event_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    voyage_id            INTEGER REFERENCES voyages(voyage_id),
    event_type           TEXT NOT NULL,
    eca_zone_name        TEXT,
    event_timestamp      TEXT NOT NULL,
    position_lat         REAL,
    position_lon         REAL,
    fuel_type_before     TEXT,
    fuel_type_after      TEXT,
    sox_before_ppm       REAL,
    sox_after_ppm        REAL,
    nox_compliant        INTEGER DEFAULT 1,
    distance_to_eca_nm   REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fuel_switch_log (
    switch_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    voyage_id            INTEGER REFERENCES voyages(voyage_id),
    switch_timestamp     TEXT NOT NULL,
    position_lat         REAL,
    position_lon         REAL,
    fuel_type_from       TEXT NOT NULL,
    fuel_type_to         TEXT NOT NULL,
    fuel_quantity_from_mt REAL,
    fuel_quantity_to_mt  REAL,
    sulfur_content_from  REAL,
    sulfur_content_to    REAL,
    reason               TEXT,
    completion_pct       REAL DEFAULT 100,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- CHARTER PARTY DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS charter_party (
    cp_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    charterer            TEXT NOT NULL,
    charter_type         TEXT DEFAULT 'voyage',
    speed_warranted_kn   REAL,
    consumption_warranted_mt_day REAL,
    consumption_tolerance_pct REAL DEFAULT 3.0,
    bor_warranted_pct_day REAL,
    bor_tolerance_pct    REAL DEFAULT 1.5,
    sea_margin_pct       REAL DEFAULT 15.0,
    weather_exclusion_beaufort INTEGER DEFAULT 6,
    off_hire_rate_usd_day REAL,
    performance_warranty  TEXT,
    contract_start       TEXT,
    contract_end         TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS charter_performance (
    perf_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    cp_id                INTEGER REFERENCES charter_party(cp_id),
    record_date          TEXT NOT NULL,
    speed_actual_kn      REAL,
    speed_warranted_kn   REAL,
    speed_weather_corrected_kn REAL,
    consumption_actual_mt REAL,
    consumption_warranted_mt REAL,
    consumption_weather_corrected_mt REAL,
    consumption_deviation_pct REAL,
    speed_deviation_pct  REAL,
    off_hire_hours       REAL DEFAULT 0,
    off_hire_reason      TEXT,
    weather_exclusion_applied INTEGER DEFAULT 0,
    wind_speed_kn        REAL,
    sea_state_beaufort   INTEGER,
    performance_compliant INTEGER DEFAULT 1,
    discrepancy_alert    INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS off_hire_events (
    off_hire_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    event_start          TEXT NOT NULL,
    event_end            TEXT,
    event_type           TEXT NOT NULL,
    cause                TEXT,
    speed_loss_kn        REAL,
    duration_hours       REAL,
    weather_factor       REAL DEFAULT 0,
    net_off_hire_hours   REAL,
    cost_usd             REAL,
    evidence_hash        TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- DIGITAL TWIN & PREDICTIVE MAINTENANCE
-- ============================================================

CREATE TABLE IF NOT EXISTS digital_twin_state (
    twin_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    record_timestamp     TEXT NOT NULL,
    engine_health_index  REAL,
    hull_health_index    REAL,
    bog_system_health    REAL,
    predicted_rul_engine_days REAL,
    predicted_rul_hull_days  REAL,
    anomaly_score        REAL,
    anomalies_detected   TEXT,
    model_version        TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS maintenance_events (
    maintenance_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    component            TEXT NOT NULL,
    component_serial     TEXT,
    maintenance_type     TEXT NOT NULL,
    priority             TEXT DEFAULT 'medium',
    scheduled_date       TEXT,
    completed_date       TEXT,
    actual_cost_usd      REAL,
    estimated_cost_usd   REAL,
    work_description     TEXT,
    port_of_repair       TEXT,
    status               TEXT DEFAULT 'planned',
    predicted_rul_days   REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS predictive_alerts (
    alert_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    alert_timestamp      TEXT NOT NULL,
    alert_type           TEXT NOT NULL,
    severity             TEXT NOT NULL,
    component            TEXT NOT NULL,
    description          TEXT NOT NULL,
    predicted_failure_days REAL,
    confidence_pct       REAL,
    recommended_action   TEXT,
    acknowledged         INTEGER DEFAULT 0,
    resolved             INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- SCRUBBER & NOX AFTER-TREATMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS scrubber_data (
    scrubber_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    mode                 TEXT DEFAULT 'open_loop',
    wash_water_ph        REAL,
    wash_water_pah       REAL,
    wash_water_turbidity REAL,
    sox_inlet_ppm        REAL,
    sox_outlet_ppm       REAL,
    removal_efficiency   REAL,
    wash_water_flow_m3_h REAL,
    power_consumption_kw REAL,
    naoh_consumption_kg_h REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scr_data (
    scr_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    nox_inlet_ppm        REAL,
    nox_outlet_ppm       REAL,
    denox_efficiency_pct REAL,
    catalyst_bed_temp_c  REAL,
    urea_consumption_kg_h REAL,
    ammonia_slip_ppm     REAL,
    exhaust_temp_in_c    REAL,
    exhaust_temp_out_c   REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- WEATHER DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS weather_data (
    weather_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    position_lat         REAL,
    position_lon         REAL,
    source               TEXT DEFAULT 'GFS',
    wind_speed_kn        REAL,
    wind_direction_deg   REAL,
    significant_wave_height_m REAL,
    wave_period_s        REAL,
    wave_direction_deg   REAL,
    sea_water_temp_k     REAL,
    air_temp_k           REAL,
    air_pressure_hpa     REAL,
    visibility_nm        REAL,
    precipitation_mm_h   REAL,
    current_speed_kn     REAL,
    current_direction_deg REAL,
    sea_ice_coverage_pct REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- SENSOR DATA (BUFFER)
-- ============================================================

CREATE TABLE IF NOT EXISTS sensor_readings (
    reading_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    sensor_type          TEXT NOT NULL,
    sensor_name          TEXT NOT NULL,
    value                REAL NOT NULL,
    unit                 TEXT,
    quality_flag         TEXT DEFAULT 'good',
    record_timestamp     TEXT NOT NULL,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sensor_vessel_time
    ON sensor_readings(vessel_id, record_timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_type_time
    ON sensor_readings(sensor_type, record_timestamp);

-- ============================================================
-- AUDIT LOG (TAMPER-EVIDENT)
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    log_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name           TEXT NOT NULL,
    record_id            INTEGER NOT NULL,
    action               TEXT NOT NULL,
    data_hash            TEXT NOT NULL,
    timestamp_utc        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_table_record
    ON audit_log(table_name, record_id);

-- ============================================================
-- REGULATORY CERTIFICATES
-- ============================================================

CREATE TABLE IF NOT EXISTS certificates (
    cert_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    cert_type            TEXT NOT NULL,
    cert_number          TEXT,
    issuing_authority    TEXT,
    issue_date           TEXT,
    expiry_date          TEXT,
    status               TEXT DEFAULT 'valid',
    document_path        TEXT,
    notes                TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- FUEL BUNKERING RECORDS
-- ============================================================

CREATE TABLE IF NOT EXISTS bunkering_records (
    bunker_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    voyage_id            INTEGER REFERENCES voyages(voyage_id),
    bunkering_date       TEXT NOT NULL,
    port                 TEXT NOT NULL,
    fuel_type            TEXT NOT NULL,
    quantity_mt          REAL NOT NULL,
    sulfur_content_pct   REAL,
    carbon_content_pct   REAL,
    density_kg_m3        REAL,
    calorific_value_mj_kg REAL,
    supplier             TEXT,
    bdn_number           TEXT,
    unit_price_usd       REAL,
    total_cost_usd       REAL,
    verified             INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- CONFIGURATION TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS eca_zones (
    zone_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_name            TEXT UNIQUE NOT NULL,
    zone_type            TEXT NOT NULL,
    sox_limit_pct        REAL,
    nox_tier             TEXT,
    effective_date       TEXT,
    boundary_polygon     TEXT,
    status               TEXT DEFAULT 'active',
    notes                TEXT
);

CREATE TABLE IF NOT EXISTS cii_rating_boundaries (
    boundary_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ship_type            TEXT NOT NULL,
    year                 INTEGER NOT NULL,
    boundary_a           REAL,
    boundary_b           REAL,
    boundary_c           REAL,
    boundary_d           REAL,
    created_at           TEXT DEFAULT (datetime('now')),
    UNIQUE(ship_type, year)
);

-- ============================================================
-- EEXI COMPLIANCE
-- ============================================================

CREATE TABLE IF NOT EXISTS eexi_assessment (
    assessment_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    assessment_year      INTEGER NOT NULL,
    attained_eexi        REAL NOT NULL,
    required_eexi        REAL NOT NULL,
    compliant            INTEGER NOT NULL,
    epl_power_limit_pct  REAL DEFAULT 100,
    reference_speed_kn   REAL,
    reference_power_kw   REAL,
    ship_type_code       TEXT DEFAULT 'LNG',
    calculation_method   TEXT DEFAULT 'ISO_20414',
    notes                TEXT,
    created_at           TEXT DEFAULT (datetime('now')),
    UNIQUE(vessel_id, assessment_year)
);

CREATE TABLE IF NOT EXISTS epl_config (
    epl_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    eca_zone_name        TEXT,
    power_limit_pct      REAL NOT NULL DEFAULT 100,
    override_active      INTEGER DEFAULT 0,
    override_reason      TEXT,
    configured_date      TEXT NOT NULL,
    configured_by        TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- SEEMP PART III
-- ============================================================

CREATE TABLE IF NOT EXISTS seemp_measures (
    measure_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    assessment_year      INTEGER NOT NULL,
    measure_type         TEXT NOT NULL,
    measure_description  TEXT NOT NULL,
    implementation_date  TEXT,
    estimated_fuel_saving_mt REAL,
    actual_fuel_saving_mt    REAL,
    status               TEXT DEFAULT 'planned',
    verified             INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS seemp_reports (
    report_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    assessment_year      INTEGER NOT NULL,
    baseline_co2_mt      REAL,
    current_co2_mt       REAL,
    improvement_pct      REAL,
    dcs_report_data      TEXT,
    submission_status    TEXT DEFAULT 'draft',
    submitted_date       TEXT,
    verified_date        TEXT,
    verifier             TEXT,
    created_at           TEXT DEFAULT (datetime('now')),
    UNIQUE(vessel_id, assessment_year)
);

-- ============================================================
-- EGR DATA
-- ============================================================

CREATE TABLE IF NOT EXISTS egr_data (
    egr_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    egr_rate_pct         REAL,
    egr_bypass_monitoring REAL,
    water_treatment_health REAL,
    cylinder_bypass_flow REAL,
    nox_reduction_pct    REAL,
    scavenge_air_pressure_bar REAL,
    exhaust_temp_after_egr REAL,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- IGC CODE COMPLIANCE
-- ============================================================

CREATE TABLE IF NOT EXISTS igc_compliance_log (
    igc_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    tank_id              INTEGER REFERENCES vessel_tanks(tank_id),
    record_timestamp     TEXT NOT NULL,
    pressure_bar         REAL,
    temperature_k        REAL,
    design_pressure_bar  REAL,
    design_temperature_k REAL,
    pressure_status      TEXT DEFAULT 'normal',
    temperature_status   TEXT DEFAULT 'normal',
    alert_level          TEXT DEFAULT 'none',
    alert_message        TEXT,
    relief_valve_status  TEXT DEFAULT 'closed',
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- CERTIFICATE TRACKING (Enhanced)
-- ============================================================

CREATE TABLE IF NOT EXISTS certificate_expiry_log (
    log_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    cert_id              INTEGER REFERENCES certificates(cert_id),
    cert_type            TEXT NOT NULL,
    cert_number          TEXT,
    expiry_date          TEXT NOT NULL,
    days_remaining       INTEGER,
    alert_90_sent        INTEGER DEFAULT 0,
    alert_30_sent        INTEGER DEFAULT 0,
    alert_expired        INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- EU ETS SURRENDER TRACKING
-- ============================================================

CREATE TABLE IF NOT EXISTS eu_ets_surrender (
    surrender_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    compliance_year      INTEGER NOT NULL,
    total_allocated_mt   REAL,
    total_surrendered_mt REAL,
    balance_mt           REAL,
    eua_price_eur        REAL,
    total_cost_eur       REAL,
    surrender_deadline   TEXT,
    status               TEXT DEFAULT 'pending',
    created_at           TEXT DEFAULT (datetime('now')),
    UNIQUE(vessel_id, compliance_year)
);
"""


PG_SCHEMA_SQL = """
-- PostgreSQL schema for LNG Fleet Performance Management System

CREATE TABLE IF NOT EXISTS vessels (
    vessel_id            SERIAL PRIMARY KEY,
    imo_number           TEXT UNIQUE NOT NULL,
    vessel_name          TEXT NOT NULL,
    vessel_type          TEXT NOT NULL DEFAULT 'LNG Carrier',
    flag_state           TEXT NOT NULL,
    classification_society TEXT,
    gross_tonnage        DOUBLE PRECISION,
    deadweight_tonnage   DOUBLE PRECISION,
    cargo_capacity_m3    DOUBLE PRECISION,
    number_of_tanks      INTEGER DEFAULT 4,
    propulsion_type      TEXT NOT NULL DEFAULT 'ME-GI',
    engine_manufacturer  TEXT,
    engine_model         TEXT,
    engine_mcr_kw        DOUBLE PRECISION,
    service_speed_kn     DOUBLE PRECISION,
    design_speed_kn      DOUBLE PRECISION,
    eexi_value           DOUBLE PRECISION,
    eedi_value           DOUBLE PRECISION,
    cii_reference_value  DOUBLE PRECISION,
    year_of_build        INTEGER,
    ice_class            TEXT,
    scrubber_equipped    INTEGER DEFAULT 0,
    reliquefaction_plant INTEGER DEFAULT 0,
    shaft_power_meter    INTEGER DEFAULT 1,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text,
    updated_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS vessel_tanks (
    tank_id              SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    tank_name            TEXT NOT NULL,
    tank_position        TEXT,
    capacity_m3          DOUBLE PRECISION NOT NULL,
    design_pressure_bar  DOUBLE PRECISION,
    design_temperature_k DOUBLE PRECISION,
    insulation_type      TEXT DEFAULT 'membrane',
    sensor_count         INTEGER DEFAULT 12,
    UNIQUE(vessel_id, tank_name)
);

CREATE TABLE IF NOT EXISTS voyages (
    voyage_id            SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    voyage_number        TEXT NOT NULL,
    charterer            TEXT,
    load_port            TEXT NOT NULL,
    discharge_port       TEXT NOT NULL,
    cargo_quantity_mt    DOUBLE PRECISION,
    cargo_type           TEXT DEFAULT 'LNG',
    planned_departure    TEXT,
    actual_departure     TEXT,
    planned_arrival      TEXT,
    actual_arrival       TEXT,
    status               TEXT DEFAULT 'planned',
    route_type           TEXT DEFAULT 'weather_optimized',
    total_distance_nm    DOUBLE PRECISION,
    total_fuel_hfo_mt    DOUBLE PRECISION DEFAULT 0,
    total_fuel_vlsfo_mt  DOUBLE PRECISION DEFAULT 0,
    total_fuel_ulsfo_mt  DOUBLE PRECISION DEFAULT 0,
    total_fuel_mgo_mt    DOUBLE PRECISION DEFAULT 0,
    total_fuel_lng_mt    DOUBLE PRECISION DEFAULT 0,
    total_bog_mt         DOUBLE PRECISION DEFAULT 0,
    co2_total_mt         DOUBLE PRECISION,
    cii_voyage_value     DOUBLE PRECISION,
    eca_time_hours       DOUBLE PRECISION DEFAULT 0,
    eu_ets_applicable    INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text,
    updated_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text,
    UNIQUE(vessel_id, voyage_number)
);

CREATE TABLE IF NOT EXISTS voyage_waypoints (
    waypoint_id          SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    sequence_num         INTEGER NOT NULL,
    latitude             DOUBLE PRECISION NOT NULL,
    longitude            DOUBLE PRECISION NOT NULL,
    waypoint_name        TEXT,
    eta_utc              TEXT,
    ata_utc              TEXT,
    speed_planned_kn     DOUBLE PRECISION,
    speed_actual_kn      DOUBLE PRECISION,
    course_deg           DOUBLE PRECISION,
    in_eca               INTEGER DEFAULT 0,
    eca_zone_name        TEXT,
    water_depth_m        DOUBLE PRECISION,
    weather_hs_m         DOUBLE PRECISION,
    weather_tp_s         DOUBLE PRECISION,
    weather_direction_deg DOUBLE PRECISION,
    wind_speed_kn        DOUBLE PRECISION,
    wind_direction_deg   DOUBLE PRECISION,
    current_speed_kn     DOUBLE PRECISION,
    current_direction_deg DOUBLE PRECISION,
    fuel_consumption_mt  DOUBLE PRECISION,
    shaft_power_kw       DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS cargo_records (
    cargo_id             SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    tank_id              INTEGER NOT NULL REFERENCES vessel_tanks(tank_id),
    record_timestamp     TEXT NOT NULL,
    cargo_level_pct      DOUBLE PRECISION,
    cargo_volume_m3      DOUBLE PRECISION,
    cargo_mass_mt        DOUBLE PRECISION,
    cargo_temperature_k  DOUBLE PRECISION,
    cargo_pressure_bar   DOUBLE PRECISION,
    cargo_composition_methane DOUBLE PRECISION DEFAULT 0.87,
    cargo_composition_ethane DOUBLE PRECISION DEFAULT 0.08,
    cargo_composition_propane DOUBLE PRECISION DEFAULT 0.03,
    cargo_composition_butane DOUBLE PRECISION DEFAULT 0.01,
    cargo_composition_nitrogen DOUBLE PRECISION DEFAULT 0.01,
    bog_generation_rate_kg_h DOUBLE PRECISION,
    tank_top_temp_k      DOUBLE PRECISION,
    tank_mid_temp_k      DOUBLE PRECISION,
    tank_bottom_temp_k   DOUBLE PRECISION,
    stratification_index DOUBLE PRECISION,
    rollover_risk_level  TEXT DEFAULT 'low',
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS bor_daily_summary (
    bor_id               SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    summary_date         TEXT NOT NULL,
    avg_bor_pct_day      DOUBLE PRECISION,
    measured_bor_pct_day DOUBLE PRECISION,
    energy_balance_bor   DOUBLE PRECISION,
    bog_to_engine_mt     DOUBLE PRECISION DEFAULT 0,
    bog_to_reliquefaction_mt DOUBLE PRECISION DEFAULT 0,
    bog_to_gcu_mt        DOUBLE PRECISION DEFAULT 0,
    reliquefaction_power_kw DOUBLE PRECISION,
    reliquefaction_cop   DOUBLE PRECISION,
    tank_avg_temp_k      DOUBLE PRECISION,
    sea_water_temp_k     DOUBLE PRECISION,
    ambient_temp_k       DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS engine_performance (
    engine_id            SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    engine_mode          TEXT DEFAULT 'gas',
    engine_speed_rpm     DOUBLE PRECISION,
    shaft_power_kw       DOUBLE PRECISION,
    mcr_pct              DOUBLE PRECISION,
    sfoc_actual_g_kwh    DOUBLE PRECISION,
    sfoc_reference_g_kwh DOUBLE PRECISION,
    sfoc_delta           DOUBLE PRECISION,
    thermal_efficiency_pct DOUBLE PRECISION,
    cylinder_pmax_bar    DOUBLE PRECISION,
    cylinder_pcomp_bar   DOUBLE PRECISION,
    exhaust_temp_cyl_avg DOUBLE PRECISION,
    turbocharger_speed_rpm DOUBLE PRECISION,
    turbocharger_surge_margin DOUBLE PRECISION,
    scavenge_air_temp_c  DOUBLE PRECISION,
    scavenge_air_pressure_bar DOUBLE PRECISION,
    fuel_injection_timing_deg DOUBLE PRECISION,
    pilot_fuel_pct       DOUBLE PRECISION,
    gas_admission_valve_timing DOUBLE PRECISION,
    methane_slip_g_kwh   DOUBLE PRECISION,
    specific_bog_consumption DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS engine_cylinder_data (
    cyl_id               SERIAL PRIMARY KEY,
    engine_perf_id       INTEGER NOT NULL REFERENCES engine_performance(engine_id),
    cylinder_number      INTEGER NOT NULL,
    pmax_bar             DOUBLE PRECISION,
    pcomp_bar            DOUBLE PRECISION,
    exhaust_temp_c       DOUBLE PRECISION,
    fuel_pressure_bar    DOUBLE PRECISION,
    deviation_pmax_pct   DOUBLE PRECISION,
    deviation_exhaust_pct DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS auxiliary_engines (
    aux_id               SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    aux_engine_number    INTEGER DEFAULT 1,
    load_kw              DOUBLE PRECISION,
    load_pct             DOUBLE PRECISION,
    sfoc_g_kwh           DOUBLE PRECISION,
    fuel_type            TEXT DEFAULT 'VLSFO',
    running_hours        DOUBLE PRECISION,
    exhaust_temp_c       DOUBLE PRECISION,
    oil_pressure_bar     DOUBLE PRECISION,
    coolant_temp_c       DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS hull_performance (
    hull_id              SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    record_date          TEXT NOT NULL,
    speed_kn             DOUBLE PRECISION,
    shaft_power_kw       DOUBLE PRECISION,
    wind_speed_kn        DOUBLE PRECISION,
    wind_direction_deg   DOUBLE PRECISION,
    current_speed_kn     DOUBLE PRECISION,
    current_direction_deg DOUBLE PRECISION,
    sea_state            INTEGER,
    water_temp_k         DOUBLE PRECISION,
    water_depth_m        DOUBLE PRECISION,
    displacement_mt      DOUBLE PRECISION,
    draft_fwd_m          DOUBLE PRECISION,
    draft_aft_m          DOUBLE PRECISION,
    trim_m               DOUBLE PRECISION,
    reference_power_kw   DOUBLE PRECISION,
    power_deviation_pct  DOUBLE PRECISION,
    friction_coeff_delta DOUBLE PRECISION,
    equivalent_roughness_mm DOUBLE PRECISION,
    fouling_level        TEXT DEFAULT 'clean',
    qpc_trending         DOUBLE PRECISION,
    hull_cleaning_due    INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS cii_assessment (
    cii_id               SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    assessment_year      INTEGER NOT NULL,
    assessment_date      TEXT NOT NULL,
    annual_co2_mt        DOUBLE PRECISION,
    annual_cargo_mt_nm   DOUBLE PRECISION,
    cii_calculated       DOUBLE PRECISION,
    cii_required         DOUBLE PRECISION,
    cii_rating           TEXT,
    rating_boundary_a    DOUBLE PRECISION,
    rating_boundary_b    DOUBLE PRECISION,
    rating_boundary_c    DOUBLE PRECISION,
    rating_boundary_d    DOUBLE PRECISION,
    projected_year_end_cii DOUBLE PRECISION,
    projected_rating     TEXT,
    distance_sailed_nm   DOUBLE PRECISION,
    cargo_carried_mt     DOUBLE PRECISION,
    port_time_hours      DOUBLE PRECISION,
    sea_time_hours       DOUBLE PRECISION,
    fuel_hfo_mt          DOUBLE PRECISION,
    fuel_vlsfo_mt        DOUBLE PRECISION,
    fuel_ulsfo_mt        DOUBLE PRECISION,
    fuel_mgo_mt          DOUBLE PRECISION,
    fuel_lng_mt          DOUBLE PRECISION,
    bog_consumed_mt      DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS eu_ets_records (
    ets_id               SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_type          TEXT NOT NULL,
    eu_port_call         TEXT,
    voyage_leg_from      TEXT,
    voyage_leg_to        TEXT,
    emission_factor_mt   DOUBLE PRECISION,
    emissions_mt_co2     DOUBLE PRECISION,
    allocation_pct       DOUBLE PRECISION,
    allocated_emissions_mt DOUBLE PRECISION,
    eu_allowance_cost_eur DOUBLE PRECISION,
    verification_status  TEXT DEFAULT 'pending',
    verification_body    TEXT,
    surrender_deadline   TEXT,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS fueleu_records (
    fueleu_id            SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_date          TEXT NOT NULL,
    fuel_type            TEXT NOT NULL,
    fuel_mass_mt         DOUBLE PRECISION,
    energy_mj            DOUBLE PRECISION,
    ghg_wtw_co2e_mt      DOUBLE PRECISION,
    ghg_intensity_g_mj   DOUBLE PRECISION,
    reference_value_g_mj DOUBLE PRECISION DEFAULT 91.16,
    compliance_balance   DOUBLE PRECISION,
    penalty_cost_eur     DOUBLE PRECISION DEFAULT 0,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS emissions_log (
    emission_id          SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    position_lat         DOUBLE PRECISION,
    position_lon         DOUBLE PRECISION,
    in_eca               INTEGER DEFAULT 0,
    eca_zone_name        TEXT,
    fuel_type            TEXT NOT NULL,
    fuel_consumption_mt_h DOUBLE PRECISION,
    co2_emissions_kg_h   DOUBLE PRECISION,
    sox_emissions_kg_h   DOUBLE PRECISION,
    nox_emissions_kg_h   DOUBLE PRECISION,
    ch4_emissions_kg_h   DOUBLE PRECISION,
    pm_emissions_kg_h    DOUBLE PRECISION,
    co2e_wtw_kg_h        DOUBLE PRECISION,
    sox_limit_ppm        DOUBLE PRECISION,
    nox_limit_g_kwh      DOUBLE PRECISION,
    compliance_status    TEXT DEFAULT 'compliant',
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS eca_events (
    event_id             SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    voyage_id            INTEGER REFERENCES voyages(voyage_id),
    event_type           TEXT NOT NULL,
    eca_zone_name        TEXT,
    event_timestamp      TEXT NOT NULL,
    position_lat         DOUBLE PRECISION,
    position_lon         DOUBLE PRECISION,
    fuel_type_before     TEXT,
    fuel_type_after      TEXT,
    sox_before_ppm       DOUBLE PRECISION,
    sox_after_ppm        DOUBLE PRECISION,
    nox_compliant        INTEGER DEFAULT 1,
    distance_to_eca_nm   DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS fuel_switch_log (
    switch_id            SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    voyage_id            INTEGER REFERENCES voyages(voyage_id),
    switch_timestamp     TEXT NOT NULL,
    position_lat         DOUBLE PRECISION,
    position_lon         DOUBLE PRECISION,
    fuel_type_from       TEXT NOT NULL,
    fuel_type_to         TEXT NOT NULL,
    fuel_quantity_from_mt DOUBLE PRECISION,
    fuel_quantity_to_mt  DOUBLE PRECISION,
    sulfur_content_from  DOUBLE PRECISION,
    sulfur_content_to    DOUBLE PRECISION,
    reason               TEXT,
    completion_pct       DOUBLE PRECISION DEFAULT 100,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS charter_party (
    cp_id                SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    charterer            TEXT NOT NULL,
    charter_type         TEXT DEFAULT 'voyage',
    speed_warranted_kn   DOUBLE PRECISION,
    consumption_warranted_mt_day DOUBLE PRECISION,
    consumption_tolerance_pct DOUBLE PRECISION DEFAULT 3.0,
    bor_warranted_pct_day DOUBLE PRECISION,
    bor_tolerance_pct    DOUBLE PRECISION DEFAULT 1.5,
    sea_margin_pct       DOUBLE PRECISION DEFAULT 15.0,
    weather_exclusion_beaufort INTEGER DEFAULT 6,
    off_hire_rate_usd_day DOUBLE PRECISION,
    performance_warranty  TEXT,
    contract_start       TEXT,
    contract_end         TEXT,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS charter_performance (
    perf_id              SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    cp_id                INTEGER REFERENCES charter_party(cp_id),
    record_date          TEXT NOT NULL,
    speed_actual_kn      DOUBLE PRECISION,
    speed_warranted_kn   DOUBLE PRECISION,
    speed_weather_corrected_kn DOUBLE PRECISION,
    consumption_actual_mt DOUBLE PRECISION,
    consumption_warranted_mt DOUBLE PRECISION,
    consumption_weather_corrected_mt DOUBLE PRECISION,
    consumption_deviation_pct DOUBLE PRECISION,
    speed_deviation_pct  DOUBLE PRECISION,
    off_hire_hours       DOUBLE PRECISION DEFAULT 0,
    off_hire_reason      TEXT,
    weather_exclusion_applied INTEGER DEFAULT 0,
    wind_speed_kn        DOUBLE PRECISION,
    sea_state_beaufort   INTEGER,
    performance_compliant INTEGER DEFAULT 1,
    discrepancy_alert    INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS off_hire_events (
    off_hire_id          SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    event_start          TEXT NOT NULL,
    event_end            TEXT,
    event_type           TEXT NOT NULL,
    cause                TEXT,
    speed_loss_kn        DOUBLE PRECISION,
    duration_hours       DOUBLE PRECISION,
    weather_factor       DOUBLE PRECISION DEFAULT 0,
    net_off_hire_hours   DOUBLE PRECISION,
    cost_usd             DOUBLE PRECISION,
    evidence_hash        TEXT,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS digital_twin_state (
    twin_id              SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    record_timestamp     TEXT NOT NULL,
    engine_health_index  DOUBLE PRECISION,
    hull_health_index    DOUBLE PRECISION,
    bog_system_health    DOUBLE PRECISION,
    predicted_rul_engine_days DOUBLE PRECISION,
    predicted_rul_hull_days  DOUBLE PRECISION,
    anomaly_score        DOUBLE PRECISION,
    anomalies_detected   TEXT,
    model_version        TEXT,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS maintenance_events (
    maintenance_id       SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    component            TEXT NOT NULL,
    component_serial     TEXT,
    maintenance_type     TEXT NOT NULL,
    priority             TEXT DEFAULT 'medium',
    scheduled_date       TEXT,
    completed_date       TEXT,
    actual_cost_usd      DOUBLE PRECISION,
    estimated_cost_usd   DOUBLE PRECISION,
    work_description     TEXT,
    port_of_repair       TEXT,
    status               TEXT DEFAULT 'planned',
    predicted_rul_days   DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS predictive_alerts (
    alert_id             SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    alert_timestamp      TEXT NOT NULL,
    alert_type           TEXT NOT NULL,
    severity             TEXT NOT NULL,
    component            TEXT NOT NULL,
    description          TEXT NOT NULL,
    predicted_failure_days DOUBLE PRECISION,
    confidence_pct       DOUBLE PRECISION,
    recommended_action   TEXT,
    acknowledged         INTEGER DEFAULT 0,
    resolved             INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS scrubber_data (
    scrubber_id          SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    mode                 TEXT DEFAULT 'open_loop',
    wash_water_ph        DOUBLE PRECISION,
    wash_water_pah       DOUBLE PRECISION,
    wash_water_turbidity DOUBLE PRECISION,
    sox_inlet_ppm        DOUBLE PRECISION,
    sox_outlet_ppm       DOUBLE PRECISION,
    removal_efficiency   DOUBLE PRECISION,
    wash_water_flow_m3_h DOUBLE PRECISION,
    power_consumption_kw DOUBLE PRECISION,
    naoh_consumption_kg_h DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS scr_data (
    scr_id               SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    nox_inlet_ppm        DOUBLE PRECISION,
    nox_outlet_ppm       DOUBLE PRECISION,
    denox_efficiency_pct DOUBLE PRECISION,
    catalyst_bed_temp_c  DOUBLE PRECISION,
    urea_consumption_kg_h DOUBLE PRECISION,
    ammonia_slip_ppm     DOUBLE PRECISION,
    exhaust_temp_in_c    DOUBLE PRECISION,
    exhaust_temp_out_c   DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS weather_data (
    weather_id           SERIAL PRIMARY KEY,
    voyage_id            INTEGER REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    position_lat         DOUBLE PRECISION,
    position_lon         DOUBLE PRECISION,
    source               TEXT DEFAULT 'GFS',
    wind_speed_kn        DOUBLE PRECISION,
    wind_direction_deg   DOUBLE PRECISION,
    significant_wave_height_m DOUBLE PRECISION,
    wave_period_s        DOUBLE PRECISION,
    wave_direction_deg   DOUBLE PRECISION,
    sea_water_temp_k     DOUBLE PRECISION,
    air_temp_k           DOUBLE PRECISION,
    air_pressure_hpa     DOUBLE PRECISION,
    visibility_nm        DOUBLE PRECISION,
    precipitation_mm_h   DOUBLE PRECISION,
    current_speed_kn     DOUBLE PRECISION,
    current_direction_deg DOUBLE PRECISION,
    sea_ice_coverage_pct DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    reading_id           SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    sensor_type          TEXT NOT NULL,
    sensor_name          TEXT NOT NULL,
    value                DOUBLE PRECISION NOT NULL,
    unit                 TEXT,
    quality_flag         TEXT DEFAULT 'good',
    record_timestamp     TEXT NOT NULL,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE INDEX IF NOT EXISTS idx_sensor_vessel_time
    ON sensor_readings(vessel_id, record_timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_type_time
    ON sensor_readings(sensor_type, record_timestamp);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id               SERIAL PRIMARY KEY,
    table_name           TEXT NOT NULL,
    record_id            INTEGER NOT NULL,
    action               TEXT NOT NULL,
    data_hash            TEXT NOT NULL,
    timestamp_utc        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_table_record
    ON audit_log(table_name, record_id);

CREATE TABLE IF NOT EXISTS certificates (
    cert_id              SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    cert_type            TEXT NOT NULL,
    cert_number          TEXT,
    issuing_authority    TEXT,
    issue_date           TEXT,
    expiry_date          TEXT,
    status               TEXT DEFAULT 'valid',
    document_path        TEXT,
    notes                TEXT,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS bunkering_records (
    bunker_id            SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    voyage_id            INTEGER REFERENCES voyages(voyage_id),
    bunkering_date       TEXT NOT NULL,
    port                 TEXT NOT NULL,
    fuel_type            TEXT NOT NULL,
    quantity_mt          DOUBLE PRECISION NOT NULL,
    sulfur_content_pct   DOUBLE PRECISION,
    carbon_content_pct   DOUBLE PRECISION,
    density_kg_m3        DOUBLE PRECISION,
    calorific_value_mj_kg DOUBLE PRECISION,
    supplier             TEXT,
    bdn_number           TEXT,
    unit_price_usd       DOUBLE PRECISION,
    total_cost_usd       DOUBLE PRECISION,
    verified             INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS eca_zones (
    zone_id              SERIAL PRIMARY KEY,
    zone_name            TEXT UNIQUE NOT NULL,
    zone_type            TEXT NOT NULL,
    sox_limit_pct        DOUBLE PRECISION,
    nox_tier             TEXT,
    effective_date       TEXT,
    boundary_polygon     TEXT,
    status               TEXT DEFAULT 'active',
    notes                TEXT
);

CREATE TABLE IF NOT EXISTS cii_rating_boundaries (
    boundary_id          SERIAL PRIMARY KEY,
    ship_type            TEXT NOT NULL,
    year                 INTEGER NOT NULL,
    boundary_a           DOUBLE PRECISION,
    boundary_b           DOUBLE PRECISION,
    boundary_c           DOUBLE PRECISION,
    boundary_d           DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text,
    UNIQUE(ship_type, year)
);

CREATE TABLE IF NOT EXISTS eexi_assessment (
    assessment_id        SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    assessment_year      INTEGER NOT NULL,
    attained_eexi        DOUBLE PRECISION NOT NULL,
    required_eexi        DOUBLE PRECISION NOT NULL,
    compliant            INTEGER NOT NULL,
    epl_power_limit_pct  DOUBLE PRECISION DEFAULT 100,
    reference_speed_kn   DOUBLE PRECISION,
    reference_power_kw   DOUBLE PRECISION,
    ship_type_code       TEXT DEFAULT 'LNG',
    calculation_method   TEXT DEFAULT 'ISO_20414',
    notes                TEXT,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text,
    UNIQUE(vessel_id, assessment_year)
);

CREATE TABLE IF NOT EXISTS epl_config (
    epl_id               SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    eca_zone_name        TEXT,
    power_limit_pct      DOUBLE PRECISION NOT NULL DEFAULT 100,
    override_active      INTEGER DEFAULT 0,
    override_reason      TEXT,
    configured_date      TEXT NOT NULL,
    configured_by        TEXT,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS seemp_measures (
    measure_id           SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    assessment_year      INTEGER NOT NULL,
    measure_type         TEXT NOT NULL,
    measure_description  TEXT NOT NULL,
    implementation_date  TEXT,
    estimated_fuel_saving_mt DOUBLE PRECISION,
    actual_fuel_saving_mt    DOUBLE PRECISION,
    status               TEXT DEFAULT 'planned',
    verified             INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS seemp_reports (
    report_id            SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    assessment_year      INTEGER NOT NULL,
    baseline_co2_mt      DOUBLE PRECISION,
    current_co2_mt       DOUBLE PRECISION,
    improvement_pct      DOUBLE PRECISION,
    dcs_report_data      TEXT,
    submission_status    TEXT DEFAULT 'draft',
    submitted_date       TEXT,
    verified_date        TEXT,
    verifier             TEXT,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text,
    UNIQUE(vessel_id, assessment_year)
);

CREATE TABLE IF NOT EXISTS egr_data (
    egr_id               SERIAL PRIMARY KEY,
    voyage_id            INTEGER NOT NULL REFERENCES voyages(voyage_id),
    record_timestamp     TEXT NOT NULL,
    egr_rate_pct         DOUBLE PRECISION,
    egr_bypass_monitoring DOUBLE PRECISION,
    water_treatment_health DOUBLE PRECISION,
    cylinder_bypass_flow DOUBLE PRECISION,
    nox_reduction_pct    DOUBLE PRECISION,
    scavenge_air_pressure_bar DOUBLE PRECISION,
    exhaust_temp_after_egr DOUBLE PRECISION,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS igc_compliance_log (
    igc_id               SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    tank_id              INTEGER REFERENCES vessel_tanks(tank_id),
    record_timestamp     TEXT NOT NULL,
    pressure_bar         DOUBLE PRECISION,
    temperature_k        DOUBLE PRECISION,
    design_pressure_bar  DOUBLE PRECISION,
    design_temperature_k DOUBLE PRECISION,
    pressure_status      TEXT DEFAULT 'normal',
    temperature_status   TEXT DEFAULT 'normal',
    alert_level          TEXT DEFAULT 'none',
    alert_message        TEXT,
    relief_valve_status  TEXT DEFAULT 'closed',
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS certificate_expiry_log (
    log_id               SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    cert_id              INTEGER REFERENCES certificates(cert_id),
    cert_type            TEXT NOT NULL,
    cert_number          TEXT,
    expiry_date          TEXT NOT NULL,
    days_remaining       INTEGER,
    alert_90_sent        INTEGER DEFAULT 0,
    alert_30_sent        INTEGER DEFAULT 0,
    alert_expired        INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text
);

CREATE TABLE IF NOT EXISTS eu_ets_surrender (
    surrender_id         SERIAL PRIMARY KEY,
    vessel_id            INTEGER NOT NULL REFERENCES vessels(vessel_id),
    compliance_year      INTEGER NOT NULL,
    total_allocated_mt   DOUBLE PRECISION,
    total_surrendered_mt DOUBLE PRECISION,
    balance_mt           DOUBLE PRECISION,
    eua_price_eur        DOUBLE PRECISION,
    total_cost_eur       DOUBLE PRECISION,
    surrender_deadline   TEXT,
    status               TEXT DEFAULT 'pending',
    created_at           TEXT DEFAULT (NOW() AT TIME ZONE 'UTC')::text,
    UNIQUE(vessel_id, compliance_year)
);
"""


def create_all_tables(db_manager):
    if USING_POSTGRES:
        conn = db_manager._pg_conn
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        count = cur.fetchone()[0]
        if count < 30:
            cur.execute(PG_SCHEMA_SQL)
            print("[schema] Created PostgreSQL tables")
        else:
            print(f"[schema] PostgreSQL already has {count} tables — skipping")
    else:
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing = {row[0] for row in cursor.fetchall()}
            conn.executescript(SCHEMA_SQL)
