# Marking Assistant — see CLAUDE.md for what each target is for.
#
# Targets with nothing to do yet exit 0 with a message rather than failing,
# so the full sequence stays runnable from the first day of the project.
#
# Windows note: GNU Make falls back to cmd.exe when no POSIX sh is on PATH,
# and cmd cannot execute a forward-slash path in command position. Paths are
# therefore OS-conditional and recipes avoid POSIX-only syntax.

ifeq ($(OS),Windows_NT)
  PY      := apps\api\.venv\Scripts\python.exe
  RUFF    := apps\api\.venv\Scripts\ruff.exe
  MYPY    := apps\api\.venv\Scripts\mypy.exe
  ALEMBIC := ..\..\apps\api\.venv\Scripts\alembic.exe
  BLANK   := @echo.
else
  PY      := apps/api/.venv/bin/python
  RUFF    := apps/api/.venv/bin/ruff
  MYPY    := apps/api/.venv/bin/mypy
  ALEMBIC := ../../apps/api/.venv/bin/alembic
  BLANK   := @echo ""
endif

COMPOSE := docker compose

.DEFAULT_GOAL := help
.PHONY: help venv install dev down clean logs test test-api test-web lint lint-api \
        lint-web typecheck typecheck-api typecheck-web fmt migrate seed evaluate \n        evaluate-strict build ci

help: ## List targets
	@echo Marking Assistant
	$(BLANK)
	@echo   make dev         bring the stack up (api, worker, postgres, redis, minio)
	@echo   make down        stop it, keep volumes
	@echo   make clean       stop it, destroy volumes
	@echo   make logs        tail the stack
	$(BLANK)
	@echo   make install     install backend and frontend dependencies
	@echo   make test        pytest + vitest
	@echo   make lint        ruff + tsc
	@echo   make typecheck   mypy + tsc
	@echo   make fmt         ruff format
	@echo   make build       production build of both clients
	@echo   make ci          lint + typecheck + test, exactly as CI runs it
	$(BLANK)
	@echo   make migrate     alembic upgrade head
	@echo   make seed        load development fixtures
	@echo   make evaluate    CER/WER/QWK against the golden set

venv: ## Create the backend virtualenv
	python -m venv apps/api/.venv

install: ## Install backend and frontend dependencies
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "apps/api[dev]"
	pnpm install

dev: ## Bring the full stack up
	$(COMPOSE) up -d --build --wait
	$(COMPOSE) exec -T api curl -fsS http://localhost:8000/healthz
	$(BLANK)
	@echo api      http://localhost:8000/healthz
	@echo docs     http://localhost:8000/docs
	@echo minio    http://localhost:9001

down: ## Stop the stack, keep volumes
	$(COMPOSE) down

clean: ## Stop the stack and destroy volumes
	$(COMPOSE) down -v

logs: ## Tail the stack
	$(COMPOSE) logs -f --tail=100

test: test-api test-web ## Run every test

test-api:
	$(PY) -m pytest apps/api -q

test-web:
	pnpm -r --if-present test

lint: lint-api lint-web ## Lint everything

lint-api:
	$(RUFF) check apps/api
	$(RUFF) format --check apps/api

lint-web:
	pnpm -r --if-present lint

typecheck: typecheck-api typecheck-web ## Static types, backend and frontend

typecheck-api:
	$(MYPY) --config-file apps/api/pyproject.toml apps/api/app

typecheck-web:
	pnpm -r --if-present typecheck

fmt: ## Format
	$(RUFF) format apps/api
	$(RUFF) check apps/api --fix

migrate: ## Apply database migrations
	cd apps/api && $(ALEMBIC) upgrade head

seed: ## Load development fixtures
	@echo seed: nothing to load yet - fixtures arrive with the first models at stage 1 (docs/TASKS.md)

# No `cd` here, unlike migrate: the api package is pip-installed editable, so
# `app` imports from any directory, and the CLI resolves the golden set from
# its own location. Avoiding the `cd` also avoids a relative Windows path,
# which cmd.exe accepts and sh silently mangles.
evaluate: ## CER/WER/QWK against the golden set
	$(PY) -m app.evaluation.cli $(ARGS)

evaluate-strict: ## As above, but exit non-zero unless every gate passes
	$(PY) -m app.evaluation.cli --strict $(ARGS)

build: ## Production build of both clients
	pnpm -r --if-present build

ci: lint typecheck test ## Exactly what CI runs
