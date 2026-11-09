# RUN_MODE из .env выбирает оверлей: docker-compose.$(RUN_MODE).yml поверх
# docker-compose.yml
RUN_MODE ?= dev
ifneq (,$(wildcard .env))
  RUN_MODE := $(shell grep -E '^RUN_MODE=' .env 2>/dev/null | tail -1 | cut -d= -f2- \
    | tr -d " '\"" )
endif
ifeq ($(RUN_MODE),)
  RUN_MODE := dev
endif
export RUN_MODE

COMPOSE_FILES = -f ./docker-compose.yml -f ./docker-compose.$(RUN_MODE).yml \
	-f ./docker-compose.local.yml
COMPOSE = docker compose $(COMPOSE_FILES)
DEV_COMPOSE = RUN_MODE=dev docker compose -f ./docker-compose.yml \
	-f ./docker-compose.dev.yml -f ./docker-compose.local.yml

.PHONY: init check_environment env-prepare docker-setup compose-build compose-up \
	compose-down compose-restart compose-logs compose-ps fix-code check-code

init: check_environment env-prepare docker-setup

check_environment:
	@command -v docker >/dev/null 2>&1 || { \
		echo "Docker is not installed or is not available in PATH."; \
		exit 1; \
	}
	@docker compose version >/dev/null 2>&1 || { \
		echo "Docker Compose plugin is not available."; \
		exit 1; \
	}
	@test -f .env.example || { \
		echo "Missing .env.example file."; \
		exit 1; \
	}
	@test -f "./docker-compose.$(RUN_MODE).yml" || { \
		echo "Missing docker-compose.$(RUN_MODE).yml"; \
		exit 1; \
	}

env-prepare:
	@echo "Подготавливаю окружение..."
	@# Новый .env: свои UID и GID — api пишет книгу от имени того, кто запускает, — и
	@# свой секрет office. Готовый .env не трогаем
	@if [ ! -f .env ]; then \
		secret=$$(openssl rand -hex 32 2>/dev/null \
			|| head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'); \
		sed -e "s/^UID=.*/UID=$$(id -u)/" -e "s/^GID=.*/GID=$$(id -g)/" \
			-e "s/^OFFICE__JWT_SECRET=.*/OFFICE__JWT_SECRET=$$secret/" \
			.env.example > .env; \
		echo "Создан .env: UID $$(id -u), GID $$(id -g), новый секрет office"; \
	fi
	@if [ ! -f docker-compose.local.yml ]; then \
		printf 'services: {}\n' > docker-compose.local.yml; \
	fi
	@mkdir -p ./deploy/book ./deploy/fonts

docker-setup: compose-down compose-build compose-up
	@echo "Окружение готово к использованию."

# Compose 5 собирает только через bake, а сборку в сети хоста (network: host) bake
# пускает лишь с --allow, которого compose ему не передаёт. Поэтому собираем bake
# напрямую: он читает те же compose-файлы
compose-build:
	@echo "Приступаю к сборке образов (RUN_MODE=$(RUN_MODE))..."
	@docker buildx bake --allow=network.host $(COMPOSE_FILES)

compose-up:
	@echo "Запускаю контейнеры (RUN_MODE=$(RUN_MODE))..."
	@$(COMPOSE) up -d

compose-down:
	@echo "Останавливаю контейнеры (RUN_MODE=$(RUN_MODE))..."
	@$(COMPOSE) down || true

compose-restart:
	@echo "Перезапускаю контейнеры (RUN_MODE=$(RUN_MODE))..."
	@$(COMPOSE) restart

compose-logs:
	@$(COMPOSE) logs -f

compose-ps:
	@$(COMPOSE) ps

fix-code: env-prepare
	@echo "Исправляю код через ruff..."
	@$(DEV_COMPOSE) run --rm --no-deps api sh -c ' \
		ruff check --fix --no-cache && \
		ruff format --no-cache'

check-code: env-prepare
	@echo "Проверяю код через ruff и mypy..."
	@$(DEV_COMPOSE) run --rm --no-deps api sh -c ' \
		ruff format --check --no-cache && \
		ruff check --no-cache && \
		mypy --cache-dir=/tmp/mypy_cache'
