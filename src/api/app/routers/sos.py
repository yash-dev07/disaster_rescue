from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from ..db import get_db
from ..models import Incident
from ..schemas import SOSIn, SOSCreatedOut
from ..queue import enqueue_incident

router = APIRouter(prefix="/api/sos", tags=["sos"])


@router.post("", response_model=SOSCreatedOut, status_code=201)
def submit_sos(sos: SOSIn, db: Session = Depends(get_db)):
    # Section 0 (privacy-first / fail-safe): no consent -> refuse rather than
    # silently process. Real deployments may special-case "carrier" source
    # under emergency-services regulations; left as a TODO for Tier 2.
    if not sos.consent_flag:
        raise HTTPException(status_code=400, detail="consent_flag must be true to process an SOS")

    lat = lon = None
    accuracy_m = sos.accuracy_m
    if sos.coords:
        lat, lon = sos.coords.lat, sos.coords.lon
    elif sos.cell_info and sos.cell_info.cell_center:
        lat, lon = sos.cell_info.cell_center.lat, sos.cell_info.cell_center.lon
        accuracy_m = accuracy_m or sos.cell_info.cell_uncertainty_m
    else:
        raise HTTPException(
            status_code=400,
            detail="SOS must include coords or cell_info.cell_center to be geolocated",
        )

    incident = Incident(
        user_hash=sos.user_hash,
        sos=sos.model_dump(),
        geom=from_shape(Point(lon, lat), srid=4326),
        accuracy_m=accuracy_m,
        status="new",
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    try:
        enqueue_incident(str(incident.id))
    except Exception:
        # Fail-safe (Section 0): if the queue is unreachable, don't lose the
        # SOS or guess - flag it for manual triage instead.
        incident.status = "needs_imagery"
        db.commit()

    return SOSCreatedOut(incident_id=str(incident.id))
