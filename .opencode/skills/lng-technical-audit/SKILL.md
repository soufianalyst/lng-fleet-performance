---
name: lng-technical-audit
description: "LNG carrier technical knowledge base — comprehensive reference for Chief Engineer systems (ME-GI, X-DF, FGSS, BOG, SFOC, emissions) and Vessel Master operations (navigation, cargo, charter party, stability, safety, environmental compliance). Load when auditing maritime simulation code, sensor data realism, physics models, or business logic accuracy."
---

# LNG Carrier Technical Knowledge Base

This skill provides the comprehensive technical reference for auditing LNG fleet performance software. Load this skill when reviewing any maritime-domain code, data models, API endpoints, or frontend displays.

---

## Part 1: Chief Engineer — Systems & Performance

### 1.1 LNG Carrier Propulsion Types

#### ME-GI (MAN Energy Solutions ME-GI)
- **Principle:** High-pressure gas injection (diesel cycle). Gas compressed to ~300 bar, injected directly into cylinder near TDC.
- **Key parameters:**
  - Gas mode SFOC: 165-175 g/kWh at 85% MCR
  - Pilot fuel (MGO/MDO): 3-5% of total energy in gas mode
  - Compression ratio: ~17:1
  - Max continuous rating (MCR): typically 25,000-35,000 kW for large LNG carriers
  - MEPL (Main Engine Power Limitation): Typically set to 75-85% MCR for EEXI compliance
  - Changeover time (FO→Gas): 15-30 minutes
  - Changeover time (Gas→FO): 10-20 minutes
  - Gas supply pressure: 300-350 bar (high pressure)

#### X-DF (WinGD X-DF)
- **Principle:** Low-pressure gas injection (Otto cycle). Gas at 5-6 bar injected during intake stroke.
- **Key parameters:**
  - Gas mode SFOC: 155-170 g/kWh at 85% MCR
  - Pilot fuel: ~1-3% in gas mode
  - Compression ratio: ~14:1
  - Gas supply pressure: 5-6 bar (low pressure)
  - Higher specific gas consumption than ME-GI per kWh
  - More tolerant of gas quality variation (Methane Number >80)
  - Changeover time: Similar to ME-GI

#### Key Differences Between ME-GI and X-DF
| Parameter | ME-GI | X-DF |
|-----------|-------|------|
| Gas pressure | 300+ bar | 5-6 bar |
| Combustion cycle | Diesel | Otto |
| Pilot fuel % | 3-5% | 1-3% |
| Specific gas consumption | Lower | Higher |
| Gas quality tolerance | Narrower | Wider |
| Capital cost | Lower | Higher |
| Maintenance (gas mode) | Similar | Similar |

### 1.2 Fuel Gas Supply System (FGSS)

#### LNG Properties
- **Boiling point:** -161.5°C at 1 atm (101.325 kPa)
- **Density at -163°C:** 420-450 kg/m³ (varies with composition)
- **Latent heat of vaporization:** ~510 kJ/kg
- **Specific gravity:** ~0.45 (relative to water)
- **Methane content:** 85-99% (typical cargo: 95%+)
- **Ethane content:** 1-10%
- **Nitrogen content:** 0-3%
- **Wobbe index:** 49-56 MJ/m³ (affects burner compatibility)
- **Methane number:** >80 for dual-fuel engines (resistance to knock)

#### BOG (Boil-Off Gas)
- **Generation sources:** Heat ingress through insulation, pump heat, sloshing, filling operations
- **Typical BOG rates:**
  - Voyage (modern insulation): 0.05-0.10% of cargo/day
  - Voyage (older insulation): 0.10-0.20% of cargo/day
  - Port (loading): 0.15-0.30% of cargo/day
  - Port (discharging): 0.05-0.15% of cargo/day
- **BOG composition:** Primarily methane (95%+), with traces of ethane and nitrogen
- **BOG management hierarchy:**
  1. Use as engine fuel (preferred)
  2. Reliquefaction (if available and economically justified)
  3. Use in auxiliary boilers
  4. Flare (last resort, regulatory limits)
