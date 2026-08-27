## Summary

<!-- What does this PR change, and why? -->

## Which service(s) does this touch?

- [ ] src/api
- [ ] src/worker
- [ ] src/frontend
- [ ] src/models
- [ ] tools/infra (PostGIS schema)
- [ ] docs / project_brief.md

## Checklist

- [ ] `make test-unit` passes
- [ ] `make up` + `make test-integration` pass (if this touches api/worker/db)
- [ ] If this changes `src/api/app/geo.py`, I updated `tests/unit/test_geo.py`
- [ ] If this touches dispatch/verify flows, it still respects Section 0
      (never auto-dispatch; every operator action stays in the audit log)
- [ ] I didn't add real PII/telemetry - synthetic/`user_hash`-only data per
      the Tier 1 scope
