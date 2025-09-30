# ==== Vars ====
IMAGE_CPU=projectx:latest
IMAGE_GPU=projectx-gpu:latest
SERVICE_CPU=cpu
SERVICE_GPU=gpu

# ==== Build images ====
build:
	docker compose build $(SERVICE_CPU)

build-gpu:
	docker compose build $(SERVICE_GPU)

# ==== Run interactive shells ====
run:
	docker compose run --rm $(SERVICE_CPU) bash

run-gpu:
	docker compose run --rm $(SERVICE_GPU) bash

# ==== Jupyter (CPU/GPU) ====
jupyter:
	docker compose run --rm -p 8888:8888 $(SERVICE_CPU) \
		jupyter lab --ip=0.0.0.0 --no-browser --allow-root

jupyter-gpu:
	docker compose run --rm -p 8888:8888 $(SERVICE_GPU) \
		jupyter lab --ip=0.0.0.0 --no-browser --allow-root

# ==== Tests / Lint ====
test:
	docker compose run --rm $(SERVICE_CPU) pytest -q

lint:
	docker compose run --rm $(SERVICE_CPU) ruff check .
	docker compose run --rm $(SERVICE_CPU) black --check .
	docker compose run --rm $(SERVICE_CPU) isort --check-only .

format:
	docker compose run --rm $(SERVICE_CPU) black .
	docker compose run --rm $(SERVICE_CPU) isort .

pre-commit:
	docker compose run --rm $(SERVICE_CPU) pre-commit run --all-files

# ==== Clean ====
clean:
	-docker compose down --remove-orphans
	-docker rmi $(IMAGE_CPU) $(IMAGE_GPU)

.PHONY: build build-gpu run run-gpu jupyter jupyter-gpu test lint format pre-commit clean
