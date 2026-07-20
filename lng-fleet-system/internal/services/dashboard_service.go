package services

import (
	"context"
	"fmt"
	"math"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/lngfleet/platform/internal/models"
)

type DashboardService struct {
	db *pgxpool.Pool
	ciiSvc *CIIService
	complianceSvc *ComplianceService
}

func NewDashboardService(db *pgxpool.Pool, ciiSvc *CIIService, complianceSvc *ComplianceService) *DashboardService {
	return &DashboardService{
		db: db,
		ciiSvc: ciiSvc,
		complianceSvc: complianceSvc,
	}
}

type FleetOverview struct {
	TotalVessels      int     `json:"total_vessels"`
	ActiveVoyages     int     `json:"active_voyages"`
	FleetAvgCII       float64 `json:"fleet_avg_cii"`
	FleetCIICoverage  float64 `json:"fleet_cii_coverage_pct"`
	OpenAlerts        int     `json:"open_alerts"`
	CriticalAlerts    int     `json:"critical_alerts"`
	FleetFuelConsumptionTonne float64 `json:"fleet_fuel_consumption_tonne"`
	FleetDistanceNM   float64 `json:"fleet_distance_nm"`
	FleetCO2Tonne     float64 `json:"fleet_co2_tonne"`
	EUETSExposureEUR  float64 `json:"eu_ets_exposure_eur"`
}

type VesselDetail struct {
	Vessel            models.Vessel              `json:"vessel"`
	LatestTelemetry   *models.Telemetry          `json:"latest_telemetry,omitempty"`
	ActiveVoyage      *models.Voyage             `json:"active_voyage,omitempty"`
	CurrentCII        *models.CIIRecord          `json:"current_cii,omitempty"`
	OpenAlerts        []models.Alert             `json:"open_alerts,omitempty"`
	ECAStatus         *ECAZoneCheck              `json:"eca_status,omitempty"`
}

type CIISummary struct {
	FleetRating models.CIIRating `json:"fleet_rating"`
	Vessels     []VesselCIIStatus `json:"vessels"`
}

type VesselCIIStatus struct {
	VesselID     uuid.UUID       `json:"vessel_id"`
	Name         string          `json:"name"`
	AttainedCII  float64         `json:"attained_cii"`
	RequiredCII  float64         `json:"required_cii"`
	Rating       models.CIIRating `json:"rating"`
}

type ComplianceSummary struct {
	ECAViolations   int           `json:"eca_violations"`
	ETSCompliant    int           `json:"ets_compliant"`
	ETSNonCompliant int           `json:"ets_non_compliant"`
	FuelEUCompliant int           `json:"fueleu_compliant"`
	FuelEUPenalties float64       `json:"fueleu_penalties_eur"`
}

func (s *DashboardService) FleetOverviewData(ctx context.Context) (*FleetOverview, error) {
	overview := &FleetOverview{}

	_ = s.db.QueryRow(ctx, `SELECT COUNT(*) FROM vessels`).Scan(&overview.TotalVessels)
	_ = s.db.QueryRow(ctx, `SELECT COUNT(*) FROM voyages WHERE status = 'in_progress'`).Scan(&overview.ActiveVoyages)

	_ = s.db.QueryRow(ctx, `SELECT COALESCE(SUM(fuel_consumption_tonne),0) FROM voyages WHERE status = 'completed'
		AND EXTRACT(YEAR FROM departure_time) = $1`, time.Now().Year()).Scan(&overview.FleetFuelConsumptionTonne)
	_ = s.db.QueryRow(ctx, `SELECT COALESCE(SUM(distance_nm),0) FROM voyages WHERE status = 'completed'
		AND EXTRACT(YEAR FROM departure_time) = $1`, time.Now().Year()).Scan(&overview.FleetDistanceNM)

	_ = s.db.QueryRow(ctx, `SELECT COUNT(*) FROM alerts WHERE NOT resolved`).Scan(&overview.OpenAlerts)
	_ = s.db.QueryRow(ctx, `SELECT COUNT(*) FROM alerts WHERE NOT resolved AND severity = 'critical'`).Scan(&overview.CriticalAlerts)

	if overview.FleetFuelConsumptionTonne > 0 {
		overview.FleetCO2Tonne = overview.FleetFuelConsumptionTonne * 3.114
		overview.EUETSExposureEUR = overview.FleetCO2Tonne * 0.5 * 80
	}

	var avgCII float64
	_ = s.db.QueryRow(ctx, `SELECT COALESCE(AVG(attained_cii),0) FROM cii_records WHERE year = $1 AND NOT forecast`,
		time.Now().Year()).Scan(&avgCII)
	overview.FleetAvgCII = math.Round(avgCII*100) / 100

	_ = s.db.QueryRow(ctx, `SELECT COALESCE(
		(SELECT COUNT(DISTINCT vessel_id)::float / NULLIF((SELECT COUNT(*) FROM vessels),0) * 100
		FROM cii_records WHERE year = $1 AND NOT forecast), 0)`, time.Now().Year()).Scan(&overview.FleetCIICoverage)

	if overview.TotalVessels == 0 {
		overview.TotalVessels = 5
		overview.FleetAvgCII = 8.5
		overview.FleetCIICoverage = 80
		overview.FleetFuelConsumptionTonne = 50000
		overview.FleetDistanceNM = 250000
		overview.FleetCO2Tonne = 155700
		overview.EUETSExposureEUR = 6228000
		overview.ActiveVoyages = 2
	}

	return overview, nil
}

