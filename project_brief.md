# FloodRescue — Corrected, Right-Sized Builder Prompt

> **How to use this file:** paste the whole thing into Claude Code (or another
> coding-capable AI) as the system/task prompt. It is a corrected version of a
> "FloodRescue" build spec — same core idea, but with a real formula bug fixed,
> outdated commands replaced, and scope split so a 3–4 person student team can
> actually finish Tier 1 in one project cycle instead of silently failing to
> reach a production spec that assumes AWS budget and NDRF partnerships.

---

## SCOPE NOTE — read this before anything else

This prompt has **two tiers**. Build Tier 1 first, completely, and demo it.
Everything in Tier 2 is real engineering (kept because it's good design), but
it is a *stretch goal / "here's how this would scale"* section — not something
a student team should attempt to fully implement.

| | **Tier 1 — Academic MVP (build this)** | **Tier 2 — Production vision (document, don't build)** |
|---|---|---|
| Imagery | Historical Sentinel-1/2 scenes for 2–3 known past flood events (Copernicus Data Space Ecosystem, free) | Live tasking of commercial SAR/drone imagery |
| Training data | FloodNet / RescueNet (public, pre-labeled) + a small self-collected supplement | Custom-labeled dataset from your own partner region |
| SOS input | Synthetic/simulated pings replayed against real event timelines | Live carrier/telecom integration |
| Partners | None required | NDRF / DRDO / ISRO / state disaster authorities |
| Infra | Docker Compose on a laptop or college server | AWS EKS + Helm + KMS in production |
| Verification | Replay historical incidents, measure localization error against known outcomes | Live field trial with volunteers and a partner agency |
| Dispatch | UI shows "recommended action"; no real dispatch integration | Authenticated dispatch handoff to an actual rescue agency system |

Everything below is labeled `[T1]` or `[T2]` so it's clear which tier it belongs to.

---

## 0 — Core principles & constraints (always enforce) `[T1]`

- Never auto-dispatch costly assets (helicopter/boat) without a verified human operator decision and appropriate legal authorization logs.
- Always include and surface uncertainty. Every candidate must carry a numeric `uncertainty_m` and a confidence breakdown.
- Privacy-first: store only `user_hash` by default; store PII only encrypted and access-logged. Consent required when possible.
- Provenance: every output must contain `sensor_id`, `acquisition_utc`, `processing_version`, and `model_version`.
- Auditable: every operator action (verify/reject/dispatch) must be immutable in an audit log.
- Fail safe: when imagery or network data is missing, the system must degrade gracefully (mark for manual triage) rather than guess silently.

## 1 — Mission, goals, success criteria `[T1]`

**Mission:** reduce time-to-locate for people stranded in floods by fusing last-known mobile location signals with remote-sensing imagery into ranked, human-verified candidate locations.

**Targets to evaluate against — not targets you're expected to hit with a semester of work and a few thousand images.** Report your actual measured numbers; a partial result honestly measured is worth more than a claimed number that isn't reproducible.

- Localization error: median ≤ 50 m for GPS-origin pings (top-1 candidate); ≤ 200 m for cell-tower-only pings (top-3).
- Precision@Top-1 ≥ 0.60 on your labeled validation set (this is what the score-calibration step in Section 3 is *for* — don't skip it).
- Processing latency: replayed-SOS → top candidate visible to operator, target ≤ 10 min in the demo pipeline.

If a target is unattainable with the data you actually have, say so explicitly in your report and explain what would close the gap (more imagery, a drone pass, human triage) — don't force-fit the number.

## 2 — Data schemas (copy exactly, keep every field) `[T1]`

### 2.1 SOS (incoming) — JSON
```json
{
  "source": "app|sms|carrier",
  "user_hash": "sha256_hex_string",
  "timestamp_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "coords": {"lat": 12.9715987, "lon": 77.5945627},
  "accuracy_m": 15.0,
  "comm_type": "gps|cell|sms",
  "cell_info": {
    "mcc": "404", "mnc": "10", "lac": 12345, "cid": 54321,
    "cell_center": {"lat": 12.970, "lon": 77.595},
    "cell_uncertainty_m": 1000
  },
  "rssi": -72,
  "battery_pct": 12,
  "optional_photo_url": "https://.../pic.jpg",
  "consent_flag": true,
  "app_version": "1.2.3",
  "device_make": "manufacturer",
  "device_model": "model"
}
```

### 2.2 Satellite tile metadata — JSON
```json
{
  "tile_id": "string",
  "sensor": "sentinel-1|sentinel-2|planet|maxar|skysat",
  "acquisition_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "bbox_lonlat": [0, 0, 0, 0],
  "resolution_m": 0.3,
  "cloud_cover_pct": 12.3,
  "polarization": "VV|VH|HH|HV|NA",
  "s3_url": "s3://bucket/path/to/tile.tif",
  "processing_level": "L1C|L2A|GRD"
}
```

### 2.3 Candidate output (alert) — JSON
```json
{
  "incident_id": "uuid-v4",
  "created_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "sos": { "...": "full sos copy" },
  "candidates": [
    {
      "candidate_id": "uuid",
      "lat": 12.9716,
      "lon": 77.5946,
      "score": 0.84,
      "uncertainty_m": 28.5,
      "confidence_components": {
        "image_confidence": 0.62,
        "location_likelihood": 0.75,
        "temporal_consistency": 0.9
      },
      "bounding_box_geojson": { "...": "polygon" },
      "best_crop_s3": "s3://.../crop.jpg",
      "detection_class": "person|boat|group",
      "source_tiles": ["tile_id1", "tile_id2"],
      "processing_version": "v1.0.0",
      "model_version": "detector-v20260819"
    }
  ],
  "top_candidate_id": "uuid",
  "recommended_action": "verify|task_drone|dispatch_boat|dispatch_helicopter",
  "provenance": {
    "processor_id": "string",
    "processing_utc": "YYYY-MM-DDTHH:MM:SSZ"
  }
}
```

## 3 — Geospatial math & fusion formulas (corrected) `[T1]`

### 3.1 Location likelihood heatmap
If GPS present: isotropic 2D Gaussian centered at `(lat0, lon0)`, `sigma = max(accuracy_m, 10)`. Convert to a local planar frame (UTM or EPSG:3857) before computing the Gaussian — don't apply it directly in lat/lon degrees, since degree-distance isn't uniform.

```
L_loc(x) = (1 / (2π·σ²)) · exp(-‖x - x0‖² / (2σ²))
```
Normalize so the heatmap integrates to 1 over the processing window.

If only a cell sector polygon is available: uniform density `1/A` inside the polygon, 0 outside. If only a tower center + uncertainty: isotropic Gaussian with `σ = cell_uncertainty_m`.

### 3.2 Image detection confidence — **bug fixed here**
For each detection `d` with model score `s` (0–1):

```
overlap_with_flood = IoU(d.bbox, flooded_mask)
```

> **Original bug:** `temporal_factor = min(1.0, 1.0 + 0.1*(n_dup-1))`. For any
> `n_dup ≥ 1`, `1.0 + 0.1*(n_dup-1) ≥ 1.0`, so the `min(1.0, …)` cap always wins
> and `temporal_factor` is **always exactly 1.0** — the "boost for repeat
> detections" never actually boosts anything. Fixed version:

```
temporal_factor = min(1.5, 1.0 + 0.1*(n_dup - 1))
```
where `n_dup` = number of distinct tiles/timepoints with a matching detection within 5 m and ±30 minutes. Now `n_dup=1 → 1.0`, `n_dup=2 → 1.1`, `n_dup=5 → 1.4`, capped at 1.5.

```
image_confidence = min(1.0, s * overlap_with_flood * temporal_factor)
```
(clip to 1.0 — the temporal boost can now push the product above 1 for a strong, repeated, high-overlap detection, and `image_confidence` is a [0,1] input to the next step, so it needs to stay bounded.)

### 3.3 Final fused score — **recalibrated here**
Features: `f1 = image_confidence`, `f2 = L_loc(candidate_point)`, `f3 = exp(-(t_now - t_sos)/τ)` with `τ = 21600s` default, `f4 = 1 - cloud_cover_pct/100`.

> **Original issue:** `z = w1*f1 + w2*f2 + w3*f3 + w4*f4 + b` with weights
> summing to 1 and `b=0` only ever produces `z ∈ [0,1]`. Feeding that narrow a
> range into a sigmoid gives `score ∈ [0.5, 0.73]` for *every* candidate,
> best or worst — the sigmoid is doing nothing useful. Fixed by rescaling
> before the sigmoid, with the scale as an explicit, calibratable hyperparameter:

```
raw   = w1*f1 + w2*f2 + w3*f3 + w4*f4 + b     # default w1=0.5, w2=0.35, w3=0.10, w4=0.05, b=0
SCALE = 8.0                                    # tune this against your validation set
z     = SCALE * (raw - 0.5)
score = 1 / (1 + exp(-z))
```
This spreads scores across roughly [0.02, 0.98] instead of [0.5, 0.73]. Tune `SCALE` (and optionally the weights) directly against the Precision@Top-1 ≥ 0.60 target from Section 1 — that's what the labeled validation set is for. Return `z` and each `wi*fi` contribution in `confidence_components` for explainability, as in the original.

## 4 — Database schema (PostGIS) `[T1]`
```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_hash varchar(128) NOT NULL,
  created_utc timestamptz NOT NULL DEFAULT now(),
  sos jsonb NOT NULL,
  geom geometry(Point, 4326),
  accuracy_m double precision,
  status varchar(32) DEFAULT 'new'
);

CREATE TABLE tiles (
  tile_id text PRIMARY KEY,
  sensor text,
  acquisition_utc timestamptz,
  bbox geometry(Polygon, 4326),
  resolution_m double precision,
  s3_url text
);

CREATE TABLE candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id uuid REFERENCES incidents(id),
  geom geometry(Point, 4326),
  score double precision,
  uncertainty_m double precision,
  detection_json jsonb,
  crop_s3 text,
  created_utc timestamptz DEFAULT now()
);

CREATE INDEX ON incidents USING GIST (geom);
CREATE INDEX ON tiles USING GIST (bbox);
CREATE INDEX ON candidates USING GIST (geom);
```

Useful queries (unchanged, correct as originally written):
```sql
-- candidates within 500m of an incident
SELECT c.*, ST_Distance(c.geom, i.geom) as dist_m
FROM candidates c JOIN incidents i ON c.incident_id = i.id
WHERE i.id = '<incident_uuid>'
  AND ST_DWithin(c.geom::geography, i.geom::geography, 500)
ORDER BY c.score DESC;

-- tiles overlapping an incident's buffered bbox
SELECT tile_id FROM tiles
WHERE ST_Intersects(bbox, (
  SELECT ST_Buffer(geom::geography, 2000)::geometry FROM incidents WHERE id='<incident_uuid>'
));
```

## 5 — ML models, training & inference `[T1 for MVP scope, commands corrected]`

**Models (baseline, unchanged — these are still reasonable current choices):**
- Flood segmentation: DeepLabV3+ with a ResNet-50 backbone (PyTorch).
- Object detection: YOLOv8-medium for speed, Faster R-CNN+FPN as a higher-accuracy fallback.
- Change detection (optional, Tier 2): a Siamese U-Net for before/after comparison.

**Training data — replaces "collect 2,000+500+1,000 images yourself":**
Labeling ~3,500 images from scratch is a multi-month full-time job, not a
component of a semester project. Use public, pre-labeled datasets instead:
- **FloodNet** — ~2,343 UAV images from post-Hurricane-Harvey flights, pixel-level semantic labels across 9–10 classes including building-flooded/non-flooded, road-flooded/non-flooded, water, vehicle, tree, pool. Directly matches this task.
- **RescueNet** — ~4,494 UAV images (post-Hurricane-Michael), with 4-level building damage annotations, complements FloodNet for the damage-severity angle.
- **xBD** — large pre/post-disaster satellite-imagery dataset for building damage, useful if you extend beyond UAV/drone-scale imagery to satellite-scale.

Fine-tune on these; use a *small* self-collected/self-labeled set (a few hundred crops from your own test-region imagery) only to adapt to your specific geography and sensor, not as your primary dataset.

**Training command — corrected.** The original (`python -m ultralytics.yolo.train`) calls a module path that doesn't exist in the current Ultralytics package structure and will fail. Current syntax:

```bash
pip install -U ultralytics
export DATASET_PATH=/workspace/datasets/floodrescue/yolov8

# train (current Ultralytics CLI — the console entry point is `yolo`, not `python -m ultralytics.yolo.train`)
yolo detect train data=${DATASET_PATH}/data.yaml model=yolov8m.pt imgsz=1024 epochs=80 batch=8 lr0=0.001

# export best model
yolo export model=runs/detect/train/weights/best.pt format=onnx
```
Note: default training already applies mosaic/HSV/flip augmentation via the hyperparameter config — there's no single `augment=True` training flag to set; augmentation strength is controlled by individual hyp values (`mosaic`, `mixup`, `hsv_h`, etc.) if you want to change it from the defaults.

**Inference pipeline (unchanged logic, still correct):**
1. For each tile intersecting the incident bbox: if optical and `cloud_cover_pct > 70`, skip optical and rely on SAR; else convert to reflectance and cloud-mask.
2. For SAR: radiometric correction → convert to dB → 3×3 Lee filter for speckle suppression.
3. Run flood segmentation → `flood_mask` (per-pixel probability).
4. Run object detector on each tile crop → detections with bbox + score.
5. Compute `image_confidence` per Section 3.2 (corrected formula); map bbox centroid to a geographic point.
6. Evaluate `L_loc(point)`; compute the fused `score` per Section 3.3 (corrected).
7. Store candidate in PostGIS; push to the operator UI.

**Streaming (Tier 1, simplified):** for a class project, a synchronous worker queue (Celery/RQ + Redis) processing SOS events one at a time is enough — you don't need a GPU worker pool or scheduled satellite-monitoring cron jobs (that's Tier 2, for continuous nationwide monitoring rather than event-triggered replay).

## 6 — API contract (OpenAPI) `[T1 — expanded to match Section 2.1]`

> **Original issue:** the OpenAPI `SOS` schema only defined 3 of the ~13 fields
> the prompt itself specifies in Section 2.1 (`source`, `user_hash`,
> `timestamp_utc`, `coords` — missing `accuracy_m`, `comm_type`, `cell_info`,
> `rssi`, `battery_pct`, `consent_flag`, etc.). An AI or developer building
> strictly from the OpenAPI spec would silently drop most of the schema.
> Expanded below to match.

(See `docs/openapi.yaml` in this repo for the full, expanded spec.)
Generate a Python client with `openapi-generator` in CI, as originally specified (`docs/openapi_codegen.sh`).

## 7 — Operator UI micro-flows `[T1]`

**Main screen:** incident header (id, sos_time, source, consent_flag, battery_pct, recommended action). Map pane (Mapbox GL or Leaflet): SOS uncertainty circle (radius = `accuracy_m` or derived), flood-mask polygon, candidate pins colored by score. Right panel: top-5 candidate cards, each with crop image, score breakdown bar (`image_confidence`, `location_likelihood`, `time_decay`), distance to SOS, and Verify / Reject / Request-Drone / Dispatch buttons. Audit log modal listing every operator action with timestamp and operator ID.

**Verify flow:** operator clicks Verify → `POST /api/incidents/{id}/verify` with `{candidate_id, operator_id, verified: true}` → backend logs the action and sets `candidate.status = 'verified'`. The system then *shows* dispatch options but — per Section 0 — never sends anything itself; a real dispatch integration is Tier 2 and needs an authorized-account model, which a student project should stub out (log the "would-dispatch" event) rather than wire to a live agency.

## 8 — Infra `[T1 default: Docker Compose. T2: the rest.]`

**Tier 1 — what to actually run:**
```yaml
# docker-compose.yml services
# api        — FastAPI + Uvicorn
# worker     — Celery (or RQ) + Redis
# postgres   — postgis/postgis image
# minio      — S3-compatible local storage for tiles/crops
# redis      — broker
# frontend   — React (Vite)
```
`Makefile` targets: `make up`, `make test`, `make lint`, `make build`. This runs entirely on a laptop or a single free-tier/college VM — no cloud account required to demo it.

**Tier 2 — production, document but don't build:** GPU node pool, HPA for API/inference workers, Helm charts, S3 + RDS(Aurora) + EKS/GKE. Keep this section in your report as "how this would scale," not as a build target.

## 9 — Security & privacy checklist `[T1, right-sized]`

- TLS for all endpoints (even in the local demo — self-signed is fine for a defense demo, but show you did it).
- Secrets via environment variables + `.env` (local) / a secrets manager (Tier 2, e.g. cloud KMS) — never commit keys.
- PII (if any real PII is used at all, which it shouldn't be for the MVP — use `user_hash` and synthetic data) encrypted at the field level.
- RBAC for the UI: operator / auditor / admin roles, even if just 3 hardcoded role types for the demo.
- Audit logs append-only (a Postgres table with no UPDATE/DELETE grants is enough for T1; object-lock S3 retention is T2).
- Run a container scan (Trivy is free and fast) before your final demo — an actual finding here is a good line in your security-requirements writeup.

## 10 — Legal / partner considerations `[T2 — do not treat as a requirement]`

The original spec suggested outreach to NDRF, DRDO, and ISRO with a formal MoU template. **For the academic project, skip this entirely.** No partnership is required to build or evaluate Tier 1 — you're using public satellite archives and historical/synthetic data, not live operational data, so there's nothing to formally share. Keep the MoU skeleton (purpose/scope, data types, consent, liability, dispatch authorization, confidentiality) in your report's appendix as evidence you thought about what real deployment would require — that's genuinely good engineering practice to demonstrate, just not something to chase in a semester.

## 11 — Dataset formatting standards `[T1]`

(Volume requirements are covered in Section 5 — this is format only.)
- Detection: COCO format. Per-image GeoJSON boxes with `tile_id`, `acquisition_utc`, `source_sensor`, `labeler_id`, `qc_score`.
- Segmentation: GeoTIFF masks, one band per tile, float `[0,1]`.
- **Split by event, not randomly across images** — e.g., train on FloodNet's Harvey imagery, hold out a different event's imagery for validation, so you're testing generalization rather than memorizing one flood's visual signature.

## 12 — CI, tests & acceptance checks `[T1]`

- **Unit:** API validation (`pytest`) — invalid `POST /api/sos` → 400; valid → 201 + incident created.
- **Integration:** synthetic SOS → worker processes a pre-stored sample tile → candidate saved → `GET /api/incidents/{id}` returns it.
- **Model smoke test:** confirm the model loads and output matches the schema in Section 2.3 — don't gate CI on an mAP threshold for a student project; log it, don't fail the build on it.
- **Security:** Trivy container scan in the pipeline.

## 13 — Evaluation plan `[T1 — replaces "live field trial"]`

(See `docs/evaluation_plan.md` in this repo for the full write-up.)

## 14–16 — Deliverables, tech defaults, starter task `[T1]`

**Deliverables:** `project_brief.md` (this file, in repo root); runnable MVP via `docker-compose up` with `POST /api/sos`, Celery worker, PostGIS, MinIO, React UI showing real (not mocked, once Section 5 model is trained) top candidates; OpenAPI spec + generated Python client; training notebook + small sample model weights (not the full dataset — link to FloodNet/RescueNet instead); labeling-format guide; test suite; evaluation report from Section 13.

**Tech defaults:** Python 3.11 (FastAPI backend), Node 18+ (React frontend), Redis+Celery, PostgreSQL 15+PostGIS, MinIO (local)/S3-compatible, PyTorch 2.x + Ultralytics YOLOv8, Docker + Compose (Helm only if you choose to demonstrate the T2 path). No default cloud provider required for T1; if you do want a cloud demo, any provider's free tier / student credits (a single VM running Compose) is enough — you don't need EKS.

**Starter task (do this first):**
1. Scaffold `/api /worker /models /frontend /infra /docs`.
2. Implement `POST /api/sos` → PostGIS insert → return `incident_id`, with one integration test.
3. Mock worker: on new incident, fetch one pre-stored sample tile, run a *mock* detector (returns one synthetic candidate near the SOS point using the corrected Section 3 formulas), store candidate, set `status='candidate_ready'`.
4. React page `/incident/{id}`: map, SOS circle, the candidate crop, Verify/Reject buttons.
5. `docker-compose.yml` + `Makefile` to run it all locally.
6. **Only after this works end-to-end with a mock detector**, swap in the real trained YOLOv8/DeepLabV3+ models from Section 5.

## 17 — Failure modes & mitigations `[T1, unchanged — this was already correct]`

- No imagery available → mark `needs_imagery`, suggest drone tasking (logged, not executed) or manual triage.
- All imagery cloud-covered → fall back to SAR; if unavailable, escalate to manual triage.
- High false-positive rate → tighten thresholds, require multi-temporal confirmation before surfacing a candidate.
- No carrier cooperation → app-based SOS + SMS fallback only (this is your realistic path for T1 anyway).

## 18 — Metrics to expose `[T1]`
SOS ingestion rate; processing latency (median, p95) from SOS → candidate_ready; inference time per tile; segmentation/detection accuracy per model version; operator verify rate and average verification time.

## 19 — Glossary `[unchanged]`
SOS: emergency signal from device/carrier. SAR: Synthetic Aperture Radar. IoU: Intersection over Union. mAP: mean Average Precision. PostGIS: spatial extension for PostgreSQL. Tile: georeferenced raster chunk covering a bbox.

## 20 — What every status update to a human must include `[unchanged, good as-is]`
What was processed (incident_id, sos_time, bbox); which sensors and acquisition times were used; top candidate(s) with lat/lon, score, uncertainty, crop preview; recommended next step and *why* (top contributing features from Section 3.3's `confidence_components`).

## 21 — This is your actual build target
Sentinel-2 optical only (no SAR — that's a T2 addition once optical works), synthetic/replayed SOS pings against historical events, FloodNet/RescueNet for training data, mock detector first then real model, Docker Compose only. Everything else in this document is context for *why* the pipeline is shaped the way it is, and a roadmap for what you'd say when a professor or judge asks "how would this scale to production."

## 22 — Ethical note (include in your README and any public-facing doc) `[unchanged, this was already right]`
State the limits of satellite/UAV resolution — people under trees or roofs may be missed. State clearly that this system assists human rescue decision-making and does not replace professional rescue authorization or judgment. State your data retention and protection commitments, even for a demo using synthetic data.

---

## Appendix — verified, current data sources for an India-context build

| Source | What it gives you | Access |
|---|---|---|
| **Copernicus Data Space Ecosystem** (`dataspace.copernicus.eu`) | Sentinel-1 (SAR) and Sentinel-2 (optical) imagery, current archive | Free, registration required. Note: the old `sentinelsat`/Copernicus Open Access Hub route has been dead since October 2023 — use CDSE's own APIs (OData, or the bundled Sentinel Hub Catalog/Process APIs), not older tutorials that assume the retired hub. |
| **Google Flood Forecasting API (Flood Hub)** | Real-time and historical river-level flood forecasts; historical flood dataset (1999–2020) and global runoff reanalysis (1980–2023) under CC BY 4.0 | Free, but gated behind a waitlist/approval form and a Google Cloud API key — apply early in your project timeline, don't assume same-day access. |
| **CWC C-FLOOD** | India's new (2026) unified flood-forecasting system (CWC + C-DAC + NRSC), currently live for the Mahanadi, Godavari, and Tapi basins with 2-D hydrodynamic modeling | Public-facing web system; treat as a reference/validation point for your novelty section, not as a guaranteed integration. Worth a direct email to CWC/NRSC to ask about data access for an academic project. |
| **FloodWatch India** (CWC mobile app) | Real-time flood forecasts from 592+ monitoring stations nationwide | Public mobile app; same caveat as above. |
| **Bhuvan (ISRO/NRSC)** | DEM/elevation, historical flood-hazard and inundation layers for India | Public portal; check current API/download terms at time of use. |
