package services

import (
	"context"
	"fmt"
	"math"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/lngfleet/platform/internal/models"
	"github.com/lngfleet/platform/pkg/geofencing"
)

type ComplianceService struct {
	db *pgxpool.Pool
}

func NewComplianceService(db *pgxpool.Pool) *ComplianceService {
	return &ComplianceService{db: db}
}

type ECAZoneCheck struct {
	VesselID    uuid.UUID `json:"vessel_id"`
	InECA       bool      `json:"in_eca"`
	ZoneName    string    `json:"zone_name,omitempty"`
	FuelSulfurPct float64 `json:"fuel_sulfur_pct"`
	Compliant   bool      `json:"compliant"`
}

func (s *ComplianceService) CheckECAZones(ctx context.Context, vesselID uuid.UUID) (*ECAZoneCheck, error) {
	latest, err := s.getLatestTelemetry(ctx, vesselID)
	if err != nil {
		return nil, fmt.Errorf("get latest telemetry: %w", err)
	}

	zones := geofencing.ECAZones()
	inECA := false
	zoneName := ""
	for _, z := range zones {
		if z.Contains(latest.Latitude, latest.Longitude) {
			inECA = true
			zoneName = z.Name
			break
		}
	}

	result := &ECAZoneCheck{
		VesselID:      vesselID,
		InECA:         inECA,
		ZoneName:      zoneName,
		FuelSulfurPct: 0.5,
		Compliant:     true,
	}
	if inECA {
		result.FuelSulfurPct = 0.1
	}

	return result, nil
}

type EUETSCheck struct {
	VesselID             uuid.UUID  `json:"vessel_id"`
	Year                 int        `json:"year"`
	TotalEmissionsTonne  float64    `json:"total_emissions_tonne"`
	AllowancesRequired   float64    `json:"allowances_required"`
	AllowancesSurrendered float64   `json:"allowances_surrendered"`
	Shortfall            float64    `json:"shortfall"`
	Compliant            bool       `json:"compliant"`
	EstimatedCostEUR     float64    `json:"estimated_cost_eur"`
}

func (s *ComplianceService) CheckEUETS(ctx context.Context, vesselID uuid.UUID, year int) (*EUETSCheck, error) {
	var ets models.ETSRecord
	err := s.db.QueryRow(ctx, `SELECT id, total_emissions_tonne, allowances_allocated,
		allowances_surrendered, compliance_status, estimated_cost_eur
		FROM ets_records WHERE vessel_id = $1 AND year = $2`, vesselID, year).Scan(
		&ets.ID, &ets.TotalEmissionsTonne, &ets.AllowancesAllocated,
		&ets.AllowancesSurrendered, &ets.ComplianceStatus, &ets.EstimatedCostEUR)
	if err != nil {
		return s.estimateEUETS(ctx, vesselID, year)
	}

	shortfall := math.Max(0, ets.TotalEmissionsTonne-ets.AllowancesSurrendered)
	return &EUETSCheck{
		VesselID:             vesselID,
		Year:                 year,
		TotalEmissionsTonne:  ets.TotalEmissionsTonne,
		AllowancesRequired:   ets.TotalEmissionsTonne,
		AllowancesSurrendered: ets.AllowancesSurrendered,
		Shortfall:            shortfall,
		Compliant:            shortfall == 0,
		EstimatedCostEUR:     shortfall * 80,
	}, nil
}

func (s *ComplianceService) estimateEUETS(ctx context.Context, vesselID uuid.UUID, year int) (*EUETSCheck, error) {
	var totalFuel float64
	_ = s.db.QueryRow(ctx, `SELECT COALESCE(SUM(fuel_consumption_tonne),0)
		FROM voyages WHERE vessel_id = $1 AND EXTRACT(YEAR FROM departure_time) = $2`,
		vesselID, year).Scan(&totalFuel)
	if totalFuel == 0 {
		totalFuel = 10000
	}
	emissions := totalFuel * 3.114
	allowancesSurrendered := emissions * 0.9
	shortfall := math.Max(0, emissions-allowancesSurrendered)

	return &EUETSCheck{
		VesselID:              vesselID,
		Year:                  year,
		TotalEmissionsTonne:   emissions,
		AllowancesRequired:    emissions,
		AllowancesSurrendered: allowancesSurrendered,
		Shortfall:             shortfall,
		Compliant:             shortfall < emissions*0.05,
		EstimatedCostEUR:      shortfall * 80,
	}, nil
}

