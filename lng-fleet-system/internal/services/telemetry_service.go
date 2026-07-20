package services

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/lngfleet/platform/internal/models"
	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
	"github.com/segmentio/kafka-go"
)

type TelemetryService struct {
	db    *pgxpool.Pool
	rdb   *redis.Client
	producer *kafka.Writer
}

func NewTelemetryService(db *pgxpool.Pool, rdb *redis.Client, producer *kafka.Writer) *TelemetryService {
	return &TelemetryService{db: db, rdb: rdb, producer: producer}
}

func (s *TelemetryService) Ingest(ctx context.Context, t *models.Telemetry) error {
	t.ID = uuid.New()
	t.IngestedAt = time.Now().UTC()

	payload, err := json.Marshal(t)
	if err != nil {
		return fmt.Errorf("marshal telemetry: %w", err)
	}

	if err := s.producer.WriteMessages(ctx, kafka.Message{
		Topic: "lng-telemetry",
		Key:   []byte(t.VesselID.String()),
		Value: payload,
	}); err != nil {
		log.Warn().Err(err).Msg("kafka write failed, storing directly to db")
	}

	if err := s.storeToDB(ctx, t); err != nil {
		return fmt.Errorf("store telemetry: %w", err)
	}

	cacheKey := fmt.Sprintf("telemetry:latest:%s", t.VesselID.String())
	cacheCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := s.rdb.Set(cacheCtx, cacheKey, string(payload), 5*time.Minute).Err(); err != nil {
		log.Warn().Err(err).Msg("redis cache set failed")
	}

	return nil
}

func (s *TelemetryService) storeToDB(ctx context.Context, t *models.Telemetry) error {
	_, err := s.db.Exec(ctx, `INSERT INTO telemetry (
		id, vessel_id, voyage_id, recorded_at, latitude, longitude,
		speed_over_ground, course_over_ground, heading,
		wind_speed_ms, wind_direction_deg, wave_height_m,
		air_temperature_c, sea_temperature_c,
		engine_load_pct, fuel_consumption_rate_tonne_day,
		me1_rpm_percent, me2_rpm_percent, aux_engine_load_kw,
		gcu_consumption_tonne_day, bog_rate_percent, tank_level_pct,
		sloshing_detected, draft_fwd_m, draft_aft_m, trim_m,
		source, ingested_at
	) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28)`,
		t.ID, t.VesselID, t.VoyageID, t.RecordedAt, t.Latitude, t.Longitude,
		t.SpeedOverGround, t.CourseOverGround, t.Heading,
		t.WindSpeedMS, t.WindDirectionDeg, t.WaveHeightM,
		t.AirTemperatureC, t.SeaTemperatureC,
		t.EngineLoadPct, t.FuelConsumptionRate,
		t.ME1RPMPercent, t.ME2RPMPercent, t.AuxEngineLoadKW,
		t.GCUConsumption, t.BOGRate, t.TankLevelPct,
		t.SloshingDetected, t.DraftFwdM, t.DraftAftM, t.TrimM,
		t.Source, t.IngestedAt)
	if err != nil {
		return fmt.Errorf("insert telemetry: %w", err)
	}
	return nil
}

func (s *TelemetryService) Query(ctx context.Context, vesselID uuid.UUID, from, to time.Time) ([]models.Telemetry, error) {
	rows, err := s.db.Query(ctx, `SELECT id, vessel_id, voyage_id, recorded_at, latitude, longitude,
		speed_over_ground, course_over_ground, heading,
		wind_speed_ms, wind_direction_deg, wave_height_m,
		air_temperature_c, sea_temperature_c,
		engine_load_pct, fuel_consumption_rate_tonne_day,
		me1_rpm_percent, me2_rpm_percent, aux_engine_load_kw,
		gcu_consumption_tonne_day, bog_rate_percent, tank_level_pct,
		sloshing_detected, draft_fwd_m, draft_aft_m, trim_m,
		source, ingested_at
		FROM telemetry WHERE vessel_id = $1 AND recorded_at BETWEEN $2 AND $3
		ORDER BY recorded_at ASC`, vesselID, from, to)
	if err != nil {
		return nil, fmt.Errorf("query telemetry: %w", err)
	}
	defer rows.Close()

	var results []models.Telemetry
	for rows.Next() {
		var t models.Telemetry
		if err := rows.Scan(&t.ID, &t.VesselID, &t.VoyageID, &t.RecordedAt,
			&t.Latitude, &t.Longitude, &t.SpeedOverGround, &t.CourseOverGround,
			&t.Heading, &t.WindSpeedMS, &t.WindDirectionDeg, &t.WaveHeightM,
			&t.AirTemperatureC, &t.SeaTemperatureC, &t.EngineLoadPct,
			&t.FuelConsumptionRate, &t.ME1RPMPercent, &t.ME2RPMPercent,
			&t.AuxEngineLoadKW, &t.GCUConsumption, &t.BOGRate, &t.TankLevelPct,
			&t.SloshingDetected, &t.DraftFwdM, &t.DraftAftM, &t.TrimM,
			&t.Source, &t.IngestedAt); err != nil {
			return nil, fmt.Errorf("scan telemetry: %w", err)
		}
		results = append(results, t)
	}
	if results == nil {
		results = []models.Telemetry{}
	}
	return results, nil
}

func (s *TelemetryService) Latest(ctx context.Context, vesselID uuid.UUID) (*models.Telemetry, error) {
	cacheKey := fmt.Sprintf("telemetry:latest:%s", vesselID.String())
	cached, err := s.rdb.Get(ctx, cacheKey).Result()
	if err == nil && cached != "" {
		var t models.Telemetry
		if err := json.Unmarshal([]byte(cached), &t); err == nil {
			return &t, nil
		}
	}

	var t models.Telemetry
	err = s.db.QueryRow(ctx, `SELECT id, vessel_id, voyage_id, recorded_at, latitude, longitude,
		speed_over_ground, course_over_ground, heading,
		wind_speed_ms, wind_direction_deg, wave_height_m,
		air_temperature_c, sea_temperature_c,
		engine_load_pct, fuel_consumption_rate_tonne_day,
		me1_rpm_percent, me2_rpm_percent, aux_engine_load_kw,
		gcu_consumption_tonne_day, bog_rate_percent, tank_level_pct,
		sloshing_detected, draft_fwd_m, draft_aft_m, trim_m,
		source, ingested_at
		FROM telemetry WHERE vessel_id = $1 ORDER BY recorded_at DESC LIMIT 1`, vesselID).Scan(
		&t.ID, &t.VesselID, &t.VoyageID, &t.RecordedAt,
		&t.Latitude, &t.Longitude, &t.SpeedOverGround, &t.CourseOverGround,
		&t.Heading, &t.WindSpeedMS, &t.WindDirectionDeg, &t.WaveHeightM,
		&t.AirTemperatureC, &t.SeaTemperatureC, &t.EngineLoadPct,
		&t.FuelConsumptionRate, &t.ME1RPMPercent, &t.ME2RPMPercent,
		&t.AuxEngineLoadKW, &t.GCUConsumption, &t.BOGRate, &t.TankLevelPct,
		&t.SloshingDetected, &t.DraftFwdM, &t.DraftAftM, &t.TrimM,
		&t.Source, &t.IngestedAt)
	if err != nil {
		return nil, fmt.Errorf("query latest telemetry %s: %w", vesselID, err)
	}
	return &t, nil
}