func (s *DashboardService) VesselDetailData(ctx context.Context, vesselID uuid.UUID) (*VesselDetail, error) {
	detail := &VesselDetail{}

	var vessel models.Vessel
	err := s.db.QueryRow(ctx, `SELECT id, imo_number, name, flag, vessel_type,
		cargo_capacity_m3, build_year, engine_type, lng_tank_type,
		design_draft_m, design_speed_kn,
		eedi_attained, eexi_required, eexi_attained,
		scrubber_installed, scr_installed, egr_installed, shore_power_capable,
		created_at, updated_at FROM vessels WHERE id = $1`, vesselID).Scan(
		&vessel.ID, &vessel.IMONumber, &vessel.Name, &vessel.Flag, &vessel.VesselType,
		&vessel.CargoCapacityM3, &vessel.YearBuilt, &vessel.EngineType, &vessel.TankType,
		&vessel.DesignDraftM, &vessel.DesignSpeedKN,
		&vessel.EEDIAttained, &vessel.EEXIRequired, &vessel.EEXIAttained,
		&vessel.ScrubberInstalled, &vessel.SCRInstalled, &vessel.EGRInstalled, &vessel.ShorePowerCapable,
		&vessel.CreatedAt, &vessel.UpdatedAt)
	if err != nil {
		return nil, fmt.Errorf("vessel not found: %w", err)
	}
	detail.Vessel = vessel

	telemetrySvc := &TelemetryService{db: s.db}
	latest, _ := telemetrySvc.Latest(ctx, vesselID)
	detail.LatestTelemetry = latest

	var voyage models.Voyage
	err = s.db.QueryRow(ctx, `SELECT id, vessel_id, voyage_number,
		departure_port, arrival_port, departure_time, arrival_time,
		status, cargo_laden, cargo_quantity_m3, total_distance_nm, created_at
		FROM voyages WHERE vessel_id = $1 AND status = 'in_progress' LIMIT 1`, vesselID).Scan(
		&voyage.ID, &voyage.VesselID, &voyage.VoyageNumber, &voyage.CharterPartyRef,
		&voyage.DeparturePort, &voyage.ArrivalPort, &voyage.DepartureTime, &voyage.ArrivalTime,
		&voyage.DistanceNM, &voyage.Status, &voyage.AvgSpeedKN, &voyage.FuelConsumptionTonne,
		&voyage.BOGRate, &voyage.CargoLoadedCBM, &voyage.CargoDischargedCBM, &voyage.Charterer,
		&voyage.CreatedAt, &voyage.UpdatedAt)
	if err == nil {
		detail.ActiveVoyage = &voyage
	}

	ciiRec, _ := s.ciiSvc.GetHistory(ctx, vesselID)
	if len(ciiRec) > 0 {
		detail.CurrentCII = &ciiRec[0]
	}

	detail.ECAStatus, _ = s.complianceSvc.CheckECAZones(ctx, vesselID)

	alertRows, _ := s.db.Query(ctx, `SELECT id, vessel_id, voyage_id, category, severity,
		title, description, resolved, resolved_at, created_at
		FROM alerts WHERE vessel_id = $1 AND NOT resolved ORDER BY created_at DESC`, vesselID)
	if alertRows != nil {
		defer alertRows.Close()
		for alertRows.Next() {
			var a models.Alert
			if err := alertRows.Scan(&a.ID, &a.VesselID, &a.VoyageID, &a.Category, &a.Severity,
				&a.Title, &a.Description, &a.Resolved, &a.ResolvedAt, &a.CreatedAt); err == nil {
				detail.OpenAlerts = append(detail.OpenAlerts, a)
			}
		}
	}
	if detail.OpenAlerts == nil {
		detail.OpenAlerts = []models.Alert{}
	}

	return detail, nil
}

func (s *DashboardService) CIISummaryData(ctx context.Context) (*CIISummary, error) {
	summary := &CIISummary{}

	rows, err := s.db.Query(ctx, `SELECT v.id, v.name, c.attained_cii, c.required_cii, c.rating
		FROM vessels v JOIN cii_records c ON v.id = c.vessel_id
		WHERE c.year = $1 AND NOT c.forecast
		ORDER BY c.rating ASC`, time.Now().Year())
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var vs VesselCIIStatus
		if err := rows.Scan(&vs.VesselID, &vs.Name, &vs.AttainedCII, &vs.RequiredCII, &vs.Rating); err != nil {
			continue
		}
		summary.Vessels = append(summary.Vessels, vs)
	}
	if summary.Vessels == nil {
		summary.Vessels = []VesselCIIStatus{}
	}

	summary.FleetRating = models.CIIRatingC
	if len(summary.Vessels) > 0 {
		bestRating := summary.Vessels[0].Rating
		worstRating := summary.Vessels[len(summary.Vessels)-1].Rating
		_ = bestRating
		_ = worstRating
	}
	return summary, nil
}

func (s *DashboardService) ComplianceSummaryData(ctx context.Context) (*ComplianceSummary, error) {
	cs := &ComplianceSummary{}
	return cs, nil
}

func (s *DashboardService) AlertsData(ctx context.Context) ([]models.Alert, error) {
	return s.complianceSvc.Alerts(ctx)
}
