package models

import (
	"time"

	"github.com/google/uuid"
)

type CIIRating string

const (
	CIIRatingA CIIRating = "A"
	CIIRatingB CIIRating = "B"
	CIIRatingC CIIRating = "C"
	CIIRatingD CIIRating = "D"
	CIIRatingE CIIRating = "E"
)

type CIIDeduction string

const (
	CIIDeductionEDDI        CIIDeduction = "EDDI"
	CIIDeductionEEDI        CIIDeduction = "EEDI"
	CIIDeductionEEDIPhase2  CIIDeduction = "EEDI_Phase2"
	CIIDeductionEEDIPhase3  CIIDeduction = "EEDI_Phase3"
	CIIDeductionCIIRef      CIIDeduction = "CII_Reference"
)

type CIIRecord struct {
	ID                uuid.UUID    `json:"id"`
	VesselID          uuid.UUID    `json:"vessel_id"`
	Year              int          `json:"year"`
	AttainedCII       float64      `json:"attained_cii"`
	RequiredCII       float64      `json:"required_cii"`
	Rating            CIIRating    `json:"rating"`
	DistanceNM        float64      `json:"distance_nm"`
	FuelConsumptionTonne float64   `json:"fuel_consumption_tonne"`
	CO2EmissionsTonne float64      `json:"co2_emissions_tonne"`
	CargoTonnes       *float64     `json:"cargo_tonnes,omitempty"`
	CapacityCBM       float64      `json:"capacity_cbm"`
	Deduction         *CIIDeduction `json:"deduction,omitempty"`
	EEDIValue         *float64     `json:"eedi_value,omitempty"`
	Forecast          bool         `json:"forecast"`
	CreatedAt         time.Time    `json:"created_at"`
}
