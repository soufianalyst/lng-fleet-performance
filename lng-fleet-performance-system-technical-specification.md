# LNG Carrier Fleet Performance Management System
## Technical Specification Document

**Version**: 1.0  
**Date**: July 2026  
**Classification**: Confidential  

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Module 1: Voyage Optimization](#2-module-1-voyage-optimization)
3. [Module 2: Cargo & Boil-Off Rate Monitoring](#3-module-2-cargo--boil-off-rate-monitoring)
4. [Module 3: Hull & Machinery Performance](#4-module-3-hull--machinery-performance)
5. [Module 4: CII & Regulatory Compliance](#5-module-4-cii--regulatory-compliance)
6. [Module 5: Digital Twin & Predictive Maintenance](#6-module-5-digital-twin--predictive-maintenance)
7. [Module 6: Charter Party Verification](#7-module-6-charter-party-verification)
8. [Module 7: ECA Zone Optimization & Emissions Management](#8-module-7-eca-zone-optimization--emissions-management)
9. [Data Architecture & Edge Processing](#9-data-architecture--edge-processing)
10. [Regulatory Compliance Matrix](#10-regulatory-compliance-matrix)
11. [Appendices](#11-appendices)

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
+------------------------------------------------------------------+
|                         CLOUD TIER                               |
|  +------------------+  +---------------+  +-------------------+  |
|  | Data Lake        |  | ML Inference  |  | API Gateway       |  |
|  | (Time-Series DB) |  | Pipeline      |  | (REST/WebSocket)  |  |
|  +------------------+  +---------------+  +-------------------+  |
|  +------------------+  +---------------+  +-------------------+  |
|  | Digital Twin     |  | Compliance   |  | Reporting &       |  |
|  | Engine           |  | Engine        |  | Dashboards        |  |
|  +------------------+  +---------------+  +-------------------+  |
+------------------------------------------------------------------+
          ^                        ^
          | Satellite (L-band/Ku)  | Compressed telemetry
          v                        v
+------------------------------------------------------------------+
|                       EDGE TIER (Onboard)                         |
|  +------------------+  +---------------+  +-------------------+  |
|  | Edge Gateway     |  | Real-Time     |  | Local Dashboard  |  |
|  | (Linux ARM64)    |  | Analytics     |  | (Web UI)         |  |
|  +------------------+  +---------------+  +-------------------+  |
|  +------------------+  +---------------+                        |
|  | Data Buffer &    |  | Config Sync   |                        |
|  | Compression      |  | Agent         |                        |
|  +------------------+  +---------------+                        |
+------------------------------------------------------------------+
          ^                        ^
          | Modbus TCP / OPC-UA    | NMEA 2000 / IEC 61162
          v                        v
+------------------------------------------------------------------+
|                    SENSOR & SYSTEMS TIER                          |
|  +------------------+  +---------------+  +-------------------+  |
|  | Engine Control   |  | Integrated   |  | Cargo Control     |  |
|  | System (ME-GI/   |  | Automation   |  | System (CCS)      |  |
|  | X-DF)            |  | System (IAS) |  |                   |  |
|  +------------------+  +---------------+  +-------------------+  |
|  +------------------+  +---------------+  +-------------------+  |
|  | Weather Sensor   |  | GPS / AIS    |  | Tank Level / Temp |  |
|  | (Anemometer/Baro)|  | Gyro/Log     |  | Pressure Sensors  |  |
|  +------------------+  +---------------+  +-------------------+  |
|  +------------------+  +---------------+  +-------------------+  |
|  | Shaft Power      |  | Flow Meters  |  | Emissions        |  |
|  | Meter (Torque)   |  | (Fuel/Gas)   |  | Analyzer (CEMS)  |  |
|  +------------------+  +---------------+  +-------------------+  |
+------------------------------------------------------------------+
```

### 1.2 Communication Protocol Stack

| Layer | Protocol | Transport | Notes |
|---|---|---|---|
| Sensor Acquisition | Modbus TCP, OPC-UA, IEC 61162-450 | Ethernet | Polling interval: 1s |
| Vessel Systems | NMEA 2000, IEC 61924 (INS) | CAN Bus / Ethernet | Navigation bridge |
| Edge Processing | MQTT (Sparkplug B) | TCP/IP | Internal edge bus |
| Shore Transmission | MQTT over HTTPS, WebSocket Secure | TCP/TLS | Zstd compression |
| Satellite | VSAT (Ku/Ka), L-band (Iridium Certus) | TCP/UDP | Dynamic QoS |
| API | REST (OpenAPI 3.1), gRPC | HTTPS/HTTP2 | Shore-to-shore |

### 1.3 Edge Processing Philosophy

**"Process at the edge, transmit intelligence"** — 80% of analytics executed onboard. Only exceptions, aggregated KPIs, and compressed time-series windows transmitted via satellite.

| Data Type | Edge Processing | Satellite Transmission |
|---|---|---|
| Engine parameters (1Hz) | Real-time anomaly detection | 5-min aggregates + anomalies |
| BOR (continuous) | Running hourly average | Hourly BOR + tank status |
| Voyage events | Immediate classification | Real-time (event-driven) |
| CII calculation | Daily computation | Daily summary |
| Raw sensor logs | Local buffer (30 days) | On-demand / WiFi at port |

---

## 2. Module 1: Voyage Optimization

### 2.1 Purpose

Minimize fuel consumption and GHG emissions while ensuring JIT (Just-In-Time) arrival, ECA compliance, and cargo condition preservation for LNG carriers.

### 2.2 Functional Components

#### 2.2.1 Weather Routing Engine

- **Inputs**: GFS 16-day global forecast (NOAA, free/open), ECMWF IFS HRES via Open-Meteo (open-data tier), wave spectra (Hs, Tp, Dir) from WW3 / CMEMS, ocean currents from HYCOM + CMEMS, sea ice from OSISAF
- **Algorithms**: Isochrone method with A* graph search on 0.25° × 0.25° grid
- **Cost Function**: Weighted sum of fuel consumption, ETA penalty, cargo BOR penalty, ECA compliance cost
- **Constraints**: Maximum significant wave height (Hs ≤ 4.5m for LNG loading), ice navigation limits, canal transit scheduling (Panama/Suez), ECA zone boundaries
- **Output**: Optimized waypoint sequence with speed profile, fuel estimate, ETA confidence interval

#### 2.2.2 Speed & Power Optimization

- **Model**: Holtrop-Mennen resistance + Wageningen B-series propeller + engine-specific SFOC map
- **Real-Time Calibration**: Kalman filter adjusting resistance coefficients based on observed speed-power relationship
- **Trim Optimization**: Computational fluid dynamics (CFD) lookup table by draft/trim/water depth — recommends optimal trim within ballast/loaded condition
- **Shaft Power Limitation (EPL/EPL+)**: Virtual engine power limiter override for EEXI compliance, configurable per ECA zone

#### 2.2.3 JIT Arrival Module

- **Integration** with AIS data + port community systems (Port CDM / PCS)
- **Dynamic ETA Recalculation** every 6 hours or when deviation > 2 hours
- **Virtual Arrival** functionality: logs weather-adjusted speed profile for charter party performance analysis
- **Berth Window Negotiation**: API to port terminal system for slot optimization

#### 2.2.4 ECA Zone Compliance Engine

See **[Module 7: ECA Zone Optimization & Emissions Management](#8-module-7-eca-zone-optimization--emissions-management)**

### 2.3 Technical Specifications

| Parameter | Specification |
|---|---|
| Route computation latency | < 30s (edge), < 5s (cloud) |
| Forecast data refresh | 4x daily (GFS 0.25° + WW3 at 00/06/12/18Z), 2x daily (ECMWF IFS open-data via Open-Meteo), daily (CMEMS ocean currents/SST) |
| Speed profile resolution | 0.1 kn increments |
| Fuel prediction accuracy | ±2% within 48h, ±5% within 7 days |
| Grid resolution | 0.25° global, 0.05° in ECAs |
| Re-routing trigger | Weather deviation > 20% or ETA slip > 3h |

### 2.4 Regulatory Compliance Features

| Regulation | Feature |
|---|---|
| **EEXI** | Shaft power limitation (EPL) enforcement during voyage planning |
| **CII** | Speed optimization targeting required annual CII rating |
| **EU ETS** | Fuel burn allocation by EU/EEA port calls for allowance calculation |
| **FuelEU Maritime** | Well-to-wake GHG intensity tracking per voyage leg |
| **MARPOL Annex VI** | ECA fuel switch timing optimization (minimize non-compliance window) |
| **MRV/DCS** | Verified fuel consumption data feed for regulatory submission |

---

## 3. Module 2: Cargo & Boil-Off Rate Monitoring

### 3.1 Purpose

Real-time monitoring and optimization of cargo condition, BOR minimization, reliquefaction plant efficiency, and tank stratification management for LNG cargoes.

### 3.2 Functional Components

#### 3.2.1 Real-Time BOR Measurement

- **Sensors**: 4-wire PT100/PT500 tank temperature arrays (top/middle/bottom), radar/laser tank level gauges, tank pressure transmitters, gas flow meters on BOG line
- **Calculation Method**:
  - Direct measurement: BOG flow meter on GCU/reliquefaction inlet
  - Energy balance: `BOR = (Q_in - Q_out + W_compression) / (m_lng * LHV)`
  - Redundant: Tank pressure rise rate during closed-hold test
- **Accuracy**: ±1.5% of measured BOR value
- **Sampling Rate**: 1 Hz (LNG carriers with custody transfer meters), 0.1 Hz (standard)

#### 3.2.2 Tank Stratification & Rollover Prevention

- **Model**: 1D finite difference heat transfer model for each tank (nodal division: 20 nodes vertically)
- **Stratification Index**: Temperature gradient ∂T/∂z normalized by tank height
- **Alert Threshold**: Stratification index > 0.5°C/m triggers recirculation recommendation
- **Rollover Prediction**: Rayleigh number + density inversion detection (LNG composition tracking via Raman spectroscopy data)

#### 3.2.3 Reliquefaction Plant Performance

- **Key Metrics**: Specific power consumption (kW/kg BOG reliquefied), thermal efficiency vs. Carnot, liquefaction rate vs. BOG generation rate
- **Compressor Monitoring**: Polytropic efficiency, surge margin, seal gas consumption
- **Optimization Advisory**: Recommends optimal number of compressors online, intercooler temperature setpoints, and condenser pressure

#### 3.2.4 Cargo Condition Forecasting

- **Propagation Model**: 4D (3D spatial + time) prediction of tank conditions for remaining voyage
- **End-of-Voyage Prediction**: Estimated cargo temperature, pressure, BOG volume at discharge port
- **Cargo Quality Tracking**: Methane number, Wobbe index, GCV prediction during voyage

### 3.3 Technical Specifications

| Parameter | Specification |
|---|---|
| BOR measurement uncertainty | < ±1.5% |
| Temperature sensor accuracy | ±0.1°C (PT100 Class A) |
| Level measurement accuracy | ±0.5 mm (radar gauge) |
| Stratification alert lead time | > 12 hours before rollover risk |
| Reliquefaction COP tracking | ±2% accuracy |
| Cargo condition forecast horizon | Full remaining voyage duration |

### 3.4 Regulatory Compliance Features

| Regulation | Feature |
|---|---|
| **MARPOL Annex VI** | BOG management fuel saving = direct GHG reduction |
| **IGC Code** | Tank pressure/temperature within design limits at all times |
| **SIGTTO** | Custody transfer accuracy compliance |
| **EU ETS** | BOG burned as fuel — tracked as emissions (distinct from cargo loss) |
| **CII** | BOG utilization efficiency as operational metric |
| **MRV** | BOG consumption metering for verified emissions report |

---

## 4. Module 3: Hull & Machinery Performance

### 4.1 Purpose

Continuous monitoring of propulsion system efficiency, hull condition, auxiliary systems, and early detection of performance degradation.

### 4.2 Functional Components

#### 4.2.1 Main Engine Performance (ME-GI / X-DF / Steam Turbine)

- **Parameters**: Cylinder pressure (Pmax, Pcomp), exhaust gas temperature per cylinder, turbocharger speed/surge margin, fuel injection timing, gas admission valve behavior
- **Dual-Fuel Tracking**: Gas mode vs. diesel mode fuel consumption curves, pilot fuel percentage, methane slip estimation
- **Methane Slip Measurement**: Tunable diode laser absorption spectroscopy (TDLAS) on exhaust stack (accuracy ±5%)
- **Performance Indices**:
  - `ΔSFOC` = Actual SFOC – Reference SFOC (ISO conditions normalized)
  - `Engine Δη` = (Actual thermal efficiency / Design thermal efficiency) × 100%
  - Compression pressure deviation per cylinder

#### 4.2.2 Boil-Off Gas Utilization System

- **GCU (Gas Combustion Unit)**: Burn rate tracking, % of BOG sent to GCU vs. engines/reliquefaction
- **Optimization**: Maximize BOG to engines (displacing HFO/LSFO), minimize GCU waste
- **Methane Slip**: Combined engine + GCU methane emission estimate

#### 4.2.3 Hull Fouling Detection

- **Method**: Statistical analysis of speed-power residuals vs. reference model
- **Fouling Metric**: `ΔCF = CF_current - CF_clean` (friction coefficient increase)
- **Propulsion Efficiency**: QPC (Quasi-Propulsive Coefficient) trending
- **Roughness Estimation**: Equivalent sand roughness (k_s) derived from frictional resistance deviation
- **Cleaning Recommendation**: When ΔCF > 15% or propulsion efficiency loss > 5%

#### 4.2.4 Auxiliary Systems

- **Aux Engine Load**: Load profile optimization for port vs. sea, PTO/PTH management
- **Boiler/Heat Recovery**: Steam production vs. demand efficiency
- **HVAC & Accommodation**: Energy consumption monitoring (target: < 50 kW per person-day)
- **Ballast System**: Ballast pump efficiency, ballast optimization for trim

#### 4.2.5 Shaft Power Measurement

- **Method**: Strain gauge telemetry system on intermediate shaft
- **Accuracy**: ±0.5% of rated torque
- **Output**: Shaft power (kW), specific fuel oil consumption (g/kWh), specific BOG consumption

### 4.3 Technical Specifications

| Parameter | Specification |
|---|---|
| Cylinder pressure measurement (if installed) | ±0.5% FS at 250 bar |
| Exhaust gas temperature accuracy | ±2°C |
| Methane slip measurement accuracy | ±5% (TDLAS), ±10% (estimated) |
| Shaft power accuracy | ±0.5% |
| Hull condition trend period | Rolling 30-day window |
| Fouling detection sensitivity | > 2% change in frictional resistance |

### 4.4 Regulatory Compliance Features

| Regulation | Feature |
|---|---|
| **EEXI** | Shaft power limitation (EPL) compliance check |
| **CII** | Engine efficiency contribution to operational carbon intensity |
| **MARPOL Annex VI** | NOx technical code compliance (engine tuning) |
| **EU ETS** | Aux engine fuel burn included in total vessel allowance |
| **SEEMP Part III** | Data collection for enhanced ship energy efficiency management plan |
| **FuelEU Maritime** | Methane slip reduction targets — on-board slip tracking |

---

## 5. Module 4: CII & Regulatory Compliance

### 5.1 Purpose

End-to-end compliance management for IMO Carbon Intensity Indicator (CII), EU Emissions Trading System (EU ETS), FuelEU Maritime, SEEMP, and MRV/DCS reporting obligations.

### 5.2 Functional Components

#### 5.2.1 CII Calculator & Forecaster

- **IMO CII Calculation** (MEPC.352(78)):
  ```
  CII_calculated = Annual CO₂ / (Annual Transport Work)
  Transport Work = (Cargo carried × Distance sailed)
  ```
  - Distance correction: Port time exclusion per MEPC specification
  - Cargo correction: LNG cargo mass from tank level + temperature + composition
- **Rating Boundaries**: Uploaded annually per IMO resolutions (A-E rating)
- **Forecasting Module**: Project year-end CII rating based on current trajectory — recommends speed adjustments or voyage selection changes
- **What-If Simulator**: Optimize remaining year trading pattern to achieve required CII rating

#### 5.2.2 EU ETS Allowance Manager

- **Geofencing**: EU/EEA port calls and voyages defined per EU ETS Directive 2023/959
- **Emissions Allocation**:
  - 100% of emissions for intra-EU voyages
  - 50% of emissions for voyages departing from or arriving to EU/EEA
  - 100% of emissions at EU/EEA berth
- **MRV Verification Feed**: Direct data pipeline to approved MRV verifier (DNV, Lloyd's, Bureau Veritas)
- **Allowance Forecasting**: Forward curve-based budgeting of EUA purchases
- **Compliance Dashboard**: Surrender deadline tracking, penalty risk assessment

#### 5.2.3 FuelEU Maritime Compliance

- **GHG Intensity Calculation (Well-to-Wake)**:
  ```
  GHG Intensity = (Well-to-Wake CO₂e) / (Total Energy Used)
  ```
  - CO₂e = CO₂ + CH₄ × GWP₂₀ (82.5) + N₂O × GWP₂₀ (273)
- **Reference Value**: 91.16 gCO₂e/MJ (2025 baseline)
- **Reduction Trajectory**: -2% (2025), -6% (2030), -14.5% (2035), -31% (2040), -62% (2045), -80% (2050)
- **Banking & Borrowing**: Compliance balance tracking and multi-year averaging
- **Onboard Penalty Estimator**: USD/mtVLSFOe non-compliance cost calculation

#### 5.2.4 SEEMP Part III Compliance

- **Data Collection**: Automated feed of fuel consumption, distance, cargo carried
- **Improvement Measures**: Tracking of implemented measures (ESCs, hull cleaning, weather routing)
- **Annual Reporting**: Template generation for IMO DCS (IMO Ship Fuel Oil Consumption Database)

#### 5.2.5 EU MRV Reporting

- **Voyage-Level Data**: Automated collection per EU MRV regulation (Reg. 2015/757)
- **Emissions Report**: Annual structured data per implementing regulation template
- **Document of Compliance**: Tracking of MRV DOC issuance and validity

### 5.3 Technical Specifications

| Parameter | Specification |
|---|---|
| CII calculation frequency | Daily (rolling annual) |
| EU ETS data granularity | Per-port call + per-voyage |
| FuelEU GHG intensity | Per-bunkering batch (well-to-wake) |
| MRV verification readiness | Full data export for verifier |
| Compliance risk alerts | Real-time (CII rating drift, allowance shortfall) |
| Regulatory update cadence | Push within 48h of IMO/EU publication |

### 5.4 ECA Zone Compliance Matrix

| ECA Zone | Applicable From | SOx Limit | NOx Limit | Technology Required |
|---|---|---|---|---|
| Baltic Sea SECA | 2010 (SOx), 2021 (NOx Tier III) | 0.10% S | Tier III | EGR/SCR + LSFO/VLSFO/MeOH |
| North Sea SECA | 2010 (SOx), 2021 (NOx Tier III) | 0.10% S | Tier III | EGR/SCR + LSFO |
| North American ECA | 2012 (SOx), 2016 (NOx Tier III) | 0.10% S | Tier III | SCR + ULSFO |
| US Caribbean Sea ECA | 2014 (SOx), 2016 (NOx Tier III) | 0.10% S | Tier III | SCR + ULSFO |
| Mediterranean Sea ECA (SOx) | 1 May 2025 | 0.10% S | — | LSFO/VLSFO/biofuel |
| Mediterranean Sea ECA (NOx Tier III) | 1 Jan 2028 (est.) | — | Tier III | SCR/EGR |
| Norwegian Sea NOx Fund | Ongoing | — | Tier I+ | NOx Fund payments |
| Red Sea SOx ECA (proposed) | 2027 (projected) | 0.10% S | — | LSFO |

---

## 6. Module 5: Digital Twin & Predictive Maintenance

### 6.1 Purpose

Physics-informed digital twin of each vessel enabling what-if simulations, degradation forecasting, and condition-based maintenance scheduling.

### 6.2 Functional Components

#### 6.2.1 Physics-Based Engine Model

- **Type**: 0D/1D thermo-fluid dynamic model of dual-fuel engine cycle
- **Sub-Models**:
  - Scavenge air system (compressor map, intercooler efficiency)
  - Combustion chamber (Wiebe function with DF-specific burn rates)
  - Gas admission valve dynamics
  - Turbocharger matching
  - Exhaust gas system (wastegate, EGR, SCR backpressure)
- **Calibration**: Online parameter estimation using Gaussian process regression
- **Applications**: Virtual sensor for unmeasured parameters, performance benchmark against design, fault injection testing

#### 6.2.2 Hull & Propeller Degradation Model

- **Hull Roughness Growth**: Semi-empirical model (Townsin, 1993) calibrated with observed speed-power trends
- **Propeller Roughness**: Added roughness model for coating degradation
- **Wake Field Effect**: CFD lookup table for hull-propeller interaction changes with fouling
- **Cavitation Detection**: Broadband vibration analysis on shaft bearings

#### 6.2.3 BOG System Digital Twin

- **Tank Thermal Model**: 3D FEM reduced-order model (SVD-POD reduction) of membrane tank heat ingress
- **BOG Generation**: Real-time comparison of expected vs. actual BOR
- **Insulation Health Index**: Derived from BOR trend vs. sea temperature, tank fill level, and age
- **Reliquefaction Plant**: Thermodynamic cycle model for performance deviation analysis

#### 6.2.4 Predictive Maintenance Engine

- **Approach**: Hybrid (physics-informed ML + threshold-based alerts)
- **Algorithms**:
  - **Cylinder Wear**: LSTM sequence prediction on compression pressure trends
  - **Turbocharger Bearing**: Vibration envelope analysis + autoregressive anomaly
  - **Fuel Injection System**: Fuel pressure waveform ML classification (XGBoost)
  - **Valve Train**: Exhaust temperature deviation with gas exchange model
- **Maintenance Scheduling**: Optimization of component remaining useful life (RUL) vs. port availability vs. criticality
- **Spare Parts Prediction**: Parts consumption forecasting per vessel + fleet pooling optimization

### 6.3 Technical Specifications

| Parameter | Specification |
|---|---|
| Digital twin update frequency | 1 Hz (engine), 1 min (hull), 5 min (BOG) |
| Model prediction horizon | 30 days for RUL predictions |
| RUL prediction accuracy | ±15% for major machinery |
| Fault detection latency | < 5 minutes from onset |
| Model retraining | Daily online + weekly full retrain |
| Scenario simulation response | < 10 seconds for 7-day voyage |

### 6.4 Edge-Cloud Synchronization Strategy

```
Edge Digital Twin (Onboard):
  - Real-time state estimation
  - Local anomaly detection
  - 30-day local model cache
  - Compressed delta sync to cloud

Cloud Digital Twin (Shore):
  - Full history model
  - Fleet-wide cross-learning
  - Heavy computation tasks
  - Updated ML model distribution
```

---

## 7. Module 6: Charter Party Verification

### 7.1 Purpose

Independent verification of charter party performance clauses — speed/consumption guarantees, performance warranties, and off-hire events — with weather-adjusted analysis and dispute resolution support.

### 7.2 Functional Components

#### 7.2.1 Speed & Consumption Warranty Verification

- **Reference Correction**: ISO 15016:2015 / ISO 19030:2016 weather correction methodology
- **Key Parameters**:
  - Displacement and draft (forward/aft mean)
  - Weather factor (wind, waves, current)
  - Water depth (shallow water correction)
  - Hull condition (baseline at drydocking)
  - Sea margin (typically 15%)
- **Reporting**: Per-voyage performance report with confidence intervals
- **Discrepancy Alert**: When actual consumption exceeds warranted + weather-adjusted by > 3%

#### 7.2.2 Off-Hire & Speed Loss Claims

- **Event Logging**: Automatic detection of speed reduction events (< warranted speed)
- **Weather Exclusion**: Automated application of Beaufort scale allowance
- **Off-Hire Calculation**: Time lost × charter rate, with weather window analysis
- **Audit Trail**: Tamper-proof sensor data logging with hash chain

#### 7.2.3 BOR Warranty Verification

- **Warranty Basis**: %/day at specific cargo temperature/pressure, laden/ballast
- **Actual BOR Calculation** (per Section 3) with warranty tolerance check
- **LNG Quality Correction**: Composition effect on BOR per vapor pressure calculation
- **Ambient Condition Normalization**: Sea temperature, air temperature correction to warranty conditions

### 7.3 Technical Specifications

| Parameter | Specification |
|---|---|
| Speed measurement accuracy | ±0.1 kn (GNSS + LR) |
| Consumption measurement accuracy | ±1.5% (coriolis flow meter) |
| Weather correction standard | ISO 15016:2015 |
| Report latency | < 24 hours post-completion |
| Data immutability | SHA-256 hashing every 15 min |
| Dispute resolution package | Full data export + correction methodology documentation |

### 7.4 Regulatory & Legal Compliance

- **Evidence Admissibility**: Data logging compliant with IIMS / LMAA evidence standards
- **Data Retention**: Minimum 6 years (consistent with limitation periods for charter party claims)
- **Independent Verification**: Certifiable by DNV or Lloyd's for evidentiary purposes
- **Cross-Border Data Compliance**: GDPR (EU-flagged vessels), UK DPA, Cyprus/Singapore flag state requirements

---

## 8. Module 7: ECA Zone Optimization & Emissions Management

### 8.1 Purpose

Active compliance management across all current and upcoming Emission Control Areas, minimizing fuel cost impact while maintaining 100% regulatory compliance.

### 8.2 Functional Components

#### 8.2.1 ECA Geofencing Engine

- **Datasets**:
  - IMO ECA boundaries (WGS 84 polygons with latest amendments)
  - Port authority ECA notification zones (e.g., California ARB, Chinese DECAs)
  - EU MRV geographical scope for EU ETS
- **Spatial Logic**:
  - `d_eca = distance_to(ECA polygon, vessel_position)`
  - Pre-entry warning: `d_eca < 120 nm` (3 hours at service speed)
  - Entry/exit logging with UTC timestamp + position accuracy < 50m
- **Dynamic Updates**: Overnight push of regulatory boundary amendments via satellite

#### 8.2.2 Fuel Switch Optimization

- **Fuel Types Tracked**:
  - HFO (0.50% S max — global cap compliant with scrubber)
  - VLSFO (0.50% S)
  - ULSFO (0.10% S)
  - MGO/MDO (0.10% S)
  - LNG (dual-fuel) — near-zero SOx, 85-90% NOx reduction
  - Biofuel blends (B30, B100) — accounting for FuelEU
- **Switch Timing Algorithm**:
  - Inputs: Position, speed, fuel system flush time, fuel availability, fuel prices
  - Optimization: Minimize total fuel cost subject to compliance constraint
  - Output: Time to commence fuel switch, estimated completion position
- **Logging**: Automatic fuel switch log with IMO DCS/MRV format (fuel type, quantity, start/stop position, time)

#### 8.2.3 Scrubber Management (if equipped)

- **Wash Water Monitoring**: pH, PAH, turbidity per IMO 2021 scrubber discharge criteria
- **Compliance Scenarios**:
  - SG/EGC (Seawater/Exhaust Gas Cleaning) — open loop
  - EGCS (closed loop with NaOH/HCO₃⁻)
  - Hybrid mode switching based on port discharge regulations
- **Scrubber Bypass**: Tracking of non-compliance periods, SOx emission estimates during bypass

#### 8.2.4 NOx After-Treatment Monitoring

- **SCR (Selective Catalytic Reduction)**:
  - DeNOx efficiency (%) = `(NOx_in - NOx_out) / NOx_in × 100`
  - Catalyst bed temperature monitoring (optimal window: 300–450°C)
  - Urea/AdBlue consumption rate vs. design
  - Ammonia slip monitoring (< 10 ppm target)
- **EGR (Exhaust Gas Recirculation)**:
  - EGR rate (% of scavenge air)
  - Cylinder bypass monitoring
  - Water treatment system health

#### 8.2.5 Compliance Certificate Management

- **IAPP Certificate**: Periodic survey tracking, SOx/NOx compliance statement
- **EIAPP Certificates**: Engine-specific NOx technical code compliance
- **SEEMP Part III / IEE Certificate**: Validity tracking
- **EU ETS / MRV**: Monitoring plan approval, verification deadlines
- **US EPA VGP / e-NOAD**: US waters compliance documentation
- **California CARB**: Ocean-going vessel at-berth regulation compliance (shore power / emissions control)

#### 8.2.6 Combined Emission Forecast & Optimization

- **Multi-Constraint Optimization**:
  ```
  Minimize: Total voyage cost (fuel + EUA + FuelEU penalty)
  Subject to:
    - ECA compliance at all times
    - CII rating ≥ C (target: ≥ B)
    - FuelEU GHG intensity ≤ annual limit
    - ETA window compliance
    - Tank pressure/temperature limits
  ```
- **Solution Method**: Mixed-integer linear programming (MILP) with 15-minute time steps
- **Computation**: Cloud-based with edge-based fallback for connectivity loss

### 8.3 ECA Zone Compliance Matrix — Technical Implementation

| ECA Zone | Fuel Type | Switch Time Required | Monitoring | Reporting Requirement |
|---|---|---|---|---|
| Baltic Sea SECA | ULSFO/MGO/LNG | 1h before entry | SOx continuous via flow | Bunker delivery note (BDN) + logbook |
| North Sea SECA | ULSFO/MGO/LNG | 1h before entry | SOx continuous via flow | BDN + logbook |
| North American ECA | ULSFO/MGO/LNG | 1h before entry | SOx + NOx (Tier III) | BDN + NOx TC certificate |
| US Caribbean ECA | ULSFO/MGO/LNG | 1h before entry | SOx + NOx (Tier III) | BDN + NOx TC certificate |
| Mediterranean SOx (2025) | VLSFO/ULSFO/LNG | 1h before entry | SOx continuous | BDN + EU MRV fuel report |
| Mediterranean NOx (2028) | LNG + SCR | 1h before entry | NOx continuous | NOx TC cert + Tier III log |
| California (CARB) | MGO/ULSFO or shore power | At berth | Shore power connection log | CARB e-NOAD |
| China DECAs | 0.50% S → 0.10% S by 2028 | At berth + 1h before entry | SOx via fuel oil sample | China MRV |

### 8.4 Emissions Monitoring Hardware Interface

| Pollutant | Measurement Method | Sensor Type | Accuracy | Certification |
|---|---|---|---|---|
| SOx | Fuel sulfur balance (primary), CEMS (optional) | Fuel flow + S content | ±5% | MARPOL Annex VI |
| NOx | CEMS (NDIR/CLD) or NOx Tech Code calculation | Heated chemiluminescence | ±5% (< 500 ppm), ±10% (> 500 ppm) | MARPOL NOx Tech Code |
| CO₂ | Fuel-based (IPCC method) | Fuel flow × EF | ±3% | EU MRV, IMO DCS |
| CH₄ (methane slip) | TDLAS (tunable diode laser) | Laser absorption (1.65 μm) | ±5% | — |
| PM (particulate) | Opacity / gravimetric (if required) | Smoke meter | ±10% | EPA Method 5/17 |
| CO₂e (well-to-wake) | FuelEU methodology + upstream factors | Calculation from fuel batch | ±5% | FuelEU Maritime |

---

## 9. Data Architecture & Edge Processing

### 9.1 Edge Gateway Specifications

| Component | Specification |
|---|---|
| **Processor** | ARM Cortex-A72 (quad-core, 1.8 GHz) or equivalent |
| **Memory** | 8 GB RAM minimum, 16 GB recommended |
| **Storage** | 256 GB industrial SSD (SLC), hot-swappable |
| **OS** | Linux RT kernel (Yocto-based or Ubuntu Core) |
| **Temperature Range** | -15°C to +55°C (engine room rated) |
| **Power Consumption** | < 50W |
| **MTBF** | > 100,000 hours |
| **Network** | Dual Ethernet (redundant), 4G/5G, Iridium Certus |

### 9.2 Data Flow and Processing Pipeline

```
SENSOR LAYER (1Hz)
    |
    v
DATA ACQUISITION SERVICE (Modbus/OPC-UA)
    |  Validation, interpolation, quality flags
    |
    v
EDGE BUFFER (InfluxDB Edge / SQLite)
    |  30-day rolling buffer
    |
    +-------> REAL-TIME ANALYTICS (Node.js / Rust)
    |           |  Anomaly detection, alerting
    |           v
    |         Local Dashboard (Grafana)
    |
    +-------> BATCH ANALYTICS (Python / NumPy)
    |           |  CII calculation, BOR averaging, daily summary
    |           v
    |         Store (parquet + compressed)
    |
    +-------> SATELLITE TRANSMISSION MANAGER
                |  MQTT with QoS 2, Zstd compression
                v
              Cloud Ingest (Kafka)
```

### 9.3 Satellite Communication Optimization

| Strategy | Bandwidth Saving | Latency |
|---|---|---|
| Zstd compression (level 10) | 60-70% | +50ms |
| Delta encoding (only changed values) | 80-90% | +20ms |
| Aggregation (5-min window) | 95% | Batch |
| Event-driven transmission (exceptions only) | 98% | < 5s |
| WiFi sync at port (bulk transfer) | 100% off satellite | N/A |

### 9.4 Cloud Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| **Time-Series DB** | TimescaleDB / InfluxDB Cloud | Sensor data (10-year retention) |
| **Data Lake** | S3 / GCS / Azure Blob | Parquet files, ML artifacts |
| **Stream Processing** | Apache Kafka + Flink | Real-time telemetry pipeline |
| **ML Platform** | MLflow + PyTorch / XGBoost | Model training + deployment |
| **API Gateway** | Kong / AWS API Gateway | REST/gRPC endpoints |
| **Dashboard** | Grafana + Metabase | Operational + compliance |
| **Digital Twin** | Unity / Unreal Engine (3D) + custom solver | Visualization + simulation |

### 9.5 Data Retention Policy

| Data Type | Edge Retention | Cloud Retention | Compression |
|---|---|---|---|
| 1Hz raw sensor (all channels) | 30 days | 90 days | Delta encoding |
| 5-min aggregates | 365 days | 3 years | Zstd |
| Hourly averages | Permanent | Permanent | Standard |
| Voyage records | Permanent | Permanent | Parquet |
| CII/compliance data | 6 years | 6 years | Parquet + encryption |
| Charter party data | 6 years | 6 years | Tamper-proof (hash chain) |

---

## 10. Regulatory Compliance Matrix

### 10.1 International Regulations (IMO)

| Regulation | Effective | Key Requirement | Module |
|---|---|---|---|
| **MARPOL Annex VI** — Global Sulfur Cap | 1 Jan 2020 | Fuel S ≤ 0.50% outside ECA | M1, M7 |
| **MARPOL Annex VI** — ECA SOx | 2010-2025 (per zone) | Fuel S ≤ 0.10% in ECA | M7 |
| **MARPOL Annex VI** — ECA NOx Tier III | 2016-2028 (per zone) | NOx ≤ 3.4 g/kWh (n < 130) | M3, M7 |
| **EEXI** (MEPC.333(76)) | 1 Jan 2023 | Attained EEXI ≤ Required EEXI | M1, M3 |
| **CII** (MEPC.352(78)) | 1 Jan 2023 | Annual CII rating A-E | M4 |
| **IMO DCS** (MEPC.282(70)) | 1 Jan 2019 | Annual fuel consumption reporting | M4 |
| **SEEMP Part III** (MEPC.346(78)) | 1 Jan 2023 | Ship-specific improvement plan | M4 |
| **IGC Code** (MSC.370(93)) | 1 Jul 2016 | LNG cargo containment integrity | M2 |
| **IGF Code** (MSC.391(95)) | 1 Jan 2017 | Gas-fueled engine safety | M3 |

### 10.2 European Union Regulations

| Regulation | Effective | Key Requirement | Module |
|---|---|---|---|
| **EU MRV** (Reg. 2015/757) | 1 Jan 2018 | CO₂ monitoring + reporting per voyage | M4 |
| **EU ETS** (Dir. 2023/959) | 1 Jan 2024 | Purchase + surrender of EUAs | M4 |
| **FuelEU Maritime** (Reg. 2023/1805) | 1 Jan 2025 | Well-to-wake GHG intensity reduction | M4, M7 |
| **EU Alternative Fuels Infrastructure (AFIR)** | 2025-2030 | Shore power at TEN-T ports | M7 |
| **EU Taxonomy Regulation** | 2022 | Green shipping classification | M4 |

### 10.3 United States Regulations

| Regulation | Authority | Key Requirement | Module |
|---|---|---|---|
| **Clean Air Act — NECA** | US EPA | Tier III NOx in N. American ECA | M7 |
| **CARB At-Berth Reg** | California ARB | Shore power or control tech > 80% | M7 |
| **Vessel General Permit (VGP)** | US EPA | Ballast water + scrubber discharge | M3, M7 |
| **USCG Gas Fuel Regulations** | USCG | LNG fuel system compliance | M3 |

### 10.4 Other National / Regional

| Regulation | Region | Key Requirement | Module |
|---|---|---|---|
| **China DECA** (MOT 2020) | China coastal | 0.50% S → 0.10% S by 2028 | M7 |
| **Singapore MPA** | Singapore | Digital bunkering (mass flow meters) | M2, M3 |
| **Turkey ECA** | Marmara Sea | 0.10% S | M7 |
| **Canada VECC** | Canada | GHG + air pollutant reporting | M4 |
| **Norway NOx Fund** | Norway | NOx tax/environmental agreement | M7 |

### 10.5 Future Regulation Readiness

| Regulation | Expected | Feature Prepared | Module |
|---|---|---|---|
| **IMO Mid-Term Measures** | 2027-2030 | GHG pricing / fuel standard | M4, M7 |
| **IMO ZEV Target** | 2050 (net-zero) | Zero-emission ready tracking | M4, M5 |
| **EU ETS Extension** | 2026+ | Methane + N₂O inclusion | M4 |
| **Mediterranean NOx ECA** | 2028 | NOx Tier III in Mediterranean | M7 |
| **FuelEU Maritime — non-ETS routes** | 2025+ | ECS routes from EU | M4 |
| **Revised IMO GHG Strategy** | 2027 (mid-cycle review) | Strengthened CII reduction rates | M4 |
| **Red Sea SOx ECA** | 2027 (projected) | 0.10% S in Red Sea | M7 |

---

## 11. Appendices

### A. Glossary

| Term | Definition |
|---|---|
| BOG | Boil-Off Gas — LNG vapor generated by heat ingress |
| BOR | Boil-Off Rate — percentage of cargo volume vaporized per day |
| CII | Carbon Intensity Indicator |
| ECA | Emission Control Area |
| EEDI | Energy Efficiency Design Index |
| EEXI | Energy Efficiency Existing Ship Index |
| EPLa | Environmental Performance (P) Limitation arrangement |
| EUA | European Union Allowance (carbon credit) |
| GCU | Gas Combustion Unit |
| JIT | Just-In-Time arrival |
| ME-GI | Main Engine — Gas Injection (MAN DF) |
| MRV | Monitoring, Reporting, Verification |
| RUL | Remaining Useful Life |
| SFOC | Specific Fuel Oil Consumption (g/kWh) |
| TDLAS | Tunable Diode Laser Absorption Spectroscopy |
| X-DF | Otto-cycle dual-fuel engine (WinGD) |
| ZEV | Zero-Emission Vehicle/Vessel |

### B. Performance KPIs

| KPI | Target | Measurement Method | Module |
|---|---|---|---|
| Fuel savings vs. baseline | 3-8% | Weather-adjusted voyage comparison | M1 |
| BOR reduction | 8-12% | Normalized to 50% tank level, 0°C SWT | M2 |
| CII rating target | ≥ B (A preferred) | IMO MEPC.352 | M4 |
| Charter party dispute reduction | 50% | Claims cost before/after | M6 |
| Unplanned maintenance reduction | 30% | Equipment downtime events | M5 |
| ECA compliance | 100% | Audit events / total entries | M7 |
| EU ETS cost optimization | 5-10% | EUA vs. compliance actual | M4 |
| Methane slip reduction | 20-30% | Absolute slip (g/kWh) | M3, M7 |

### C. Interface Standards

| Interface | Standard | Data Content |
|---|---|---|
| Engine Control (ECS) | Modbus TCP / OPC-UA | Speed, power, temperatures, pressures |
| Cargo Control (CCS) | Modbus RTU/TCP | Tank levels, temperatures, pressures, BOG flow |
| Navigation | IEC 61162-450 (NMEA) | Position, SOG, COG, heading, depth |
| Weather (open-source) | Open-Meteo API (free, aggregates GFS + ECMWF IFS + DWD ICON + WW3) | Forecast + hindcast |
| Weather (ocean) | CMEMS (Copernicus Marine, free) / HYCOM NCOM | Currents, SST, wave spectra, sea ice |
| Weather (fallback commercial) | API (MeteoGroup/DTN / Spire Weather) | Premium ensemble forecasts |
| AIS | AIS (NMEA) + AIS API | Vessel traffic, port data |
| Port Community | S2P (Port Activity) / IMO FAL | Berth windows, port services |
| Corporate ERP | REST / Webhook | Invoicing, procurement, HR |
| Class Society API | DNV Veracity / LR RINA | Survey status, certificates |
| Regulatory API | IMO GISIS + EU MRV | Compliance data submission |

### D. Security & Data Integrity

- **Encryption at Rest**: AES-256 on edge and cloud storage
- **Encryption in Transit**: TLS 1.3 (all external interfaces)
- **Tamper Evidence**: SHA-256 audit chain for charter party data (15-minute intervals)
- **Access Control**: RBAC with LDAP/OIDC federation, 2FA required for shore access
- **GDPR Compliance**: Data segregation, right to deletion, data processing records
- **Penetration Testing**: Annual + after every major release (ISO 27001 scope)
- **Vessel Access Control**: Hardware security module (HSM) for edge gateway identity

### E. System Integration Points

| External System | Integration Method | Data Frequency | Criticality |
|---|---|---|---|
| Charterer's portal | REST API (OAuth 2.0) | Per-voyage | High |
| Port community (PCS) | S2P / MQTT | Real-time | Medium |
| Bunker supplier | API (BDN) | Per-bunkering | High |
| Class society | API (DNV/Lloyd's) | Daily sync | High |
| Regulatory authority | API / File upload | Annual (MRV), continuous (CII) | Critical |
| Insurance (H&M, P&I) | REST API | Per-claim | Low |
| Fleet ERP | ODBC / REST | Hourly | Medium |
| Weather provider | Open-Meteo / NOAA NOMADS / CMEMS API polling | 4x daily (GFS), 2x daily (ECMWF), daily (CMEMS) | Medium |
| EU ETS registry | API (ETS Union Registry) | Quarterly (surrender) | Critical |

---

*This document is proprietary and confidential. No part of this document may be reproduced or transmitted without prior written permission.*
