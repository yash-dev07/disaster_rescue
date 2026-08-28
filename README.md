<div align="center">

# 🌊 FloodRescue

<img src="assets/banner.svg" alt="FloodRescue — fusing SOS signals and satellite imagery into ranked, human-verified rescue candidates" width="100%" />

**Tier 1 Academic MVP** — fuses last-known mobile SOS signals with satellite imagery
into ranked, human-verified candidate rescue locations.

[![License: MIT](https://img.shields.io/badge/license-MIT-2DD4BF.svg)](LICENSE)
[![Stack](https://img.shields.io/badge/stack-docker--compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Database](https://img.shields.io/badge/database-PostGIS-336791?logo=postgresql&logoColor=white)](https://postgis.net/)
[![Status](https://img.shields.io/badge/status-Tier%201%20Academic%20MVP-F59E0B)](#whats-real-vs-mocked)

<p>
<a href="#quickstart">Quickstart</a> ·
<a href="#how-it-works">How it works</a> ·
<a href="#architecture">Architecture</a> ·
<a href="#whats-real-vs-mocked">What's real</a> ·
<a href="#ethical-note">Ethical note</a>
</p>

</div>

---

<details>
<summary><b>Table of contents</b></summary>

- [Overview](#overview)
- [Key features](#key-features)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Quickstart](#quickstart)
- [Run the evaluation replay (Section 13)](#run-the-evaluation-replay-section-13)
- [Tests](#tests)
- [Project layout](#project-layout)
- [What's real vs. mocked](#whats-real-vs-mocked)
- [Two fixed bugs from the original spec](#two-fixed-bugs-from-the-original-spec)
- [Ethical note](#ethical-note)
- [Contributing](#contributing)

</details>

## Overview

FloodRescue is the **Tier 1** build described in [`project_brief.md`](project_brief.md): a self-contained way to explore how last-known mobile SOS pings and satellite imagery can be fused into a short, ranked list of candidate locations for human search-and-rescue teams to investigate. It runs entirely on synthetic and replayed data, behind a mock detector you can swap for a real trained model, in Docker Compose on a laptop.

No cloud account, telecom partner, or agency MoU required.

## Key features

- 📡 **Synthetic SOS ingestion** with realistic GPS noise, replayable for evaluation
- 🛰️ **Pluggable detector** — ships with a mock, ready to swap for a trained YOLOv8 model
- 🧮 **Corrected geospatial fusion math** (Section 3), backed by regression tests
- 🗺️ **Operator console** (React + PostGIS) for human review, verification, and rejection
- 🧾 **Full audit logging**, including a stubbed "would-dispatch" record that never reaches a real agency
- 🐳 **One-command local stack** — `make up` and you're running

## How it works

<div align="center">
<img src="assets/pipeline-diagram.svg" alt="Six-step FloodRescue pipeline: SOS ping, tile fetch and detection, fusion scoring, ranked candidates, human verification, audit-only log" width="68%" />
</div>

Every candidate that reaches an operator has already passed through the corrected Section 3 math — and every candidate that reaches a rescue conversation has already passed through a human. Section 0's fail-safe and consent checks hold at each stage.

## Architecture

<img src="assets/architecture-diagram.svg" alt="FloodRescue architecture: React console, FastAPI backend, Redis, Celery worker, PostGIS, and MinIO, all launched by docker compose" width="100%" />

`make up` starts six containers: Postgres+PostGIS, Redis, MinIO, the FastAPI backend, the Celery worker, and the React operator console — nothing to install or configure by hand beyond Docker itself.

## Quickstart

```bash
cp .env.example .env
make up
```

This starts: Postgres+PostGIS, Redis, MinIO, the FastAPI backend, the Celery worker, and the React operator console.

| Service | Address | Notes |
|---|---|---|
| API | http://localhost:8000 | docs at `/docs` |
| Operator console | http://localhost:5173 | React + Vite |
| MinIO console | http://localhost:9001 | user/pass: `floodrescue` / `floodrescue123` |

Open the console, go to **Send SOS**, submit a synthetic ping, and you'll be redirected to the incident page once the worker's mock detector produces a candidate (a few seconds).

<div align="center">
<img src="assets/console-mockup.svg" alt="Conceptual mockup of the operator console: ranked candidate cards next to a map with numbered pins" width="100%" />

<sub>Conceptual mockup — not an actual product screenshot. Real screenshots belong in <code>assets/</code> alongside this README once captured from a running stack.</sub>
</div>

## Run the evaluation replay (Section 13)

```bash
python3 tools/scripts/generate_synthetic_sos.py --count 10 --api http://localhost:8000
# or: make seed
```

Fires synthetic SOS pings with realistic GPS noise against the running stack and prints each resulting `incident_id`.

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

## What's real vs. mocked

| Component | Status |
|---|---|
| API contract (Section 2/6) | ✅ Real |
| PostGIS schema (Section 4) | ✅ Real |
| Geospatial fusion math (Section 3) | ✅ Real, bug-fixed — see `src/api/app/geo.py` and `tests/unit/test_geo.py` |
| Async worker pipeline shape | ✅ Real |
| Operator console | ✅ Real |
| Audit logging | ✅ Real |
| Fail-safe / consent checks (Section 0) | ✅ Real |
| Object detector & flood segmentation | 🔶 Mocked by design — `src/worker/worker/mock_detector.py`; swap-in guide in `src/models/README.md` |
| Satellite tile fetching | 🔶 Mocked — one synthetic tile ID used throughout |
| Dispatch (`/api/incidents/{id}/dispatch_log`) | ⛔ Stubbed, never live — records a "would-dispatch" audit entry only; nothing is sent to a real rescue agency (Section 0) |

## Two fixed bugs from the original spec

1. **`temporal_factor`** was capped at exactly the value it started at (`min(1.0, 1.0 + 0.1*(n_dup-1))`), so repeat detections never actually boosted confidence. Cap raised to **1.5**.
2. **Fused score sigmoid** only ever received inputs in `[0,1]`, which compresses every candidate's score into `[0.5, 0.73]` regardless of quality. Fixed with an explicit, tunable `SCALE` hyperparameter that rescales around the midpoint before the sigmoid.

Both are implemented in `src/api/app/geo.py` (and mirrored in `src/worker/worker/geo.py`), with regression tests in `tests/unit/test_geo.py` that would fail against the original, buggy versions.

## Ethical note

> Satellite/UAV resolution has real limits — people under trees or roofs may be missed. This system **assists** human rescue decision-making; it does **not** replace professional rescue authorization or judgment. See Section 22 of [`project_brief.md`](project_brief.md).

## Contributing

See [`.github/pull_request_template.md`](.github/pull_request_template.md) and the issue templates under [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/). Licensed under the [MIT License](LICENSE).

<div align="center">
<sub>Built for the evaluation replay in Section 13 — synthetic data, mocked detector, real math.</sub>
</div>
