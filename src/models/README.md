# Models (Section 5)

Baseline models (unchanged from the original spec, still reasonable current
choices):
- **Flood segmentation:** DeepLabV3+ with a ResNet-50 backbone (PyTorch).
- **Object detection:** YOLOv8-medium for speed; Faster R-CNN+FPN as a
  higher-accuracy fallback.
- **Change detection (Tier 2, optional):** a Siamese U-Net for before/after
  comparison.

## Training data

Do **not** try to hand-label thousands of images yourselves — that's a
multi-month full-time job, not a component of a semester project. Use public,
pre-labeled datasets instead:

| Dataset | What it gives you |
|---|---|
| [FloodNet](https://arxiv.org/abs/2012.02951) | ~2,343 UAV images (post-Hurricane-Harvey), pixel-level labels across 9-10 classes including building-flooded/non-flooded, road-flooded/non-flooded, water, vehicle, tree, pool. Directly matches this task. |
| RescueNet | ~4,494 UAV images (post-Hurricane-Michael), 4-level building damage annotations. Complements FloodNet for the damage-severity angle. |
| xBD | Large pre/post-disaster satellite-imagery dataset for building damage; useful if you extend beyond UAV/drone-scale imagery to satellite-scale. |

Fine-tune on these. Use a *small* self-collected/self-labeled set (a few
hundred crops from your own test-region imagery) only to adapt to your
specific geography and sensor — not as your primary dataset.

**Split by event, not randomly** (Section 11): train on one event, validate
on a different one, so you're testing generalization rather than memorizing
a single flood's visual signature.

## Training

`train_yolo.sh` uses the **current** Ultralytics CLI. The old
`python -m ultralytics.yolo.train` module path no longer exists in current
Ultralytics releases and will fail — the console entry point is `yolo`.

```bash
bash train_yolo.sh
```

Default training already applies mosaic/HSV/flip augmentation via the
hyperparameter config — there's no single `augment=True` flag; augmentation
strength is controlled by individual hyp values (`mosaic`, `mixup`, `hsv_h`,
etc.) if you want to change it from the defaults.

## Build order (Section 21)

1. Get the end-to-end pipeline working with `src/worker/worker/mock_detector.py`
   first (synthetic candidate near the SOS point, using the corrected
   Section 3 formulas).
2. Only once that works, swap in the real trained YOLOv8 (+ DeepLabV3+ flood
   mask) models by replacing the call to `run_mock_detector()` in
   `src/worker/worker/tasks.py` with a call to your trained model's inference.
3. Export the trained model as documented below and drop it somewhere the
   worker container can read it (e.g. mount a `models/weights/` volume).

## Smoke test only, no mAP gate (Section 12)

CI should confirm the model loads and its output matches the Section 2.3
candidate schema. Don't gate CI on an mAP threshold for a student project —
log it, don't fail the build on it.
