.PHONY: up down build test test-unit test-integration lint logs seed clean

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

# Unit tests: pure logic (Section 3 formulas), no DB/network needed.
# Runs inside the api container so it uses the same deps as production.
test-unit:
	docker compose run --rm api pytest -q /tests/unit

# Integration tests: hit a live, already-running stack over HTTP.
# Run `make up` in another terminal first.
test-integration:
	pip install -q --break-system-packages requests pytest 2>/dev/null || pip install -q requests pytest
	FLOODRESCUE_API_URL=http://localhost:8000 python3 -m pytest -q tests/integration

test: test-unit

lint:
	docker compose run --rm api sh -c "pip install ruff -q && ruff check app"
	docker compose run --rm worker sh -c "pip install ruff -q && ruff check worker"

logs:
	docker compose logs -f

# Section 13 evaluation helper: fire N synthetic SOS pings at the running stack.
seed:
	python3 tools/scripts/generate_synthetic_sos.py --count 5 --api http://localhost:8000

clean:
	docker compose down -v
