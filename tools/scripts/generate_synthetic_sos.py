#!/usr/bin/env python3
"""
Section 13 evaluation helper: generate synthetic SOS pings at known
ground-truth locations with realistic GPS/cell-tower noise, and optionally
fire them at a running FloodRescue API for an end-to-end pipeline test.

Usage:
  python3 scripts/generate_synthetic_sos.py --count 5 --api http://localhost:8000
  python3 scripts/generate_synthetic_sos.py --count 20 --out pings.jsonl   # offline only
"""
import argparse
import hashlib
import json
import random
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# A few illustrative ground-truth points for flood-prone low-lying areas.
# Swap these for real known casualty/rescue locations from public
# post-incident reports when replaying an actual documented event.
GROUND_TRUTH_POINTS = [
    {"label": "site-a", "lat": 12.9351, "lon": 77.6785},
    {"label": "site-b", "lat": 13.1007, "lon": 77.5963},
    {"label": "site-c", "lat": 12.9081, "lon": 77.6476},
]


def jitter(lat, lon, sigma_m):
    """Add Gaussian noise (meters, roughly) to a lat/lon point."""
    deg_per_m_lat = 1 / 111320.0
    deg_per_m_lon = 1 / (111320.0 * max(0.1, abs(__import__("math").cos(__import__("math").radians(lat)))))
    dlat = random.gauss(0, sigma_m) * deg_per_m_lat
    dlon = random.gauss(0, sigma_m) * deg_per_m_lon
    return lat + dlat, lon + dlon


def make_ping(ground_truth, comm_type="gps"):
    if comm_type == "gps":
        accuracy_m = random.uniform(5, 30)
        lat, lon = jitter(ground_truth["lat"], ground_truth["lon"], accuracy_m)
        coords = {"lat": lat, "lon": lon}
        cell_info = None
    else:
        accuracy_m = random.uniform(300, 1500)
        lat, lon = jitter(ground_truth["lat"], ground_truth["lon"], accuracy_m)
        coords = None
        cell_info = {
            "mcc": "404", "mnc": "10", "lac": 12345, "cid": 54321,
            "cell_center": {"lat": lat, "lon": lon},
            "cell_uncertainty_m": accuracy_m,
        }

    return {
        "source": "app",
        "user_hash": hashlib.sha256(f"{ground_truth['label']}-{time.time()}".encode()).hexdigest(),
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coords": coords,
        "accuracy_m": accuracy_m,
        "comm_type": comm_type,
        "cell_info": cell_info,
        "battery_pct": random.randint(5, 60),
        "consent_flag": True,
        "app_version": "sim-1.0.0",
        # kept for evaluation scoring, not part of the real SOS schema
        "_ground_truth": ground_truth,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--api", default=None, help="If set, POST each ping to <api>/api/sos")
    parser.add_argument("--out", default=None, help="If set, write pings as JSONL here")
    parser.add_argument("--comm-type", choices=["gps", "cell"], default="gps")
    args = parser.parse_args()

    pings = []
    for i in range(args.count):
        gt = random.choice(GROUND_TRUTH_POINTS)
        ping = make_ping(gt, comm_type=args.comm_type)
        pings.append(ping)

    if args.out:
        with open(args.out, "w") as f:
            for p in pings:
                f.write(json.dumps(p) + "\n")
        print(f"wrote {len(pings)} pings to {args.out}")

    if args.api:
        for p in pings:
            body = {k: v for k, v in p.items() if not k.startswith("_")}
            req = urllib.request.Request(
                f"{args.api}/api/sos",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read())
                    print(f"[ok] ground_truth={p['_ground_truth']['label']} -> incident_id={data['incident_id']}")
            except urllib.error.HTTPError as e:
                print(f"[fail] {e.code}: {e.read().decode()}")
            time.sleep(0.3)

    if not args.api and not args.out:
        print(json.dumps(pings, indent=2))


if __name__ == "__main__":
    main()
