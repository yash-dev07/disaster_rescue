"""
Mock detector - Section 21 / starter-task step 3: "on new incident, fetch one
pre-stored sample tile, run a *mock* detector (returns one synthetic
candidate near the SOS point using the corrected Section 3 formulas)".

Swap this module out for the real YOLOv8 + DeepLabV3+ pipeline (Section 5,
models/train_yolo.sh) once the end-to-end flow with this mock is verified
working end to end (Section 21 build order).
"""
import random


def run_mock_detector(sos_lat: float, sos_lon: float) -> dict:
    """
    Returns a single synthetic detection near the SOS point with a plausible
    model score, flood-mask overlap, and duplicate count, standing in for a
    real YOLOv8 + flood-segmentation pass over Sentinel-2 tiles.
    """
    jitter_lat = random.uniform(-0.0004, 0.0004)  # roughly tens of meters
    jitter_lon = random.uniform(-0.0004, 0.0004)
    return {
        "lat": sos_lat + jitter_lat,
        "lon": sos_lon + jitter_lon,
        "model_score": round(random.uniform(0.55, 0.9), 3),
        "overlap_with_flood": round(random.uniform(0.4, 0.95), 3),
        "n_dup": random.choice([1, 1, 2, 3]),
        "cloud_cover_pct": round(random.uniform(0, 30), 1),
        "detection_class": random.choice(["person", "group", "boat"]),
        "source_tiles": ["MOCK_TILE_0001"],
    }
