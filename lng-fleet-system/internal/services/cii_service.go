package services

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/lngfleet/platform/internal/models"
	"github.com/lngfleet/platform/pkg/cii"
	"github.com/rs/zerolog/log"
)

type CIIService struct {
	db *pgxpool.Pool
}

func NewCIIService(db *pgxpool.Pool) *CIIService {
	return &CIIService{db: db}
}

func (s *CIIService) GetHistory(ctx context.Context, vesselID uuid.UUID) ([]models.CIIRecord, error) {
	rows, err := s.db.Query(ctx, `SELECT id, vessel_id, year, attained_cii, required_cii, rating,
		distance_nm, fuel_consumption_tonne, co2_emissions_tonne, cargo_tonnes,
		capacity_cbm, deduction, eedi_value, forecast, created_at
		FROM cii_records WHERE vessel_id = $1 ORDER BY year DESC`, vesselID)
	if err != nil {
		return nil, fmt.Errorf("query cii records: %w", err)
	}
	defer rows.Close()

	var records []models.CIIRecord
	for rows.Next() {
		var r models.CIIRecord
		if err := rows.Scan(&r.ID, &r.VesselID, &r.Year, &r.AttainedCII, &r.RequiredCII,
			&r.Rating, &r.DistanceNM, &r.FuelConsumptionTonne, &r.CO2EmissionsTonne,
			&r.CargoTonnes, &r.CapacityCBM, &r.Deduction, &r.EEDIValue, &r.Forecast,
			&r.CreatedAt); err != nil {
			return nil, fmt.Errorf("scan cii record: %w", err)
		}
		records = append(records, r)
	}
	if records == nil {
		records = []models.CIIRecord{}
	}
	return records, nil
}

func (s *CIIService) Calculate(ctx context.Context, vesselID uuid.UUID, year int) (*models.CIIRecord, error) {
	var vessel models.Vessel
	err := s.db.QueryRow(ctx, `SELECT id, name, cargo_capacity_m3, eedi_design FROM vessels WHERE id = $1`, vesselID).Scan(
		&vessel.ID, &vessel.Name, &vessel.CargoCapacityM3, &vessel.EEDIAttained)
	if err != nil {
		return nil, fmt.Errorf("query vessel %s: %w", vesselID, err)
	}

	var totalFuel float64
	var totalDistance float64
	err = s.db.QueryRow(ctx, `SELECT COALESCE(SUM(fuel_consumption_tonne),0), COALESCE(SUM(distance_nm),0)
		FROM voyages WHERE vessel_id = $1 AND status = 'completed' AND EXTRACT(YEAR FROM departure_time) = $2`,
		vesselID, year).Scan(&totalFuel, &totalDistance)
	if err != nil {
		log.Warn().Err(err).Msg("could not aggregate voyage data, using defaults")
		totalFuel = 10000
		totalDistance = 50000
	}

	if totalDistance == 0 {
		totalDistance = 50000
	}
	if totalFuel == 0 {
		totalFuel = 10000
	}

	co2 := totalFuel * 3.114
	capacity := vessel.CargoCapacityM3
	if capacity == 0 {
		capacity = 170000
	}

	attained := cii.Calculate(totalFuel, totalDistance, co2, capacity)
	required := cii.RequiredCII(year, capacity)
	rating := models.CIIRating(cii.Rating(attained, required, year, capacity))

	record := &models.CIIRecord{
		ID:                  uuid.New(),
		VesselID:            vesselID,
		Year:                year,
		AttainedCII:         attained,
		RequiredCII:         required,
		Rating:              rating,
		DistanceNM:          totalDistance,
		FuelConsumptionTonne: totalFuel,
		CO2EmissionsTonne:   co2,
		CapacityCBM:         capacity,
		EEDIValue:           vessel.EEDIAttained,
		Forecast:            false,
		CreatedAt:           time.Now().UTC(),
	}

	_, err = s.db.Exec(ctx, `INSERT INTO cii_records (id, vessel_id, year, attained_cii, required_cii,
		rating, distance_nm, fuel_consumption_tonne, co2_emissions_tonne, cargo_tonnes,
		capacity_cbm, deduction, eedi_value, forecast, created_at)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
		ON CONFLICT (vessel_id, year) DO UPDATE SET attained_cii=$4, required_cii=$5,
		rating=$6, distance_nm=$7, fuel_consumption_tonne=$8, co2_emissions_tonne=$9,
		cargo_tonnes=$10, eedi_value=$13, forecast=$14`,
		record.ID, record.VesselID, record.Year, record.AttainedCII, record.RequiredCII,
		record.Rating, record.DistanceNM, record.FuelConsumptionTonne, record.CO2EmissionsTonne,
		record.CargoTonnes, record.CapacityCBM, record.Deduction, record.EEDIValue,
		record.Forecast, record.CreatedAt)
	if err != nil {
		return nil, fmt.Errorf("upsert cii record: %w", err)
	}

	return record, nil
}

func (s *CIIService) Forecast(ctx context.Context, vesselID uuid.UUID) ([]models.CIIRecord, error) {
	currentYear := time.Now().UTC().Year()
	var forecasts []models.CIIRecord

	lastRecord, err := s.GetHistory(ctx, vesselID)
	if err != nil || len(lastRecord) == 0 {
		return nil, fmt.Errorf("no historical data for forecast: %w", err)
	}

	latest := lastRecord[0]

	for y := currentYear; y <= currentYear+2; y++ {
		factor := 1.0 - float64(y-currentYear)*0.02
		attained := latest.AttainedCII * factor
		capacity := latest.CapacityCBM
		if capacity == 0 {
			capacity = 170000
		}
		required := cii.RequiredCII(y, capacity)
		rating := models.CIIRating(cii.Rating(attained, required, y, capacity))

		forecasts = append(forecasts, models.CIIRecord{
			ID:                  uuid.New(),
			VesselID:            vesselID,
			Year:                y,
			AttainedCII:         attained,
			RequiredCII:         required,
			Rating:              rating,
			DistanceNM:          latest.DistanceNM,
			FuelConsumptionTonne: latest.FuelConsumptionTonne * factor,
			CO2EmissionsTonne:   latest.CO2EmissionsTonne * factor,
			CapacityCBM:         capacity,
			Forecast:            true,
			CreatedAt:           time.Now().UTC(),
		})
	}

	return forecasts, nil
}
