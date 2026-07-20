package models

import (
	"time"

	"github.com/google/uuid"
)

type Vessel struct {
	ID               uuid.UUID `json:"id"`
	IMONumber        int       `json:"imo_number"`
	Name             string    `json:"name"`
	Flag             string    `json:"flag"`
	VesselType       string    `json:"vessel_type"`
	CargoCapacityM3  float64   `json:"cargo_capacity_m3"`
	YearBuilt        int       `json:"build_year"`
	EngineType       string    `json:"engine_type"`
	TankType         string    `json:"lng_tank_type"`
	DesignDraftM     float64   `json:"design_draft_m"`
	DesignSpeedKN    float64   `json:"design_speed_kn"`
	EEDIAttained     *float64  `json:"eedi_attained,omitempty"`
	EEXIRequired     *float64  `json:"eexi_required,omitempty"`
	EEXIAttained     *float64  `json:"eexi_attained,omitempty"`
	ScrubberInstalled bool    `json:"scrubber_installed"`
	SCRInstalled     bool      `json:"scr_installed"`
	EGRInstalled     bool      `json:"egr_installed"`
	ShorePowerCapable bool    `json:"shore_power_capable"`
	CreatedAt        time.Time `json:"created_at"`
	UpdatedAt        time.Time `json:"updated_at"`
}
