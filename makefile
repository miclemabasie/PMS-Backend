# ----------------------------------------------------------------------------
# Django Starter Makefile
# ----------------------------------------------------------------------------

# Load environment variables from .env file (if present)
ifneq (,$(wildcard ./.env))
	include .env
	export
	ENV_FILE_PARAM = --env-file .env
endif

# ----------------------------------------------------------------------------
# Project Configuration
# ----------------------------------------------------------------------------
# Automatically detect project name from environment or directory.
# Override by setting PROJECT_NAME_ENV in .env.
PROJECT_NAME ?= $(or $(PROJECT_NAME_ENV), $(shell basename $(CURDIR)))
ifeq ($(PROJECT_NAME),)
	PROJECT_NAME = djangostarter
endif

# PostgreSQL settings – read from .env, fallback to defaults
PG_USER ?= $(or $(POSTGRES_USER), postgresadmin)
PG_DB   ?= $(or $(POSTGRES_DB), $(PROJECT_NAME))

# ----------------------------------------------------------------------------
# Docker Compose Commands
# ----------------------------------------------------------------------------
build:
	docker compose up --build -d --remove-orphans

up:
	docker compose up -d

down:
	docker compose down

down-v:
	docker compose down -v

restart: down up

logs:
	docker compose logs -f

api-logs:
	docker compose logs --follow api

nginx-logs:
	docker compose logs --follow nginx

ps:
	docker compose ps

config:
	docker compose config

# ----------------------------------------------------------------------------
# Django Management Commands
# ----------------------------------------------------------------------------
migrate:
	docker compose exec api python manage.py migrate

makemigrations:
	docker compose exec api python manage.py makemigrations

show-urls:
	docker compose exec api python manage.py show_urls

check:
	docker compose exec api python manage.py check

django-check: check

createsuperuser:
	docker compose exec api python manage.py createsuperuser

collectstatic:
	docker compose exec api python manage.py collectstatic --no-input --clear

shell:
	docker compose exec api python manage.py shell_plus

shell-plain:
	docker compose exec api python manage.py shell

# ----------------------------------------------------------------------------
# Database Commands
# ----------------------------------------------------------------------------
init-db:
	docker compose exec api python manage.py db_init 30

psql:
	docker compose exec postgres-db psql --username=$(PG_USER) --dbname=$(PG_DB)

dump-db:
	@mkdir -p backups
	docker compose exec postgres-db pg_dump --username=$(PG_USER) $(PG_DB) > ./backups/$(PROJECT_NAME)_$(shell date +%Y%m%d_%H%M%S).sql

restore-db:
	@echo "Usage: make restore-db FILE=backup.sql"
	docker compose exec -T postgres-db psql --username=$(PG_USER) --dbname=$(PG_DB) < $(FILE)

# ----------------------------------------------------------------------------
# Elasticsearch Commands
# ----------------------------------------------------------------------------
migrate-elasticsearch:
	docker compose exec api python manage.py search_index --rebuild

# ----------------------------------------------------------------------------
# Testing & Code Quality
# ----------------------------------------------------------------------------
test:
	docker compose exec api pytest -p no:warnings --cov=.

test-html:
	docker compose exec api pytest -p no:warnings --cov=. --cov-report html

flake8:
	docker compose exec api flake8

black-check:
	docker compose exec api black --check --exclude=migrations .

black-diff:
	docker compose exec api black --diff --exclude=migrations .

black:
	docker compose exec api black --exclude=migrations .

isort-check:
	docker compose exec api isort . --check-only --skip env --skip migrations

isort-diff:
	docker compose exec api isort . --diff --skip env --skip migrations

isort:
	docker compose exec api isort . --skip env --skip migrations

lint: flake8 black-check isort-check

format: black isort

# ----------------------------------------------------------------------------
# API Schema Generation
# ----------------------------------------------------------------------------
schema-yaml:
	docker compose exec api python manage.py spectacular --file schema.yaml

schema-json:
	docker compose exec api python manage.py spectacular --file schema.json

# ----------------------------------------------------------------------------
# Development Tools
# ----------------------------------------------------------------------------
watch:
	docker compose exec api watchmedo shell-command \
		--patterns="*.py" \
		--recursive \
		--command='make lint test' .

