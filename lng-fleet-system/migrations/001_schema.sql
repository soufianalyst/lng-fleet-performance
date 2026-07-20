CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- VESSELS
-- ============================================================================
CREATE TABLE vessels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    imo_number INTEGER UNIQUE NOT NULL CHECK (imo_number >= 1000000 AND imo_number <= 9999999),
    name VARCHAR(100) NOT NULL,
    flag VARCHAR(3) NOT NULL,
    vessel_type VARCHAR(20) NOT NULL DEFAULT 'LNG_CARRIER',
    cargo_capacity_m3 NUMERIC(10,1) NOT NULL,
    build_year SMALLINT NOT NULL,
    engine_type VARCHAR(30) NOT NULL,
    lng_tank_type VARCHAR(20),
    design_draft_m NUMERIC(4,2),
    design_speed_kn NUMERIC(4,2),
    eedi_design NUMERIC(5,3),
    eedi_attained NUMERIC(5,3),
    eexi_required NUMERIC(5,3),
    eexi_attained NUMERIC(5,3),
    scrubber_installed BOOLEAN DEFAULT FALSE,
    scr_installed BOOLEAN DEFAULT FALSE,
    egr_installed BOOLEAN DEFAULT FALSE,
    shore_power_capable BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active',
    design_consumption_tonne_day NUMERIC(8,2),
    bor_percent NUMERIC(5,3),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- VOYAGES
-- ============================================================================
CREATE TABLE voyages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    voyage_number VARCHAR(20) NOT NULL,
    charter_party_ref VARCHAR(50),
    departure_port VARCHAR(100) NOT NULL,
    arrival_port VARCHAR(100) NOT NULL,
    departure_time TIMESTAMPTZ NOT NULL,
    arrival_time TIMESTAMPTZ,
    distance_nm NUMERIC(8,1),
    status VARCHAR(20) DEFAULT 'in_progress',
    avg_speed_kn NUMERIC(4,2),
    fuel_consumption_tonne NUMERIC(10,3),
    bog_rate NUMERIC(6,4),
    cargo_loaded_cbm NUMERIC(10,1),
    cargo_discharged_cbm NUMERIC(10,1),
    charterer VARCHAR(100),
    cargo_laden BOOLEAN,
    cargo_quantity_m3 NUMERIC(10,1),
    total_distance_nm NUMERIC(8,1),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(vessel_id, voyage_number)
);

-- ============================================================================
-- TELEMETRY (TimescaleDB hypertable)
-- ============================================================================
CREATE TABLE telemetry (
    time TIMESTAMPTZ NOT NULL,
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    voyage_id UUID REFERENCES voyages(id),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    sog_kn NUMERIC(5,2),
    cog_deg NUMERIC(5,2),
    heading_deg NUMERIC(5,2),
    engine_speed_rpm NUMERIC(6,1),
    shaft_power_kw NUMERIC(8,1),
    sfoc_g_per_kwh NUMERIC(6,1),
    fuel_flow_t_per_day NUMERIC(8,3),
    bog_flow_t_per_day NUMERIC(8,3),
    pilot_fuel_flow_t_per_day NUMERIC(8,4),
    engine_load_pct NUMERIC(5,2),
    exhaust_temp_c NUMERIC(5,1),
    scavenge_air_pressure_bar NUMERIC(5,3),
    turbocharger_speed_rpm NUMERIC(7,1),
    fuel_type TEXT,
    fuel_sulfur_pct NUMERIC(4,3),
    methane_slip_g_per_kwh NUMERIC(6,3),
    cargo_tank_temp_c NUMERIC(4,1),
    cargo_tank_pressure_bar NUMERIC(5,3),
    cargo_tank_level_pct NUMERIC(5,2),
    cargo_tank_top_temp_c NUMERIC(4,1),
    cargo_tank_mid_temp_c NUMERIC(4,1),
    cargo_tank_bot_temp_c NUMERIC(4,1),
    bor_pct_per_day NUMERIC(6,4),
    wind_speed_kn NUMERIC(5,1),
    wind_direction_deg NUMERIC(5,1),
    wave_height_m NUMERIC(4,2),
    wave_period_s NUMERIC(4,1),
    air_temp_c NUMERIC(4,1),
    sea_temp_c NUMERIC(4,1),
    current_speed_kn NUMERIC(4,2),
    current_direction_deg NUMERIC(5,1),
    air_pressure_hpa NUMERIC(6,1),
    in_eca_zone BOOLEAN DEFAULT FALSE,
    eca_zone_name TEXT,
    scrubber_operating BOOLEAN DEFAULT FALSE,
    co2_t_per_day NUMERIC(8,3),
    nox_g_per_kwh NUMERIC(6,2),
    sox_g_per_kwh NUMERIC(6,3),
    hull_draft_fwd_m NUMERIC(4,2),
    hull_draft_aft_m NUMERIC(4,2),
    hull_trim_m NUMERIC(4,2),
    water_depth_m NUMERIC(6,1),
    quality_flag SMALLINT DEFAULT 0
);

