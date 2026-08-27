# FloodRescue — Tier 1 Academic MVP

Fuses last-known mobile SOS signals with satellite imagery into ranked,
human-verified candidate rescue locations. This is the **Tier 1** build from
[`project_brief.md`](project_brief.md) — synthetic/replayed data, a mock
detector you can swap for a real trained model, running entirely in Docker
Compose on a laptop. No cloud account, telecom partner, or agency MoU
required.

## Quickstart

```bash
cp .env.example .env
make up
```

This starts: Postgres+PostGIS, Redis, MinIO, the FastAPI backend, the Celery
worker, and the React operator console.

- API: http://localhost:8000 (docs at http://localhost:8000/docs)
- Operator console: http://localhost:5173
- MinIO console: http://localhost:9001 (user/pass: floodrescue / floodrescue123)

Open the console, go to **Send SOS**, submit a synthetic ping, and you'll be
redirected to the incident page once the worker's mock detector produces a
candidate (a few seconds).

## Run the evaluation replay (Section 13)

```bash
python3 tools/scripts/generate_synthetic_sos.py --count 10 --api http://localhost:8000
# or: make seed
```

Fires synthetic SOS pings with realistic GPS noise against the running
stack and prints each resulting `incident_id`.

## Tests

```bash
make test-unit          # pure logic (Section 3 formulas) - no stack needed
make up                 # in another terminal, leave running
make test-integration   # hits the live API end to end
```

## Project layout

```
.github/            CI workflow, issue/PR templates
assets/             logos, screenshots referenced from this README
build/              build/export output (gitignored, kept empty on checkout)
docs/               OpenAPI spec, evaluation plan write-up
src/
  api/              FastAPI backend - SOS ingest, incident/candidate endpoints, Section 3 formulas
  worker/           Celery worker - mock detector + Section 5 inference pipeline (Tier 1 version)
  frontend/         React operator console (Vite) - map, candidate cards, verify/reject
  models/           YOLOv8 training scripts (corrected CLI) + dataset notes (FloodNet/RescueNet)
tests/
  unit/             pure-logic tests, no DB/network (e.g. the Section 3 formula fixes)
  integration/      HTTP tests against a live `make up` stack
tools/
  infra/            PostGIS init.sql (Section 4 schema), loaded automatically by docker-compose
  scripts/          synthetic SOS generator for Section 13 replay evaluation
  openapi_codegen.sh
docker-compose.yml
Makefile
project_brief.md    the full corrected spec this build follows
```

## What's real vs. mocked right now

- **Real:** the API contract (Section 2/6), the PostGIS schema (Section 4),
  the corrected geospatial fusion math (Section 3 — see
  `src/api/app/geo.py` and its regression tests in `tests/unit/test_geo.py`),
  the async worker pipeline shape, the operator console, audit logging, and
  the fail-safe / consent checks from Section 0.
- **Mocked (by design, for Tier 1):** the object detector and flood
  segmentation model (`src/worker/worker/mock_detector.py` — see
  `src/models/README.md` for how to swap in a real trained YOLOv8 model),
  and satellite tile fetching (one synthetic tile ID is used throughout).
- **Stubbed, never live:** dispatch (`/api/incidents/{id}/dispatch_log`)
  only ever records a "would-dispatch" audit entry — nothing is sent to a
  real rescue agency. This is intentional per Section 0.

## Two fixed bugs from the original spec

1. **`temporal_factor`** was capped at exactly the value it started at
   (`min(1.0, 1.0 + 0.1*(n_dup-1))`), so repeat detections never actually
   boosted confidence. Cap raised to 1.5.
2. **Fused score sigmoid** only ever received inputs in `[0,1]`, which
   compresses every candidate's score into `[0.5, 0.73]` regardless of
   quality. Fixed with an explicit, tunable `SCALE` hyperparameter that
   rescales around the midpoint before the sigmoid.

Both are implemented in `src/api/app/geo.py` (and mirrored in
`src/worker/worker/geo.py`), with regression tests in
`tests/unit/test_geo.py` that would fail against the original, buggy
versions.

## Ethical note

Satellite/UAV resolution has real limits — people under trees or roofs may
be missed. This system assists human rescue decision-making; it does not
replace professional rescue authorization or judgment. See Section 22 of
[`project_brief.md`](project_brief.md).

## Contributing

See [`.github/pull_request_template.md`](.github/pull_request_template.md)
and the issue templates under [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/).
Licensed under the [MIT License](LICENSE).
