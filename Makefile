# BetScout Monorepo Makefile (app/ Vue 3 + Tailwind SPA & api/ Python Quant Engine)
SHELL := /bin/bash
export PATH := /opt/homebrew/bin:/usr/local/bin:$(PATH)

HOST ?= 127.0.0.1
PORT ?= 8090

.PHONY: help install dev serve app-dev app-build app-test frontend-dev frontend-build frontend-test sdk-build sdk-test api-test backend-test test logos cards-gallery sync rescan pipeline deploy undeploy clean

help: ## Show all available Makefile commands
	@echo "BetScout — Quantitative Sports Edge & Score Intelligence"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install app (npm), sdk (npm), and api (uv) dependencies
	cd app && npm install --no-audit --no-fund
	cd sdk/typescript && npm install --no-audit --no-fund
	cd api && uv sync

app-dev: ## Run Vite app dev server with HMR
	cd app && npm run dev

app-build: ## Build production Vue 3 + Tailwind SPA into app/dist
	cd app && npm run build

app-test: ## Run Vitest unit & component tests in app/
	cd app && npm run test

frontend-dev: app-dev
frontend-build: app-build
frontend-test: app-test

sdk-build: ## Build standalone TypeScript SDK into sdk/typescript/dist
	cd sdk/typescript && npm run build

sdk-test: ## Run Vitest & Pytest suites for TypeScript and Python SDKs
	cd sdk/typescript && npm run test
	cd sdk/python && PYTHONPATH=src ../../api/.venv/bin/pytest -q

api-test: ## Run Pytest suite in api/
	cd api && uv run pytest -q

backend-test: api-test

test: app-test sdk-test api-test ## Run all app (Vitest), SDK (Vitest + Pytest), and api (Pytest) test suites

logos: ## Regenerate SVG and PNG logo assets (Option 7.3) in all sizes
	cp -f app/public/betscout-logo.svg app/public/favicon.svg
	cd api && uv run python -c "from pathlib import Path; from betscout.pick_card import render_logo_png; r = Path('..'); render_logo_png(512, r/'app/public/betscout-logo.png'); render_logo_png(512, r/'app/public/icon-512.png'); render_logo_png(192, r/'app/public/icon-192.png'); render_logo_png(180, r/'app/public/apple-touch-icon.png')"

cards-gallery: ## Generate docs/png-notification-cards.html showcasing all PNG notification card designs
	cd api && uv run python scripts/generate_cards_gallery.py

dev: app-build ## Build app/dist and start local BetScout server on http://127.0.0.1:8090
	cd api && uv run python scripts/webapp.py --host $(HOST) --port $(PORT)

serve: ## Start local BetScout server on http://127.0.0.1:8090 (without rebuilding app)
	cd api && uv run python scripts/webapp.py --host $(HOST) --port $(PORT)

sync: ## Settle finished paper-bets against official match results
	cd api && uv run python scripts/paper_bet.py --settle-only

rescan: ## Settle paper-bets and rescan live/upcoming fixtures across all 10 sports
	cd api && uv run python scripts/paper_bet.py --days 3

pipeline: ## Run full 4-stage ingestion, quality & model pipeline
	cd api && uv run python scripts/daily_pipeline.py

deploy: ## Test, build app/dist, and deploy to Google Cloud Run + Firebase Hosting
	bash api/scripts/deploy_cloud_run.sh

undeploy: ## Tear down Cloud Run service and Cloud Scheduler jobs
	bash api/scripts/undeploy_cloud_run.sh

clean: ## Remove build artifacts and temporary caches
	rm -rf app/dist api/.pytest_cache .pytest_cache
