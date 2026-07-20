package services

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/lngfleet/platform/internal/models"
	"github.com/rs/zerolog/log"
)

type VesselService struct {
	db *pgxpool.Pool
}

func NewVesselService(db *pgxpool.Pool) *VesselService {
	return &VesselService{db: db}
}

func (s *VesselService) List(ctx context.Context) ([]models.Vessel, error) {
	rows, err := s.db.Query(ctx, `SELECT id, imo_number, name, flag, vessel_type,
		cargo_capacity_m3, build_year, engine_type, lng_tank_type,
		design_draft_m, design_speed_kn,
		eedi_attained, eexi_required, eexi_attained,
		scrubber_installed, scr_installed, egr_installed, shore_power_capable,
		created_at, updated_at FROM vessels ORDER BY name`)
	if err != nil {
		return nil, fmt.Errorf("query vessels: %w", err)
	}
	defer rows.Close()

	var vessels []models.Vessel
	for rows.Next() {
		var v models.Vessel
		if err := rows.Scan(&v.ID, &v.IMONumber, &v.Name, &v.Flag, &v.VesselType,
			&v.CargoCapacityM3, &v.YearBuilt, &v.EngineType, &v.TankType,
			&v.DesignDraftM, &v.DesignSpeedKN,
			&v.EEDIAttained, &v.EEXIRequired, &v.EEXIAttained,
			&v.ScrubberInstalled, &v.SCRInstalled, &v.EGRInstalled, &v.ShorePowerCapable,
			&v.CreatedAt, &v.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan vessel: %w", err)
		}
		vessels = append(vessels, v)
	}
	if vessels == nil {
		vessels = []models.Vessel{}
	}
	return vessels, nil
}

func (s *VesselService) GetByID(ctx context.Context, id uuid.UUID) (*models.Vessel, error) {
	var v models.Vessel
	err := s.db.QueryRow(ctx, `SELECT id, imo_number, name, flag, vessel_type,
		cargo_capacity_m3, build_year, engine_type, lng_tank_type,
		design_draft_m, design_speed_kn,
		eedi_attained, eexi_required, eexi_attained,
		scrubber_installed, scr_installed, egr_installed, shore_power_capable,
		created_at, updated_at FROM vessels WHERE id = $1`, id).Scan(
		&v.ID, &v.IMONumber, &v.Name, &v.Flag, &v.VesselType,
		&v.CargoCapacityM3, &v.YearBuilt, &v.EngineType, &v.TankType,
		&v.DesignDraftM, &v.DesignSpeedKN,
		&v.EEDIAttained, &v.EEXIRequired, &v.EEXIAttained,
		&v.ScrubberInstalled, &v.SCRInstalled, &v.EGRInstalled, &v.ShorePowerCapable,
		&v.CreatedAt, &v.UpdatedAt)
	if err != nil {
		return nil, fmt.Errorf("query vessel %s: %w", id, err)
	}
	return &v, nil
}

func (s *VesselService) Create(ctx context.Context, v *models.Vessel) error {
	v.ID = uuid.New()
	_, err := s.db.Exec(ctx, `INSERT INTO vessels (id, imo_number, name, flag, vessel_type,
		cargo_capacity_m3, build_year, engine_type, lng_tank_type,
		design_draft_m, design_speed_kn,
		scrubber_installed, scr_installed, egr_installed, shore_power_capable)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)`,
		v.ID, v.IMONumber, v.Name, v.Flag, v.VesselType,
		v.CargoCapacityM3, v.YearBuilt, v.EngineType, v.TankType,
		v.DesignDraftM, v.DesignSpeedKN,
		v.ScrubberInstalled, v.SCRInstalled, v.EGRInstalled, v.ShorePowerCapable)
	if err != nil {
		return fmt.Errorf("insert vessel: %w", err)
	}
	log.Info().Str("vessel_id", v.ID.String()).Str("name", v.Name).Msg("vessel created")
	return nil
}

func (s *VesselService) Update(ctx context.Context, v *models.Vessel) error {
	_, err := s.db.Exec(ctx, `UPDATE vessels SET imo_number=$2, name=$3, flag=$4, build_year=$5,
		cargo_capacity_m3=$6, engine_type=$7, lng_tank_type=$8,
		design_draft_m=$9, design_speed_kn=$10
		WHERE id=$1`,
		v.ID, v.IMONumber, v.Name, v.Flag, v.YearBuilt,
		v.CargoCapacityM3, v.EngineType, v.TankType,
		v.DesignDraftM, v.DesignSpeedKN)
	if err != nil {
		return fmt.Errorf("update vessel: %w", err)
	}
	return nil
}

func (s *VesselService) Delete(ctx context.Context, id uuid.UUID) error {
	_, err := s.db.Exec(ctx, `DELETE FROM vessels WHERE id = $1`, id)
	if err != nil {
		return fmt.Errorf("delete vessel: %w", err)
	}
	return nil
}