- **BOG consumption in gas mode:** Engine consumes all BOG produced + additional LNG from cargo tanks

#### Cargo Tank Types
| Type | Design | Pressure | Temp | Typical Capacity |
|------|--------|----------|------|-----------------|
| GTT Mark III | Membrane (stainless steel) | 0.25 bar g | -163°C | 145,000-180,000 m³ |
| GTT NO96 | Membrane (Invar) | 0.25 bar g | -163°C | 145,000-180,000 m³ |
| Moss (sphere) | Self-supporting | 0.30 bar g | -163°C | 125,000-155,000 m³ |
| Type C (prismatic) | Independent | 4.5 bar g | -128°C | Variable |

#### Cargo Operations
- **Loading:** Sequential loading (1-4 cargo arms per tank), heel management, trim control
- **Discharging:** Submerged cargo pumps (typically 3 per tank, ~5,000 m³/h each)
- **Cool-down:** Maximum 5°C/hour temperature change rate (thermal stress limit)
- **Warm-up:** Slower than cool-down, typically 2-3°C/hour
- **Inerting:** N₂ purging to <2% O₂ before gas-up
- **Gas-up:** LNG vapor introduced gradually, temperature monitoring critical

### 1.3 Engine Performance Parameters

#### SFOC (Specific Fuel Oil Consumption)
- **Definition:** Fuel mass consumed per unit of energy output (g/kWh)
- **Reference conditions (ISO 3046-1):**
  - Ambient temperature: 25°C (298.15 K)
  - Atmospheric pressure: 100 kPa
  - Relative humidity: 30%
  - Cooling water temperature: 25°C
- **Correction formula:** SFOC_corrected = SFOC_measured × (1 + 0.0025 × (T_actual - 25))
  - Approximate: +1 g/kWh per 5°C deviation from 25°C
- **Typical ranges:**
  - Two-stroke ME-GI (gas mode): 165-175 g/kWh
  - Two-stroke X-DF (gas mode): 155-170 g/kWh
  - Two-stroke (fuel oil mode): 165-180 g/kWh
  - Four-stroke auxiliaries (MGO): 180-200 g/kWh
  - Four-stroke auxiliaries (LNG): 160-175 g/kWh
- **Efficiency drivers:** Load, ambient conditions, fuel quality, turbocharger condition, cylinder condition

#### Specific LNG Consumption (SLC)
- **Definition:** Mass of LNG consumed per kWh (kg/kWh)
- **Relationship to SFOC:** SLC = SFOC_LNG × (heating_value_VLSFO / heating_value_LNG)
  - VLSFO: ~42.7 MJ/kg, LNG: ~50.0 MJ/kg
  - So SLC ≈ SFOC_LNG × 0.854 (approximately)
- **Typical SLC:** 140-155 g/kWh for modern dual-fuel engines

#### Cylinder Performance
- **Pmax (Peak Firing Pressure):** Maximum pressure during combustion stroke
  - ME-GI: 900-1500 bar (gas mode lower than FO mode)
  - X-DF: 600-900 bar
- **Pcomp (Compression Pressure):** Pressure at end of compression stroke
  - Should be ~60-70% of Pmax in good condition
- **Pmean (Mean Indicated Pressure):** Average effective pressure over cycle
  - Directly proportional to power output
- **Ratios to monitor:**
  - Pmax/Pcomp: 1.2-1.4 (indicates good combustion)
  - Pmax too high: Knocking risk, injector timing issue
  - Pmax too low: Compression leak, injector problem
- **Exhaust temperature spread:** <40°C between cylinders (two-stroke)
  - >40°C spread: Indicates individual cylinder issue

#### Turbocharger Performance
- **Efficiency:** 75-82% at design point
- **Sudden efficiency drop:** Fouling, damage, or surge
- **Surge margin:** Typically 10-15% above operating point
- **Cleaning:** Water washing (online) every 200-400 hours, mechanical cleaning during overhaul

### 1.4 Emissions Factors