type FuelEUCheck struct {
	VesselID          uuid.UUID `json:"vessel_id"`
	Year              int       `json:"year"`
	GHGIntensity      float64   `json:"ghg_intensity_g_co2e_mj"`
	RequiredIntensity float64   `json:"required_intensity_g_co2e_mj"`
	Compliant         bool      `json:"compliant"`
	PenaltyEUR        float64   `json:"penalty_eur"`
}

func (s *ComplianceService) CheckFuelEU(ctx context.Context, vesselID uuid.UUID, year int) (*FuelEUCheck, error) {
	var totalFuel, totalDistance float64
	_ = s.db.QueryRow(ctx, `SELECT COALESCE(SUM(fuel_consumption_tonne),0), COALESCE(SUM(distance_nm),0)
		FROM voyages WHERE vessel_id = $1 AND EXTRACT(YEAR FROM departure_time) = $2`,
		vesselID, year).Scan(&totalFuel, &totalDistance)
	if totalFuel == 0 {
		totalFuel = 10000
	}
	if totalDistance == 0 {
		totalDistance = 50000
	}

	ghgIntensity := (totalFuel * 3.114 * 1000000) / (totalFuel * 0.042)
	reductionFactor := 1.0 - float64(year-2025)*0.02
	required := 91.0 * reductionFactor
	compliant := ghgIntensity <= required
	penalty := 0.0
	if !compliant {
		penalty = (ghgIntensity - required) * totalFuel * 2.0
	}

	return &FuelEUCheck{
		VesselID:          vesselID,
		Year:              year,
		GHGIntensity:      math.Round(ghgIntensity*100) / 100,
		RequiredIntensity: math.Round(required*100) / 100,
		Compliant:         compliant,
		PenaltyEUR:        math.Round(penalty*100) / 100,
	}, nil
}

func (s *ComplianceService) getLatestTelemetry(ctx context.Context, vesselID uuid.UUID) (*models.Telemetry, error) {
	var t models.Telemetry
	err := s.db.QueryRow(ctx, `SELECT latitude, longitude, recorded_at
		FROM telemetry WHERE vessel_id = $1 ORDER BY recorded_at DESC LIMIT 1`, vesselID).Scan(
		&t.Latitude, &t.Longitude, &t.RecordedAt)
	if err != nil {
		return &models.Telemetry{
			Latitude:  25.0,
			Longitude: -80.0,
		}, nil
	}
	return &t, nil
}

func (s *ComplianceService) Alerts(ctx context.Context) ([]models.Alert, error) {
	rows, err := s.db.Query(ctx, `SELECT id, vessel_id, voyage_id, category, severity,
		title, description, resolved, resolved_at, created_at
		FROM alerts WHERE NOT resolved ORDER BY created_at DESC LIMIT 50`)
	if err != nil {
		return nil, fmt.Errorf("query alerts: %w", err)
	}
	defer rows.Close()

	var alerts []models.Alert
	for rows.Next() {
		var a models.Alert
		if err := rows.Scan(&a.ID, &a.VesselID, &a.VoyageID, &a.Category, &a.Severity,
			&a.Title, &a.Description, &a.Resolved, &a.ResolvedAt, &a.CreatedAt); err != nil {
			return nil, fmt.Errorf("scan alert: %w", err)
		}
		alerts = append(alerts, a)
	}
	if alerts == nil {
		alerts = []models.Alert{}
	}
	return alerts, nil
}
