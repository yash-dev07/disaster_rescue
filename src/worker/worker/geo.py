"""
Geospatial fusion math for FloodRescue (Section 3 of project_brief.md).

Two bugs from the original spec are fixed here, exactly as documented in
project_brief.md Section 3.2 and 3.3:

  1. temporal_factor's cap was set below its own floor (min(1.0, 1.0 + ...))
     so it was always exactly 1.0 regardless of n_dup. Cap raised to 1.5.
  2. The fused score's sigmoid input range was [0, 1] with weights summing to
     1, which only ever produced scores in [0.5, 0.73] - useless for ranking.
     Fixed by rescaling around the midpoint (SCALE=8.0, tunable) before the
     sigmoid.
"""
import math
from dataclasses import dataclass

try:
    from pyproj import Transformer
    _HAS_PYPROJ = True
except ImportError:
    _HAS_PYPROJ = False


def latlon_to_local_xy(lat, lon, lat0, lon0):
    """
    Project (lat, lon) into a local planar (meters) frame centered on
    (lat0, lon0), per Section 3.1's "convert to a local planar frame before
    computing the Gaussian" requirement. Uses an azimuthal-equidistant
    projection via pyproj when available; falls back to an equirectangular
    approximation (accurate enough at the <20km scales this system operates
    over) if pyproj isn't installed.
    """
    if _HAS_PYPROJ:
        transformer = Transformer.from_crs(
            "EPSG:4326",
            f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +units=m +ellps=WGS84",
            always_xy=True,
        )
        x, y = transformer.transform(lon, lat)
        return x, y
    R = 6371000.0
    dlat = math.radians(lat - lat0)
    dlon = math.radians(lon - lon0)
    x = dlon * math.cos(math.radians(lat0)) * R
    y = dlat * R
    return x, y


def gaussian_location_likelihood(lat, lon, lat0, lon0, sigma_m):
    """
    Section 3.1 - isotropic 2D Gaussian centered at (lat0, lon0), evaluated in
    the local planar frame. sigma is floored at 10m per the spec
    (sigma = max(accuracy_m, 10)).

    Note: this returns a probability *density*, not a bounded [0,1] score. Its
    peak value shrinks as sigma grows (peak = 1/(2*pi*sigma^2)), so at typical
    GPS accuracies (10-30m) it will be a small number. That's fine for
    *ranking* candidates within one incident (it's monotonic in distance from
    the SOS point), but if you want it to behave like the other, roughly
    O(1)-scaled features going into Section 3.3, consider normalizing it
    (e.g. divide by its own peak value) before treating w2 as directly
    comparable to w1/w3/w4. The brief doesn't flag this as one of the two
    bugs to fix, so it's left as specified - just documented here so it
    doesn't look like an oversight.
    """
    sigma = max(sigma_m, 10.0)
    x, y = latlon_to_local_xy(lat, lon, lat0, lon0)
    r2 = x * x + y * y
    return (1.0 / (2 * math.pi * sigma ** 2)) * math.exp(-r2 / (2 * sigma ** 2))


def uniform_polygon_likelihood(inside: bool, area_m2: float) -> float:
    """Section 3.1 - cell-sector-only case: uniform density 1/A inside, 0 outside."""
    if not inside or area_m2 <= 0:
        return 0.0
    return 1.0 / area_m2


def iou(box_a, box_b):
    """Intersection-over-union of two (xmin, ymin, xmax, ymax) boxes."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return 0.0 if union <= 0 else inter / union


def temporal_factor(n_dup: int) -> float:
    """
    Section 3.2 - FIXED. Original: min(1.0, 1.0 + 0.1*(n_dup-1)) which is
    always exactly 1.0 for any n_dup >= 1 (the cap sits below the floor of
    the expression). Fixed cap raised to 1.5:
      n_dup=1 -> 1.0, n_dup=2 -> 1.1, n_dup=5 -> 1.4, capped at 1.5.
    """
    n_dup = max(1, n_dup)
    return min(1.5, 1.0 + 0.1 * (n_dup - 1))


def image_confidence(model_score: float, overlap_with_flood: float, n_dup: int) -> float:
    """
    Section 3.2 fused image confidence. Clipped to [0,1]: with the corrected
    temporal_factor able to exceed 1.0, the raw product (score * overlap *
    temporal_factor) can now exceed 1.0 for a strong, repeated, high-overlap
    detection, and this value feeds Section 3.3 as a [0,1] feature.
    """
    tf = temporal_factor(n_dup)
    raw = model_score * overlap_with_flood * tf
    return min(1.0, max(0.0, raw))


@dataclass
class FusionInputs:
    image_confidence: float
    location_likelihood: float
    t_now_epoch: float
    t_sos_epoch: float
    cloud_cover_pct: float
    tau_seconds: float = 21600.0
    w1: float = 0.5
    w2: float = 0.35
    w3: float = 0.10
    w4: float = 0.05
    b: float = 0.0
    scale: float = 8.0  # SCALE hyperparameter from Section 3.3 - tune against validation set


@dataclass
class FusionResult:
    score: float
    z: float
    raw: float
    contributions: dict


def fused_score(inp: "FusionInputs") -> "FusionResult":
    """
    Section 3.3 - FIXED. Original: z = w1*f1+w2*f2+w3*f3+w4*f4+b fed directly
    into a sigmoid. With weights summing to 1 and b=0, raw in [0,1] means
    every candidate - best or worst - scores in sigmoid([0,1]) = [0.5, 0.73].
    Fixed by rescaling around the midpoint before the sigmoid:
      z = SCALE * (raw - 0.5), SCALE=8.0 by default (tune this).
    This spreads scores across roughly [0.02, 0.98].
    """
    f1 = inp.image_confidence
    f2 = inp.location_likelihood
    f3 = math.exp(-(inp.t_now_epoch - inp.t_sos_epoch) / inp.tau_seconds)
    f4 = 1.0 - (inp.cloud_cover_pct / 100.0)

    c1, c2, c3, c4 = inp.w1 * f1, inp.w2 * f2, inp.w3 * f3, inp.w4 * f4
    raw = c1 + c2 + c3 + c4 + inp.b
    z = inp.scale * (raw - 0.5)
    score = 1.0 / (1.0 + math.exp(-z))

    return FusionResult(
        score=score,
        z=z,
        raw=raw,
        contributions={
            "image_confidence": f1,
            "location_likelihood": f2,
            "temporal_consistency": f3,
            "cloud_factor": f4,
            "w1*f1": c1,
            "w2*f2": c2,
            "w3*f3": c3,
            "w4*f4": c4,
        },
    )
