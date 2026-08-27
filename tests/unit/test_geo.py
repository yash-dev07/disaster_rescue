"""
Regression tests for the two bugs fixed in project_brief.md Section 3.
Pure logic, no DB/network - safe to run anywhere `app.geo` is importable
(see tests/conftest.py for how that's resolved).
"""
from app.geo import temporal_factor, fused_score, FusionInputs, image_confidence


def test_temporal_factor_actually_boosts_with_repeats():
    """The original bug made this constant at 1.0 for all n_dup >= 1."""
    assert temporal_factor(1) == 1.0
    assert temporal_factor(2) > temporal_factor(1)
    assert temporal_factor(5) == 1.4
    assert temporal_factor(100) == 1.5  # capped


def test_image_confidence_is_clipped_to_one():
    conf = image_confidence(model_score=1.0, overlap_with_flood=1.0, n_dup=10)
    assert conf <= 1.0


def test_fused_score_spreads_across_full_range():
    """The original bug compressed every score into sigmoid([0,1]) = [0.5, 0.73]."""
    weak = fused_score(FusionInputs(
        image_confidence=0.05, location_likelihood=0.0,
        t_now_epoch=100000, t_sos_epoch=0, cloud_cover_pct=90,
    ))
    strong = fused_score(FusionInputs(
        image_confidence=0.95, location_likelihood=0.002,
        t_now_epoch=100, t_sos_epoch=0, cloud_cover_pct=5,
    ))
    assert strong.score > weak.score
    # With the fix these should be well outside the old [0.5, 0.73] band
    assert strong.score > 0.75 or weak.score < 0.45


def test_fused_score_returns_contributions_for_explainability():
    result = fused_score(FusionInputs(
        image_confidence=0.6, location_likelihood=0.001,
        t_now_epoch=500, t_sos_epoch=0, cloud_cover_pct=20,
    ))
    for key in ("image_confidence", "location_likelihood", "temporal_consistency", "cloud_factor"):
        assert key in result.contributions