#### CO2 Emission Factors
| Fuel | kg CO2 / tonne fuel | kg CO2 / kWh |
|------|---------------------|--------------|
| HFO | 3,114 | 0.3207 (at 175 g/kWh SFOC) |
| VLSFO | 3,151 | 0.3245 |
| MGO | 3,206 | 0.3302 |
| LNG (as fuel) | 2,750 | 0.2838 (at 160 g/kWh) |
| LNG (cargo boil-off) | 2,750 | Same, but "free" emissions |

#### NOx Emission Factors
| Tier | Limit (g/kWh) | Typical two-stroke |
|------|---------------|-------------------|
| Tier I | 17.0 (n < 130 rpm) | 12-15 |
| Tier II | 14.4 (n < 130 rpm) | 10-13 |
| Tier III (ECAs) | 3.4 (n < 130 rpm) | 2.5-3.5 |

#### SOx Emission Factors
- Global limit: 0.50% S (mass/mass) → SOx factor: ~6.2 g SOx / kg fuel × S%
- ECA limit: 0.10% S → SOx factor: ~1.2 g SOx / kg fuel × S%
- LNG as fuel: Near-zero SOx (negligible sulfur content)

### 1.5 Hull Performance

#### Fouling Impact on Resistance
| Fouling Level | Resistance Increase | Fuel Penalty |
|---------------|-------------------|--------------|
| Light slime | 5-10% | 5-12% |
| Moderate slime/grass | 15-25% | 15-30% |
| Heavy growth | 40-60% | 50-80% |
| Barnacles/mussels | 80-120% | 100%+ |

#### Bottom Paint Types
| Type | Mechanism | Slime Removal | Hard Growth |
|------|-----------|---------------|-------------|
| Copper ablative | Biocide release | Good | Good |
| Silicone foul-release | Low surface energy | Excellent | Moderate |
| Hybrid | Combined | Very Good | Good |

#### Trim Optimization
- **Optimal trim for LNG carriers:** Typically 0.5-1.5m stern trim
- **Trim resistance:** Each 0.1m deviation from optimal = ~0.5-1% fuel penalty
- **Optimal ballast condition:** Minimum ballast consistent with stability requirements

---

## Part 2: Vessel Master — Navigation & Operations

### 2.1 Route Planning and Weather Routing

#### Distance Calculations
- **Great Circle (GC):** Shortest path on sphere. Used for ocean passages.
- **Rhumb Line (RL):** Constant bearing. Longer but simpler for plotting.
- **Composite:** GC segments connected by RL waypoints.
- **Typical distances (nautical miles):**
  - Ras Laffan → Tokyo: ~5,600 nm
  - Ras Laffan → Jiangsu: ~5,200 nm
  - Sabine Pass → Zeebrugge: ~4,800 nm
  - US Gulf → South Korea: ~8,500 nm
  - Australia → Japan: ~4,200 nm
  - Malaysia → Japan: ~2,800 nm

#### Weather Routing Principles
- **Added resistance in waves:** R_add ≈ (ρg/2) × B² × Hs² × (C_R / λ)
  - Simplified: Added power ∝ Hs² (wave height squared)
  - Rule of thumb: 1m Hs adds ~2-3% to resistance at service speed
- **Current effects:** Gulf Stream ~2-3 knots, Kuroshio ~1-2 knots. Route planning must account.
- **Optimal speed profile:** Variable speed (slow steaming in bad weather, full speed in good) saves 5-15% fuel vs constant speed
- **Storm avoidance:** 1000+ nm avoidance routes are sometimes optimal when considering fuel + time

#### Speed-Power Relationship
- **Admiralty formula:** Power ∝ Speed³ (for same displacement and conditions)
  - P1/P2 = (V1/V2)³
  - Halving speed reduces power to 1/8
- **Wind resistance:** Additional power ∝ V² (relative wind speed)
- **Current effect:** Speed over ground = Speed through water ± Current
- **Slip:** (Propeller pitch × RPM - Speed) / (Propeller pitch × RPM)
  - Typical slip: 8-15% for laden LNG carrier
  - Ballast: slip increases to 12-18%

### 2.2 Cargo Operations

