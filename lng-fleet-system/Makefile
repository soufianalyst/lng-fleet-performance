.PHONY: dev build test clean db-gen data-gen up down logs help

SHELL := /bin/bash

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Run full stack in development mode
	docker compose up -d postgres redis kafka
	@sleep 3
	cd synthetic-data-generator && pip install -q -r requirements.txt && python run.py --db
	cd frontend && npm run dev &
	go run ./cmd/server &
	@echo "API: http://localhost:8080 | Frontend: http://localhost:5173"

build: ## Build all Docker images
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down -v

logs: ## Follow logs
	docker compose logs -f

db-up: ## Start only database
	docker compose up -d postgres redis

db-connect: ## Connect to PostgreSQL
	PGPASSWORD=lngfleet_dev psql -h localhost -U lngfleet -d lngfleet

data-gen: ## Generate synthetic data and load to DB
	docker compose run --rm synthetic-data-gen

data-gen-local: ## Generate synthetic data locally (CSV + DB)
	cd synthetic-data-generator && pip install -q -r requirements.txt && python run.py --csv --db

ml-train: ## Train ML models
	docker compose run --rm ml-pipeline python -m pipeline.train

ml-serve: ## Start ML inference server
	cd ml && pip install -q -r requirements.txt && python -m pipeline.inference

backend: ## Run Go backend locally
	go run ./cmd/server

frontend: ## Run frontend dev server
	cd frontend && npm run dev

edge-build: ## Build Rust edge gateway
	cd edge && cargo build --release

edge-run: ## Run edge gateway locally
	cd edge && cargo run --release

test-backend: ## Run Go tests
	go test ./... -v -count=1

test-frontend: ## Run frontend tests
	cd frontend && npm run test -- --run

test: test-backend ## Run all tests

lint: ## Lint all code
	golangci-lint run ./...
	cd frontend && npm run lint
	cd edge && cargo clippy -- -D warnings

clean: ## Clean build artifacts
	rm -rf frontend/dist
	rm -rf edge/target
	go clean -cache
	docker compose down -v
	rm -rf synthetic-data-generator/output

deploy: ## Deploy to production (requires .env.prod)
	@echo "Set KUBECONFIG and run: kubectl apply -f deploy/kubernetes/"