SELECT create_hypertable('telemetry', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_telemetry_vessel_time ON telemetry(vessel_id, time DESC);

-- ============================================================================
-- CII COMPLIANCE
-- ============================================================================
CREATE TABLE cii_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    year SMALLINT NOT NULL,
    month SMALLINT,
    attained_cii NUMERIC(8,4) NOT NULL,
    required_cii NUMERIC(8,4),
    rating CHAR(1),
    distance_nm NUMERIC(8,1),
    fuel_consumption_tonne NUMERIC(10,3),
    co2_emissions_tonne NUMERIC(10,3),
    cargo_tonnes NUMERIC(10,1),
    capacity_cbm NUMERIC(10,1),
    deduction VARCHAR(20),
    eedi_value NUMERIC(5,3),
    forecast BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(vessel_id, year)
);

-- ============================================================================
-- EU ETS
-- ============================================================================
CREATE TABLE eu_ets_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    voyage_id UUID REFERENCES voyages(id),
    reporting_year SMALLINT NOT NULL,
    voyage_leg TEXT,
    co2_emitted_t NUMERIC(10,3) NOT NULL,
    co2_liable_t NUMERIC(10,3) NOT NULL,
    euas_required INTEGER,
    verification_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- FUEL EU MARITIME
-- ============================================================================
CREATE TABLE fueleu_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    voyage_id UUID REFERENCES voyages(id),
    reporting_year SMALLINT NOT NULL,
    energy_used_mj NUMERIC(14,2),
    co2_wtw_t NUMERIC(10,3),
    ch4_wtw_t NUMERIC(8,4),
    n2o_wtw_t NUMERIC(8,5),
    co2e_wtw_t NUMERIC(10,3),
    ghg_intensity_g_per_mj NUMERIC(8,4),
    compliance_balance NUMERIC(8,4)
);

-- ============================================================================
-- BOG / CARGO
-- ============================================================================
CREATE TABLE bog_records (
    recorded_at TIMESTAMPTZ NOT NULL,
    id UUID DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    voyage_id UUID REFERENCES voyages(id),
    tank_id SMALLINT NOT NULL,
    tank_level_pct NUMERIC(5,2),
    tank_temp_c NUMERIC(4,1),
    tank_pressure_bar NUMERIC(5,3),
    bor_pct_per_day NUMERIC(6,4),
    bog_flow_t_per_day NUMERIC(8,3),
    bog_to_engine_pct NUMERIC(5,2),
    bog_to_gcu_pct NUMERIC(5,2),
    bog_to_reliquefaction_pct NUMERIC(5,2),
    reliquefaction_power_kw NUMERIC(8,1),
    stratification_index NUMERIC(8,6),
    rollover_risk TEXT
);

SELECT create_hypertable('bog_records', 'recorded_at', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_bog_vessel_time ON bog_records(vessel_id, recorded_at DESC);

-- ============================================================================
-- ECA ZONE EVENTS
-- ============================================================================
CREATE TABLE eca_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    voyage_id UUID REFERENCES voyages(id),
    eca_zone_name TEXT NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    fuel_type_before VARCHAR(10),
    fuel_type_after VARCHAR(10),
    fuel_switch_completed BOOLEAN DEFAULT FALSE,
    compliance_status TEXT DEFAULT 'compliant',
    scrubber_mode TEXT,
    nox_aftertreatment_active BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- CHARTER PARTY
-- ============================================================================
CREATE TABLE charter_parties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    charterer_name VARCHAR(100) NOT NULL,
    charter_type TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    warranted_speed_kn NUMERIC(4,2) NOT NULL,
    warranted_consumption_t_per_day NUMERIC(6,3) NOT NULL,
    warranted_bor_pct_per_day NUMERIC(5,3),
    speed_tolerance_pct NUMERIC(4,1) DEFAULT 5.0,
    weather_allowance_beaufort_max SMALLINT DEFAULT 4,
    demurrage_rate_usd_per_day NUMERIC(10,2)
);