#### Loading Procedure (Typical)
1. **Pre-cooling** (if cold tank): 24-48 hours, max 5°C/hour
2. **Inerting** to <2% O₂ (N₂ purging)
3. **Gas-up** with LNG vapor, gradually introducing liquid
4. **Cool-down** of cargo lines and tank (if warm)
5. **Loading** at 10,000-12,000 m³/hour per tank
6. **Heel management:** Maintain minimum heel (typically 500-1000 m³) for tank stability
7. **Final ullage and measurement**
8. **Pressurizing** cargo tanks to voyage pressure

#### Discharging Procedure
1. **Initial cool-down** of cargo lines (spray cargo)
2. **Cargo pump start-up** (submerged pumps, ~5,000 m³/hour each)
3. **Sequential discharging** per tank
4. **Boil-off management** during discharge
5. **Final pumping** (stripping pumps for heel)
6. **Tank monitoring** throughout

#### Cargo Measurement (ISO 6578)
- **Ullage:** Distance from reference point to cargo surface
- **Temperature:** Multi-point measurement (top, middle, bottom of tank)
- **Pressure:** Tank pressure in bar (typically 0.1-0.2 bar g)
- **Cargo calculation:** Volume from ullage → Mass from density at measured T/P
- **Shrinkage factor:** LNG volume change during loading/unloading (thermal contraction)

### 2.3 Charter Party Operations

#### Speed and Consumption Warranty
- **Typical warranty:** "About 19.5 knots laden / 19.0 knots ballast on about XX MT VLSFO per day"
- **"About" allowance:** Usually ±0.5 knots (industry standard)
- **Weather corrections per ISO 15016:**
  - Wind: Based on Beaufort scale, relative wind direction
  - Sea state: Based on Douglas sea scale, wave height and direction
  - Current: Set and drift relative to course
  - Hull fouling: Days since last drydocking, coating condition
  - Displacement: Laden vs ballast

#### Off-Hire Triggers
- **Mechanical breakdown:** Engine failure, steering gear failure
- **Deficiency of crew:** Insufficient qualified officers
- **Drydocking:** Scheduled and emergency
- **Strikes:** Crew or shore-side
- **Average stoppages:** Time lost due to Charterer's instructions
- **Deviation:** Unordered deviation from trading area
- **Speed deficiency:** Sustained failure to meet warranted speed
- **Consumption excess:** Sustained excess consumption above warranty
- **Key principle:** Off-hire stops the clock — Owner bears the cost

#### Laytime and Demurrage
- **Laytime:** Time allowed for loading and discharging operations
  - LNG standard: 36-72 hours per port (varies by terminal)
  - Commencement: When NOR (Notice of Readiness) tendered and accepted
  - Counting: Weather working days (WWD) or consecutive hours (SHINC)
- **Despatch:** If operations complete before laytime expires
  - Despatch rate: Usually 50% of laytime saved (half-despatch)
- **Demurrage:** If operations exceed laytime
  - Rate: Usually 125-150% of daily hire rate
  - Compensation for Owner's additional costs

#### BIMCO Charter Party Forms
- **LNGTIME (Shell):** Most common for time charters
- **LNGVOY:** For voyage charters
- **Key clauses:** Speed/consumption, off-hire, deviation, war risk, ice, sanctions

### 2.4 Stability

#### Key Concepts
- **GM (Metacentric Height):** Distance from center of gravity (G) to metacenter (M)
  - Minimum GM: 0.15m (IMO IS Code)
  - Typical operating GM: 1.5-3.0m for LNG carriers
  - Too high GM: Stiff ship, uncomfortable motion
  - Too low GM: Tender ship, risk of capsizing
- **GZ curve:** Righting lever at various angles of heel
  - Area under curve to 30° > 0.055 m·rad
  - Area under curve to 40° > 0.09 m·rad
  - Maximum GZ > 0.20 m at angle > 25°
- **Free surface effect:** Reduces effective GM by GM_fse = Σ(i × ρ_water) / Δ
  - For LNG carrier with partial cargo: Can be significant (0.5-1.0m reduction)

#### Ballast Management
- **Segregated Ballast Tanks (SBT):** Ballast never mixes with cargo or fuel
- **Ballast exchange:** Mid-ocean exchange to prevent transfer of invasive species
  - Sequential method: Pump out ballast from bottom, fill from top
  - Flow-through method: Pump through at 3× tank volume

