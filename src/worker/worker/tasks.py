"""
Section 5 inference pipeline, Tier-1/mock-detector version:
  1. Fetch incident + SOS location from Postgres.
  2. Run the mock detector (swap for real YOLOv8+DeepLabV3+ per Section 5
     once this end-to-end flow is verified - Section 21 build order).
  3. Compute image_confidence per Section 3.2 (corrected).
  4. Evaluate location likelihood per Section 3.1.
  5. Compute the fused score per Section 3.3 (corrected).
  6. Store the candidate in PostGIS; incident status -> candidate_ready.

Raw SQL (via SQLAlchemy Core) is used here rather than the ORM models so the
worker has no import-time dependency on the api package - the two services
ship as separate Docker images.
"""
import os
import json
import uuid
import datetime as dt

from sqlalchemy import create_engine, text

from .celery_app import celery_app
from .mock_detector import run_mock_detector
from .geo import gaussian_location_likelihood, image_confidence, fused_score, FusionInputs

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://floodrescue:floodrescue@postgres:5432/floodrescue",
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


@celery_app.task(name="worker.tasks.process_incident")
def process_incident(incident_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT sos, ST_Y(geom) AS lat, ST_X(geom) AS lon, accuracy_m, created_utc "
                "FROM incidents WHERE id = :id"
            ),
            {"id": incident_id},
        ).fetchone()

        if row is None:
            return {"error": "incident not found", "incident_id": incident_id}

        sos, lat, lon, accuracy_m, created_utc = row
        accuracy_m = accuracy_m or 50.0

        # Fail-safe (Section 0/17): the mock path always "has" its one tile.
        # In the real pipeline this is where a missing/cloud-covered tile
        # would set status='needs_imagery' and return early instead of
        # guessing silently.
        det = run_mock_detector(lat, lon)

        loc_likelihood = gaussian_location_likelihood(
            det["lat"], det["lon"], lat, lon, sigma_m=accuracy_m
        )
        img_conf = image_confidence(
            det["model_score"], det["overlap_with_flood"], det["n_dup"]
        )

        now = dt.datetime.now(dt.timezone.utc)
        t_sos = created_utc if created_utc.tzinfo else created_utc.replace(tzinfo=dt.timezone.utc)

        result = fused_score(FusionInputs(
            image_confidence=img_conf,
            location_likelihood=loc_likelihood,
            t_now_epoch=now.timestamp(),
            t_sos_epoch=t_sos.timestamp(),
            cloud_cover_pct=det["cloud_cover_pct"],
        ))

        candidate_id = str(uuid.uuid4())
        detection_json = {
            "confidence_components": result.contributions,
            "detection_class": det["detection_class"],
            "source_tiles": det["source_tiles"],
            "processing_version": "v1.0.0",
            "model_version": "mock-detector-v0",
            "bounding_box_geojson": None,
        }

        conn.execute(
            text(
                "INSERT INTO candidates "
                "(id, incident_id, geom, score, uncertainty_m, detection_json, crop_s3) "
                "VALUES (:id, :incident_id, "
                "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), "
                ":score, :uncertainty_m, CAST(:detection_json AS jsonb), :crop_s3)"
            ),
            {
                "id": candidate_id,
                "incident_id": incident_id,
                "lon": det["lon"],
                "lat": det["lat"],
                "score": result.score,
                "uncertainty_m": max(accuracy_m * 0.6, 10.0),
                "detection_json": json.dumps(detection_json),
                "crop_s3": None,
            },
        )
        conn.execute(
            text("UPDATE incidents SET status = 'candidate_ready' WHERE id = :id"),
            {"id": incident_id},
        )

    return {"incident_id": incident_id, "candidate_id": candidate_id, "score": result.score}
