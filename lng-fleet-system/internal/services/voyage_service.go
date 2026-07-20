package services

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/lngfleet/platform/internal/models"
	"github.com/rs/zerolog/log"
)

type VoyageService struct {
	db *pgxpool.Pool
}

func NewVoyageService(db *pgxpool.Pool) *VoyageService {
	return &VoyageService{db: db}
}

func (s *VoyageService) List(ctx context.Context, vesselID *uuid.UUID) ([]models.Voyage, error) {
	var rows pgx.Rows
	var err error
	if vesselID != nil {
		rows, err = s.db.Query(ctx, `SELECT id, vessel_id, voyage_number, charter_party_ref,
			departure_port, arrival_port, departure_time, arrival_time, distance_nm,
			status, avg_speed_kn, fuel_consumption_tonne, bog_rate, cargo_loaded_cbm,
			cargo_discharged_cbm, charterer, created_at, updated_at
			FROM voyages WHERE vessel_id = $1 ORDER BY departure_time DESC`, *vesselID)
	} else {
		rows, err = s.db.Query(ctx, `SELECT id, vessel_id, voyage_number, charter_party_ref,
			departure_port, arrival_port, departure_time, arrival_time, distance_nm,
			status, avg_speed_kn, fuel_consumption_tonne, bog_rate, cargo_loaded_cbm,
			cargo_discharged_cbm, charterer, created_at, updated_at
			FROM voyages ORDER BY departure_time DESC`)
	}
	if err != nil {
		return nil, fmt.Errorf("query voyages: %w", err)
	}
	defer rows.Close()

	var voyages []models.Voyage
	for rows.Next() {
		var v models.Voyage
		if err := rows.Scan(&v.ID, &v.VesselID, &v.VoyageNumber, &v.CharterPartyRef,
			&v.DeparturePort, &v.ArrivalPort, &v.DepartureTime, &v.ArrivalTime,
			&v.DistanceNM, &v.Status, &v.AvgSpeedKN, &v.FuelConsumptionTonne,
			&v.BOGRate, &v.CargoLoadedCBM, &v.CargoDischargedCBM, &v.Charterer,
			&v.CreatedAt, &v.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan voyage: %w", err)
		}
		voyages = append(voyages, v)
	}
	if voyages == nil {
		voyages = []models.Voyage{}
	}
	return voyages, nil
}

func (s *VoyageService) GetByID(ctx context.Context, id uuid.UUID) (*models.Voyage, error) {
	var v models.Voyage
	err := s.db.QueryRow(ctx, `SELECT id, vessel_id, voyage_number, charter_party_ref,
		departure_port, arrival_port, departure_time, arrival_time, distance_nm,
		status, avg_speed_kn, fuel_consumption_tonne, bog_rate, cargo_loaded_cbm,
		cargo_discharged_cbm, charterer, created_at, updated_at
		FROM voyages WHERE id = $1`, id).Scan(
		&v.ID, &v.VesselID, &v.VoyageNumber, &v.CharterPartyRef,
		&v.DeparturePort, &v.ArrivalPort, &v.DepartureTime, &v.ArrivalTime,
		&v.DistanceNM, &v.Status, &v.AvgSpeedKN, &v.FuelConsumptionTonne,
		&v.BOGRate, &v.CargoLoadedCBM, &v.CargoDischargedCBM, &v.Charterer,
		&v.CreatedAt, &v.UpdatedAt)
	if err != nil {
		return nil, fmt.Errorf("query voyage %s: %w", id, err)
	}
	return &v, nil
}

func (s *VoyageService) Create(ctx context.Context, v *models.Voyage) error {
	v.ID = uuid.New()
	v.CreatedAt = time.Now().UTC()
	v.UpdatedAt = v.CreatedAt
	_, err := s.db.Exec(ctx, `INSERT INTO voyages (id, vessel_id, voyage_number, charter_party_ref,
		departure_port, arrival_port, departure_time, arrival_time, distance_nm,
		status, avg_speed_kn, fuel_consumption_tonne, bog_rate, cargo_loaded_cbm,
		cargo_discharged_cbm, charterer, created_at, updated_at)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)`,
		v.ID, v.VesselID, v.VoyageNumber, v.CharterPartyRef,
		v.DeparturePort, v.ArrivalPort, v.DepartureTime, v.ArrivalTime,
		v.DistanceNM, v.Status, v.AvgSpeedKN, v.FuelConsumptionTonne,
		v.BOGRate, v.CargoLoadedCBM, v.CargoDischargedCBM, v.Charterer,
		v.CreatedAt, v.UpdatedAt)
	if err != nil {
		return fmt.Errorf("insert voyage: %w", err)
	}
	log.Info().Str("id", v.ID.String()).Str("number", v.VoyageNumber).Msg("voyage created")
	return nil
}

func (s *VoyageService) Update(ctx context.Context, v *models.Voyage) error {
	v.UpdatedAt = time.Now().UTC()
	_, err := s.db.Exec(ctx, `UPDATE voyages SET vessel_id=$2, voyage_number=$3, charter_party_ref=$4,
		departure_port=$5, arrival_port=$6, departure_time=$7, arrival_time=$8,
		distance_nm=$9, status=$10, avg_speed_kn=$11, fuel_consumption_tonne=$12,
		bog_rate=$13, cargo_loaded_cbm=$14, cargo_discharged_cbm=$15, charterer=$16,
		updated_at=$17 WHERE id=$1`,
		v.ID, v.VesselID, v.VoyageNumber, v.CharterPartyRef,
		v.DeparturePort, v.ArrivalPort, v.DepartureTime, v.ArrivalTime,
		v.DistanceNM, v.Status, v.AvgSpeedKN, v.FuelConsumptionTonne,
		v.BOGRate, v.CargoLoadedCBM, v.CargoDischargedCBM, v.Charterer,
		v.UpdatedAt)
	if err != nil {
		return fmt.Errorf("update voyage %s: %w", v.ID, err)
	}
	return nil
}

func (s *VoyageService) Delete(ctx context.Context, id uuid.UUID) error {
	_, err := s.db.Exec(ctx, `DELETE FROM voyages WHERE id = $1`, id)
	if err != nil {
		return fmt.Errorf("delete voyage %s: %w", id, err)
	}
	return nil
}
