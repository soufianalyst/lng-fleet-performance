package models

import (
	"time"

	"github.com/google/uuid"
)

type TelemetrySource string

const (
	TelemetrySourceAIS      TelemetrySource = "ais"
	TelemetrySourceIoT      TelemetrySource = "iot"
	TelemetrySourceManual   TelemetrySource = "manual"
)

type Telemetry struct {
	ID              uuid.UUID       `json:"id"`
	VesselID        uuid.UUID       `json:"vessel_id"`
	VoyageID        *uuid.UUID      `json:"voyage_id,omitempty"`
	RecordedAt      time.Time       `json:"recorded_at"`
	Latitude        float64         `json:"latitude"`
	Longitude       float64         `json:"longitude"`
	SpeedOverGround float64         `json:"speed_over_ground_kn"`
	CourseOverGround float64        `json:"course_over_ground_deg"`
	Heading         float64         `json:"heading_deg"`
	WindSpeedMS     *float64        `json:"wind_speed_ms,omitempty"`
	WindDirectionDeg *float64       `json:"wind_direction_deg,omitempty"`
	WaveHeightM     *float64        `json:"wave_height_m,omitempty"`
	AirTemperatureC *float64        `json:"air_temperature_c,omitempty"`
	SeaTemperatureC *float64        `json:"sea_temperature_c,omitempty"`
	EngineLoadPct   *float64        `json:"engine_load_pct,omitempty"`
	FuelConsumptionRate *float64    `json:"fuel_consumption_rate_tonne_day,omitempty"`
	ME1RPMPercent   *float64        `json:"me1_rpm_percent,omitempty"`
	ME2RPMPercent   *float64        `json:"me2_rpm_percent,omitempty"`
	AuxEngineLoadKW *float64        `json:"aux_engine_load_kw,omitempty"`
	GCUConsumption  *float64        `json:"gcu_consumption_tonne_day,omitempty"`
	BOGRate         *float64        `json:"bog_rate_percent,omitempty"`
	TankLevelPct    *float64        `json:"tank_level_pct,omitempty"`
	SloshingDetected bool           `json:"sloshing_detected"`
	DraftFwdM       *float64        `json:"draft_fwd_m,omitempty"`
	DraftAftM       *float64        `json:"draft_aft_m,omitempty"`
	TrimM           *float64        `json:"trim_m,omitempty"`
	Source          TelemetrySource `json:"source"`
	IngestedAt      time.Time       `json:"ingested_at"`
}
