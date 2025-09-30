
# ===== Project X Makefile =====
# Requires: docker, docker compose, (optional) GNU make

SHELL := /bin/bash

IMAGE_CPU := projectx:latest
IMAGE_GPU := projectx-gpu:latest
SERVICE_CPU := cpu
SERVICE_GPU := gpu

# -------- Help --------
help:
	@echo "Make targets:"
	@echo "  build           - docker compose build CPU service"
	@echo "  build-gpu       - docker compose build GPU service"
	@echo "  run             - run interactive CPU container (bash)"
	@echo "  run-gpu         - run interactive GPU container (bash)"
	@echo "  jupyter         - start Jupyter Lab (CPU) on http://localhost:8888"
	@echo "  jupyter-gpu     - start Jupyter Lab (GPU) on http://localhost:8888"
	@echo "  test            - run pytest inside CPU container"
	@echo "  lint            - ruff, black --check, isort --check-only"
	@echo "  format          - black + isort (format code)"
	@echo "  pre-commit      - run pre-commit on all files"
	@echo "  images          - list local docker images"
	@echo "  clean           - stop services and remove images (careful)"
	@echo ""

# -------- Build --------
build:
	docker compose build $(SERVICE_CPU)

build-gpu:
	docker compose build $(SERVICE_GPU)

# -------- Run shells --------
run:
	docker compose run --rm $(SERVICE_CPU) bash

run-gpu:
	docker compose run --rm $(SERVICE_GPU) bash

# -------- Jupyter --------
jupyter:
	docker compose run --rm -p 8888:8888 $(SERVICE_CPU) \
		jupyter lab --ip=0.0.0.0 --no-browser --allow-root

jupyter-gpu:
	docker compose run --rm -p 8888:8888 $(SERVICE_GPU) \
		jupyter lab --ip=0.0.0.0 --no-browser --allow-root

# -------- QA / Tests --------
test:
	docker compose run --rm $(SERVICE_CPU) pytest -q

lint:
	docker compose run --rm $(SERVICE_CPU) bash -lc "ruff check . && black --check . && isort --check-only ."

format:
	docker compose run --rm $(SERVICE_CPU) bash -lc "black . && isort ."

pre-commit:
	docker compose run --rm $(SERVICE_CPU) pre-commit run --all-files

# -------- Images / Clean --------
images:
	docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | sort -k2 -h

clean:
	- docker compose down --remove-orphans
	- docker rmi $(IMAGE_CPU) $(IMAGE_GPU)

.PHONY: help build build-gpu run run-gpu jupyter jupyter-gpu test lint format pre-commit images clean
