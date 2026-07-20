package models

import (
	"time"

	"github.com/google/uuid"
)

type VoyageStatus string

const (
	VoyageStatusPlanned    VoyageStatus = "planned"
	VoyageStatusInProgress VoyageStatus = "in_progress"
	VoyageStatusCompleted  VoyageStatus = "completed"
	VoyageStatusCancelled  VoyageStatus = "cancelled"
)

type Voyage struct {
	ID               uuid.UUID    `json:"id"`
	VesselID         uuid.UUID    `json:"vessel_id"`
	VoyageNumber     string       `json:"voyage_number"`
	CharterPartyRef  string       `json:"charter_party_ref,omitempty"`
	DeparturePort    string       `json:"departure_port"`
	ArrivalPort      string       `json:"arrival_port"`
	DepartureTime    time.Time    `json:"departure_time"`
	ArrivalTime      *time.Time   `json:"arrival_time,omitempty"`
	DistanceNM       float64      `json:"distance_nm"`
	Status           VoyageStatus `json:"status"`
	AvgSpeedKN       *float64     `json:"avg_speed_kn,omitempty"`
	FuelConsumptionTonne *float64 `json:"fuel_consumption_tonne,omitempty"`
	BOGRate          *float64     `json:"bog_rate,omitempty"`
	CargoLoadedCBM   *float64     `json:"cargo_loaded_cbm,omitempty"`
	CargoDischargedCBM *float64   `json:"cargo_discharged_cbm,omitempty"`
	Charterer         string       `json:"charterer,omitempty"`
	CreatedAt        time.Time    `json:"created_at"`
	UpdatedAt        time.Time    `json:"updated_at"`
}