### 2.5 Environmental Regulations

#### CII (Carbon Intensity Indicator)
- **Rating:** A (best) to E (worst)
- **AER (Annual Efficiency Ratio):** CO2 emitted / (DWT × distance sailed)
  - Unit: gCO2 / (tonne·nm)
- **LNG carrier typical rating:** B to C
- **Deterioration factor:** 1% per year (thresholds tighten)
- **Corrective action:** Required for D and E rated vessels (SEEMP Part III)

#### EEXI (Energy Efficiency Existing Ship Index)
- **Attained EEXI:** Technical efficiency = Power × Reference Speed / (Capacity × V_ref²)
- **Required EEXI:** Set by IMO, varies by ship type and size
- **Compliance route:** Main Engine Power Limitation (MEPL) is most common
  - MEPL reduces available power to meet EEXI
  - Typically 75-85% of original MCR

#### EU ETS (Emissions Trading System)
- **Inclusion:** Maritime included from 2024, phased in 2024-2026
- **Coverage:** 100% for intra-EU voyages, 50% for voyages to/from EU
- **Allowance:** EUA (EU Allowance), ~€80-100/tonne CO2
- **Surrender:** Annual, by September 30
- **LNG advantage:** Lower CO2 per kWh than HFO/VLSFO

#### FuelEU Maritime
- **GHG intensity limit:** Sets maximum GHG intensity of energy used on board
- **Compliance:**
  - Use of LNG: 0.67 × fossil GHG intensity (methane slip penalized)
  - Use of green methanol/ammonia: 0% GHG intensity
  - Shore power: 0% GHG intensity
- **Penalty:** Surcharge of €2,400 per GWh of non-compliance

#### ECA (Emission Control Areas)
- **SOx limit:** 0.10% S (mass/mass)
- **NOx limit:** Tier III (3.4 g/kWh for n < 130 rpm)
- **Major ECAs:** North Sea, Baltic, North American, US Caribbean
- **Compliance:** Switch to LSFO/MGO or use LNG (zero SOx, low NOx)

---

## Part 3: Data Validation Reference

### 3.1 Sensor Value Ranges (LNG Carrier)

| Parameter | Min | Typical | Max | Unit | Notes |
|-----------|-----|---------|-----|------|-------|
| Speed over ground | 0 | 14-20 | 22 | kn | >22 suspect, 0 at sea = off-hire |
| Engine load | 0 | 60-90 | 105 | % MCR | >100% possible briefly (overload) |
| SFOC (gas mode) | 140 | 165 | 200 | g/kWh | <140 or >200 investigate |
| SLC (gas mode) | 120 | 145 | 175 | g/kWh | Specific LNG consumption |
| BOG rate | 0.03 | 0.08-0.15 | 0.50 | % cargo/day | >0.30 in port possible |
| Cargo level | 0 | 30-95 | 100 | % | <10% = nearly empty |
| Tank pressure | 0.05 | 0.10-0.20 | 0.25 | bar g | >0.25 = PRV risk |
| Tank temperature | -165 | -163 | -155 | °C | >-155 = warming concern |
| Exhaust temp | 200 | 280-340 | 400 | °C | >380°C = overload |
| Exhaust spread | 0 | 15-30 | 60 | °C | >40 = cylinder issue |
| Scavenge air temp | 25 | 35-45 | 55 | °C | >50 = cooler fouling |
| Cooling water temp | 30 | 36-42 | 50 | °C | >45 = cooling issue |
| Cylinder Pmax | 500 | 1000-1400 | 1600 | bar | Depends on engine type |
| CO2 | 0 | 500-2000 | 5000 | tonnes/day | Depends on fuel and power |
| NOx | 0 | 5-20 | 50 | kg/day | Tier III in ECAs |
| SOx | 0 | 0-5 | 20 | kg/day | ~0 for LNG fuel |

### 3.2 Correlation Checks