CREATE TABLE charter_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    charter_id UUID NOT NULL REFERENCES charter_parties(id),
    voyage_id UUID NOT NULL REFERENCES voyages(id),
    verified_speed_kn NUMERIC(4,2),
    verified_consumption_t_per_day NUMERIC(6,3),
    weather_correction_applied BOOLEAN DEFAULT TRUE,
    weather_adjusted_speed_kn NUMERIC(4,2),
    weather_adjusted_consumption_t_per_day NUMERIC(6,3),
    speed_compliance BOOLEAN,
    consumption_compliance BOOLEAN,
    off_hire_hours NUMERIC(6,2) DEFAULT 0,
    claim_amount_usd NUMERIC(12,2),
    hash_chain VARCHAR(64),
    verified_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ALERTS
-- ============================================================================
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    voyage_id UUID REFERENCES voyages(id),
    category VARCHAR(30),
    severity VARCHAR(10) NOT NULL CHECK (severity IN ('info','warning','critical')),
    title VARCHAR(200),
    description TEXT,
    details JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_vessel_time ON alerts(vessel_id, created_at DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity);

-- ============================================================================
-- MAINTENANCE PREDICTIONS
-- ============================================================================
CREATE TABLE maintenance_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL REFERENCES vessels(id),
    component VARCHAR(60) NOT NULL,
    parameter VARCHAR(60) NOT NULL,
    predicted_value NUMERIC(12,4),
    actual_value NUMERIC(12,4),
    deviation_pct NUMERIC(8,4),
    rul_days INTEGER,
    confidence_pct NUMERIC(4,1),
    anomaly_score NUMERIC(5,3),
    model_version VARCHAR(20),
    predicted_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- MATERIALIZED VIEW
-- ============================================================================
CREATE MATERIALIZED VIEW cii_running_annual AS
SELECT
    vessel_id,
    year,
    AVG(attained_cii) AS avg_cii,
    AVG(required_cii) AS avg_required_cii
FROM cii_records
GROUP BY vessel_id, year;

-- ============================================================================
-- TRIGGER
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER vessels_updated_at
    BEFORE UPDATE ON vessels
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER voyages_updated_at
    BEFORE UPDATE ON voyages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- ECA ZONE DEFINITIONS
-- ============================================================================
CREATE TABLE eca_zone_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(40) NOT NULL,
    zone_type TEXT NOT NULL,
    effective_date DATE NOT NULL,
    sox_limit_pct NUMERIC(4,3),
    nox_tier TEXT,
    fuel_switch_required BOOLEAN DEFAULT TRUE,
    min_lat DOUBLE PRECISION,
    max_lat DOUBLE PRECISION,
    min_lon DOUBLE PRECISION,
    max_lon DOUBLE PRECISION
);

INSERT INTO eca_zone_definitions (name, zone_type, effective_date, sox_limit_pct, nox_tier, fuel_switch_required, min_lat, max_lat, min_lon, max_lon) VALUES
('Baltic Sea SECA', 'SECA', '2010-01-01', 0.100, 'Tier III', TRUE, 53.5, 66.0, 13.0, 30.0),
('North Sea SECA', 'SECA', '2010-01-01', 0.100, 'Tier III', TRUE, 48.0, 62.0, -5.0, 9.0),
('North American ECA', 'ECA_SOx', '2012-08-01', 0.100, 'Tier III', TRUE, 25.0, 60.0, -100.0, -50.0),
('US Caribbean Sea ECA', 'ECA_SOx', '2014-01-01', 0.100, 'Tier III', TRUE, 8.0, 25.0, -90.0, -60.0),
('Mediterranean Sea SOx ECA', 'ECA_SOx', '2025-05-01', 0.100, 'Tier III', TRUE, 35.0, 46.0, -6.0, 36.0),
('California ECA (CARB)', 'CARB', '2014-01-01', 0.100, 'Tier III', TRUE, 32.0, 42.0, -125.0, -117.0);
