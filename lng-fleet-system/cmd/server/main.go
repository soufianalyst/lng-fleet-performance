package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/lngfleet/platform/internal/api"
	"github.com/lngfleet/platform/internal/config"
	"github.com/lngfleet/platform/internal/database"
	"github.com/lngfleet/platform/internal/services"
	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/segmentio/kafka-go"
)

func main() {
	zerolog.TimeFieldFormat = time.RFC3339Nano
	zerolog.SetGlobalLevel(zerolog.InfoLevel)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg, err := config.Load()
	if err != nil {
		log.Fatal().Err(err).Msg("failed to load config")
	}

	log.Info().Str("port", cfg.ServerPort).Msg("starting lng-fleet-system server")

	pgPool, err := database.NewPostgresPool(ctx, cfg.PostgresDSN, cfg.PostgresMaxConns, cfg.PostgresMinConns)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to postgres")
	}
	defer pgPool.Close()

	var rdb *redis.Client
	rdb, err = database.NewRedisClient(ctx, cfg.RedisAddr, cfg.RedisPassword, cfg.RedisDB)
	if err != nil {
		log.Warn().Err(err).Msg("redis not available, continuing without cache")
		rdb = nil
	}
	if rdb != nil {
		defer rdb.Close()
	}

	var kafkaWriter *kafka.Writer
	if len(cfg.KafkaBrokers) > 0 {
		kafkaWriter = &kafka.Writer{
			Addr:     kafka.TCP(cfg.KafkaBrokers...),
			Topic:    cfg.KafkaTopic,
			Balancer: &kafka.LeastBytes{},
			BatchTimeout: 10 * time.Millisecond,
			Async:    true,
		}
		log.Info().Strs("brokers", cfg.KafkaBrokers).Str("topic", cfg.KafkaTopic).Msg("kafka producer initialized")
		defer kafkaWriter.Close()
	} else {
		log.Warn().Msg("no kafka brokers configured, telemetry will be stored directly")
	}

	if rdb == nil {
		rdb = redis.NewClient(&redis.Options{Addr: "localhost:6379"})
	}
	if kafkaWriter == nil {
		kafkaWriter = &kafka.Writer{
			Addr:  kafka.TCP("localhost:9092"),
			Topic: "lng-telemetry",
		}
	}

	vesselSvc := services.NewVesselService(pgPool)
	voyageSvc := services.NewVoyageService(pgPool)
	telemetrySvc := services.NewTelemetryService(pgPool, rdb, kafkaWriter)
	ciiSvc := services.NewCIIService(pgPool)
	complianceSvc := services.NewComplianceService(pgPool)
	dashboardSvc := services.NewDashboardService(pgPool, ciiSvc, complianceSvc)

	router := api.NewRouter(
		cfg.Env,
		cfg.JWTSecret,
		vesselSvc,
		voyageSvc,
		telemetrySvc,
		ciiSvc,
		dashboardSvc,
	)

	srv := &http.Server{
		Addr:         fmt.Sprintf(":%s", cfg.ServerPort),
		Handler:      router,
		ReadTimeout:  cfg.ServerTimeout,
		WriteTimeout: cfg.ServerTimeout,
		IdleTimeout:  120 * time.Second,
	}

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Info().Str("addr", srv.Addr).Msg("http server listening")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("http server error")
		}
	}()

	<-quit
	log.Info().Msg("shutting down server...")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Error().Err(err).Msg("server shutdown error")
	}

	log.Info().Msg("server stopped")
}
