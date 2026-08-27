#!/usr/bin/env bash
# Corrected training commands - see models/README.md.
# The original `python -m ultralytics.yolo.train` module path does not exist
# in current Ultralytics releases and will fail immediately.
set -euo pipefail

pip install -U ultralytics
export DATASET_PATH="${DATASET_PATH:-/workspace/datasets/floodrescue/yolov8}"

# train (current Ultralytics CLI: console entry point `yolo`, not
# `python -m ultralytics.yolo.train`)
yolo detect train \
  data="${DATASET_PATH}/data.yaml" \
  model=yolov8m.pt \
  imgsz=1024 \
  epochs=80 \
  batch=8 \
  lr0=0.001

# export best model to ONNX for lighter-weight inference in the worker
yolo export model=runs/detect/train/weights/best.pt format=onnx
