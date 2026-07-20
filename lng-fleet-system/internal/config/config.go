package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

type Config struct {
	Env           string
	ServerPort    string
	ServerTimeout time.Duration

	PostgresDSN    string
	PostgresMaxConns int32
	PostgresMinConns int32

	RedisAddr     string
	RedisPassword string
	RedisDB       int

	KafkaBrokers  []string
	KafkaTopic    string

	JWTSecret     string
	JWTExpiration time.Duration

	PrometheusEnabled bool
	LogLevel          string
}

func Load() (*Config, error) {
	port := envStr("SERVER_PORT", "8080")
	timeoutSec := envInt("SERVER_TIMEOUT_SEC", 30)

	pgHost := envStr("PGHOST", "localhost")
	pgPort := envStr("PGPORT", "5432")
	pgUser := envStr("PGUSER", "lngfleet")
	pgPass := envStr("PGPASSWORD", "lngfleet")
	pgDB := envStr("PGDATABASE", "lngfleet")
	pgSSL := envStr("PGSSLMODE", "disable")
	dsn := fmt.Sprintf("postgres://%s:%s@%s:%s/%s?sslmode=%s", pgUser, pgPass, pgHost, pgPort, pgDB, pgSSL)

	return &Config{
		Env:           envStr("ENV", "development"),
		ServerPort:    port,
		ServerTimeout: time.Duration(timeoutSec) * time.Second,

		PostgresDSN:       dsn,
		PostgresMaxConns:  int32(envInt("PG_MAX_CONNS", 20)),
		PostgresMinConns:  int32(envInt("PG_MIN_CONNS", 2)),

		RedisAddr:     envStr("REDIS_ADDR", "localhost:6379"),
		RedisPassword: envStr("REDIS_PASSWORD", ""),
		RedisDB:       envInt("REDIS_DB", 0),

		KafkaBrokers: envSlice("KAFKA_BROKERS", []string{"localhost:9092"}),
		KafkaTopic:   envStr("KAFKA_TELEMETRY_TOPIC", "lng-telemetry"),

		JWTSecret:     envStr("JWT_SECRET", "change-me-in-production"),
		JWTExpiration: time.Duration(envInt("JWT_EXPIRATION_HOURS", 24)) * time.Hour,

		PrometheusEnabled: envBool("PROMETHEUS_ENABLED", true),
		LogLevel:          envStr("LOG_LEVEL", "info"),
	}, nil
}

func envStr(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	if v, ok := os.LookupEnv(key); ok {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return fallback
}

func envBool(key string, fallback bool) bool {
	if v, ok := os.LookupEnv(key); ok {
		if b, err := strconv.ParseBool(v); err == nil {
			return b
		}
	}
	return fallback
}

func envSlice(key string, fallback []string) []string {
	if v, ok := os.LookupEnv(key); ok {
		return []string{v}
	}
	return fallback
}
