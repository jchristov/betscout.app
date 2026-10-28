# BetScout Monorepo Makefile (frontend/ Vue 3 + Tailwind SPA & backend/ Python Quant Engine)
SHELL := /bin/bash
export PATH := /opt/homebrew/bin:/usr/local/bin:$(PATH)

HOST ?= 127.0.0.1
PORT ?= 8090

.PHONY: help install dev serve frontend-dev frontend-build frontend-test sdk-build sdk-test backend-test test logos cards-gallery sync rescan pipeline deploy undeploy clean

help: ## Show all available Makefile commands
	@echo "BetScout — Quantitative Sports Edge & Score Intelligence"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install frontend (npm), sdk (npm), and backend (uv) dependencies
	cd frontend && npm install --no-audit --no-fund
	cd sdk && npm install --no-audit --no-fund
	cd backend && uv sync

frontend-dev: ## Run Vite frontend dev server with HMR
	cd frontend && npm run dev

frontend-build: ## Build production Vue 3 + Tailwind SPA into frontend/dist
	cd frontend && npm run build

frontend-test: ## Run Vitest unit & component tests in frontend/
	cd frontend && npm run test

sdk-build: ## Build standalone TypeScript Sportradar Gismo SDK into sdk/dist
	cd sdk && npm run build

sdk-test: ## Run Vitest unit & integration tests for the Sportradar Gismo SDK in sdk/
	cd sdk && npm run test

backend-test: ## Run Pytest suite in backend/
	cd backend && uv run pytest -q

test: frontend-test sdk-test backend-test ## Run all frontend (Vitest), SDK (Vitest), and backend (Pytest) test suites

logos: ## Regenerate SVG and PNG logo assets (Option 7.3) in all sizes
	cp -f frontend/public/betscout-logo.svg frontend/public/favicon.svg
	cd backend && uv run python -c "from pathlib import Path; from betscout.pick_card import render_logo_png; r = Path('..'); render_logo_png(512, r/'frontend/public/betscout-logo.png'); render_logo_png(512, r/'frontend/public/icon-512.png'); render_logo_png(192, r/'frontend/public/icon-192.png'); render_logo_png(180, r/'frontend/public/apple-touch-icon.png')"

cards-gallery: ## Generate docs/png-notification-cards.html showcasing all PNG notification card designs
	cd backend && uv run python scripts/generate_cards_gallery.py

dev: frontend-build ## Build frontend/dist and start local BetScout server on http://127.0.0.1:8090
	cd backend && uv run python scripts/webapp.py --host $(HOST) --port $(PORT)

serve: ## Start local BetScout server on http://127.0.0.1:8090 (without rebuilding frontend)
	cd backend && uv run python scripts/webapp.py --host $(HOST) --port $(PORT)

sync: ## Settle finished paper-bets against official match results
	cd backend && uv run python scripts/paper_bet.py --settle-only

rescan: ## Settle paper-bets and rescan live/upcoming fixtures across all 10 sports
	cd backend && uv run python scripts/paper_bet.py --days 3

pipeline: ## Run full 4-stage ingestion, quality & model pipeline
	cd backend && uv run python scripts/daily_pipeline.py

deploy: ## Test, build frontend/dist, and deploy to Google Cloud Run + Firebase Hosting
	bash backend/scripts/deploy_cloud_run.sh

undeploy: ## Tear down Cloud Run service and Cloud Scheduler jobs
	bash backend/scripts/undeploy_cloud_run.sh

clean: ## Remove build artifacts and temporary caches
	rm -rf frontend/dist backend/.pytest_cache .pytest_cache
