"""
Shared pytest setup. Makes `from app.<module> import ...` resolve to
src/api/app regardless of whether tests run:
  - inside the api container (make test-unit), where FLOODRESCUE_API_SRC=/app, or
  - directly on the host from the repo root (pytest tests/unit).
"""
import os
import sys

_API_SRC = os.environ.get("FLOODRESCUE_API_SRC")
if not _API_SRC:
    _API_SRC = os.path.join(os.path.dirname(__file__), "..", "src", "api")

sys.path.insert(0, os.path.abspath(_API_SRC))
