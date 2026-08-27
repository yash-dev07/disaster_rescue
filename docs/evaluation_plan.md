# Evaluation plan (Section 13)

The original brief called for a live controlled field trial with consenting
volunteers and a partner dispatcher — that's Tier 2 and needs approvals a
semester project won't get in time. This is the Tier 1 substitute.

## Steps

1. **Pick 2-3 documented past flood events** with available Sentinel-1/2
   imagery, e.g. a documented Indian monsoon flood, or reuse FloodNet's
   Hurricane Harvey imagery with synthetic SOS pings placed near its labeled
   "person" / building-flooded regions.
2. **Generate synthetic SOS pings** at known ground-truth locations with
   realistic GPS/cell-tower noise added (`tools/scripts/generate_synthetic_sos.py`).
3. **Run the full pipeline** end to end; record for every replayed ping:
   - localization error (top-1 candidate distance to ground truth, for
     GPS-origin pings; top-3 for cell-tower-only pings)
   - Precision@Top-1 on your labeled validation set
   - time-to-candidate (SOS submit -> candidate_ready)
4. **Compare against Section 1 targets:**
   - median localization error <= 50m (GPS-origin, top-1), <= 200m
     (cell-tower-only, top-3)
   - Precision@Top-1 >= 0.60
   - time-to-candidate <= 10 min
5. **Report honestly** where you fall short and why (imagery resolution,
   cloud cover, dataset domain gap, small validation set, etc.) — a partial
   result honestly measured is worth more than a claimed number that isn't
   reproducible.

## Metrics dashboard (Section 18)

Expose via `/health` and application logs, or a small notebook:
SOS ingestion rate; processing latency (median, p95) from SOS to
candidate_ready; inference time per tile; segmentation/detection accuracy
per `model_version`; operator verify rate and average verification time.

## Split discipline (Section 11)

Split by event, not randomly across images: train on one event's imagery
(e.g. Harvey via FloodNet), hold out a different event for validation, so
you're testing generalization rather than memorizing one flood's visual
signature.