# ----------------------------------------------------------------------------
# Project Setup & Maintenance – ✅ RUN INSIDE CONTAINER
# ----------------------------------------------------------------------------
email-setup:
	docker compose exec api python manage.py setup_email_config

rename:
	@read -p "Enter new project name: " name; \
	python manage.py rename_project $$name --clean --force
	@echo "✅ Project renamed to $$name."
	@echo "👉 Run 'make down && make up --build' to rebuild with new name."

# ----------------------------------------------------------------------------
# Docker Volume Management – ✅ Uses dynamic PROJECT_NAME
# ----------------------------------------------------------------------------
volume-list:
	docker volume ls --filter name=$(PROJECT_NAME)

volume-inspect:
	docker volume inspect $(PROJECT_NAME)-app_postgres_data

volume-rm:
	docker volume rm $(PROJECT_NAME)-app_postgres_data

# ----------------------------------------------------------------------------
# Cleanup
# ----------------------------------------------------------------------------
clean: down-v
	docker system prune -f
	docker volume prune -f
	@echo "✅ Cleaned up Docker system and volumes."

# ----------------------------------------------------------------------------
# Help
# ----------------------------------------------------------------------------
help:
	@echo "Django Starter Makefile"
	@echo "======================="
	@echo ""
	@echo "Project: $(PROJECT_NAME)"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Docker Compose:"
	@echo "  build            - Build and start containers with --build"
	@echo "  up               - Start all services"
	@echo "  down             - Stop all services"
	@echo "  down-v           - Stop and remove volumes"
	@echo "  restart          - Restart all services"
	@echo "  logs             - Tail all logs"
	@echo "  api-logs         - Tail API logs"
	@echo "  nginx-logs       - Tail Nginx logs"
	@echo "  ps               - List running containers"
	@echo "  config           - Validate compose file"
	@echo ""
	@echo "Django:"
	@echo "  migrate          - Run migrations"
	@echo "  makemigrations   - Create migrations"
	@echo "  show-urls        - List all URL patterns"
	@echo "  check            - Run Django system check"
	@echo "  createsuperuser  - Create admin user"
	@echo "  collectstatic    - Collect static files"
	@echo "  shell            - Django shell_plus"
	@echo "  shell-plain      - Plain Django shell"
	@echo ""
	@echo "Database:"
	@echo "  init-db          - Initialize database with sample data"
	@echo "  psql             - Open PostgreSQL CLI"
	@echo "  dump-db          - Dump database to backups/"
	@echo "  restore-db       - Restore database from file (FILE=path)"
	@echo ""
	@echo "Elasticsearch:"
	@echo "  migrate-elasticsearch - Rebuild search index"
	@echo ""
	@echo "Testing & Linting:"
	@echo "  test             - Run pytest with coverage"
	@echo "  test-html        - Run pytest with HTML coverage report"
	@echo "  flake8           - Run flake8"
	@echo "  black-check      - Check code formatting"
	@echo "  black-diff       - Show black diff"
	@echo "  black            - Apply black formatting"
	@echo "  isort-check      - Check import sorting"
	@echo "  isort-diff       - Show isort diff"
	@echo "  isort            - Apply isort"
	@echo "  lint             - Run all linters"
	@echo "  format           - Apply black + isort"
	@echo ""
	@echo "API Schema:"
	@echo "  schema-yaml      - Generate OpenAPI schema (YAML)"
	@echo "  schema-json      - Generate OpenAPI schema (JSON)"
	@echo ""
	@echo "Development:"
	@echo "  watch            - Auto-run linters/tests on file change"
	@echo ""
	@echo "Setup & Maintenance:"
	@echo "  email-setup      - Configure default email templates"
	@echo "  rename           - Rename the entire project (run inside Docker)"
	@echo ""
	@echo "Volumes:"
	@echo "  volume-list      - List project volumes"
	@echo "  volume-inspect   - Inspect PostgreSQL volume"
	@echo "  volume-rm        - Remove PostgreSQL volume"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean            - Full system cleanup"
	@echo ""
	@echo "Help:"
	@echo "  help             - Show this message"