| Relationship | Expected | Investigation if violated |
|-------------|----------|--------------------------|
| Speed vs Load | Load ∝ Speed³ | Non-cubic = hull/propeller issue |
| Fuel vs Load | Linear correlation | Nonlinear = engine issue |
| CO2 vs Fuel | Linear (fixed factor) | Nonlinear = wrong emission factor |
| BOG vs Cargo Level | BOG ∝ Surface area ∝ Level^0.6 | Non-correlated = insulation issue |
| Wind vs Speed | Inverse correlation | None = data quality issue |
| SFOC vs Load | U-shaped curve (best at 75-85%) | Flat = engine issue |
| Distance vs Speed | Linear (D = V × T) | Nonlinear = GPS or speed sensor issue |

### 3.3 Route Distance Validation (Approximate)

| Route | Distance (nm) | Typical Transit Time (days) |
|-------|---------------|---------------------------|
| Ras Laffan → Tokyo | 5,600 | 13-15 |
| Ras Laffan → Jiangsu | 5,200 | 12-14 |
| Ras Laffan → Dahej (India) | 1,800 | 4-5 |
| Ras Laffan → Busan | 5,800 | 13-15 |
| Sabine Pass → Zeebrugge | 4,800 | 12-14 |
| Sabine Pass → South Korea | 8,500 | 20-23 |
| Darwin → Tokyo | 3,500 | 8-10 |
| Bintulu → Incheon | 3,200 | 7-9 |
| Point Fortin → Barcelona | 4,200 | 10-12 |
| Suez Canal transit | ~120 | 12-16 hours |
| Panama Canal transit | ~50 | 8-12 hours |

### 3.4 Port Time Estimation

| Port Activity | Duration (hours) | Notes |
|---------------|------------------|-------|
| Arrival pilot boarding | 1-2 | From anchorage/sea |
| T berthing | 1-2 | Depends on terminal |
| Loading (per tank) | 4-8 | 10,000-12,000 m³/hour |
| Discharging (per tank) | 3-6 | 3 pumps × 5,000 m³/hour |
| Tank cleaning | 12-48 | If required between cargoes |
| Bunkering | 8-16 | Depends on quantity |
| Inspection/customs | 2-8 | Port state dependent |
| Total typical port stay | 24-96 | Varies widely |

---

## Part 4: Audit Checklist

When auditing code in this project, systematically check:

### Physics & Constants
- [ ] LNG density correct at operating temperature (420-450 kg/m³ at -163°C)
- [ ] BOG rate within realistic range (0.05-0.30%/day)
- [ ] SFOC values in valid range (140-200 g/kWh)
- [ ] Emission factors match IMO guidelines (CO2: 3.114 t/t HFO)
- [ ] Energy content units consistent (MJ/tonne vs MJ/kg)
- [ ] Temperature conversions correct (K = °C + 273.15)
- [ ] Speed-power relationship follows cube law

### Navigation
- [ ] Route distances within 10% of published sea distances
- [ ] Speed values realistic for LNG carrier (14-21 knots)
- [ ] Position updates consistent with speed and course
- [ ] ECA zone boundaries correct (check against known coordinates)
- [ ] Great circle calculations accurate for long routes

### Business Logic
- [ ] Charter party compliance uses ISO 15016 weather corrections
- [ ] Off-hire calculation properly distinguishes time vs event triggers
- [ ] P&L calculations account for all cost components
- [ ] CII uses correct AER formula (CO2 / DWT × distance)
- [ ] EU ETS correctly applies 50% for extra-EU voyages
- [ ] Laytime calculation uses correct weather working day conventions
- [ ] Demurrage rate correctly applied (125-150% of hire)

### Data Model
- [ ] All critical sensor fields present in telemetry schema
- [ ] Foreign keys properly reference existing records
- [ ] Index coverage for common query patterns
- [ ] No gaps in time series data (missing records)
- [ ] Data types appropriate (REAL for floats, INTEGER for counts)

### Safety
- [ ] No values that could indicate dangerous conditions presented as normal
- [ ] Alarm thresholds set at realistic levels
- [ ] Emergency parameters (fire, gas, flooding) properly modeled
- [ ] Stability calculations include free surface effect
