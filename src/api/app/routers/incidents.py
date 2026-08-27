from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from ..db import get_db
from ..models import Incident, Candidate, AuditLog
from ..schemas import IncidentOut, CandidateOut, VerifyIn, DispatchLogIn

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def _incident_to_out(incident, candidates) -> IncidentOut:
    cand_list = []
    top_id, top_score = None, -1.0
    for c in candidates:
        pt = to_shape(c.geom)
        det = c.detection_json or {}
        cand_list.append(CandidateOut(
            candidate_id=str(c.id),
            lat=pt.y,
            lon=pt.x,
            score=c.score,
            uncertainty_m=c.uncertainty_m,
            confidence_components=det.get("confidence_components", {}),
            bounding_box_geojson=det.get("bounding_box_geojson"),
            best_crop_s3=c.crop_s3,
            detection_class=det.get("detection_class"),
            source_tiles=det.get("source_tiles", []),
            processing_version=det.get("processing_version", "v1.0.0"),
            model_version=det.get("model_version", "mock-detector-v0"),
        ))
        if c.score is not None and c.score > top_score:
            top_score, top_id = c.score, str(c.id)

    recommended = None
    if top_id:
        # Section 0: this is only ever a *displayed* recommendation - nothing
        # is dispatched automatically. Threshold is a placeholder; calibrate
        # against Section 1's Precision@Top-1 target.
        recommended = "verify" if top_score < 0.75 else "task_drone"

    return IncidentOut(
        incident_id=str(incident.id),
        created_utc=incident.created_utc.isoformat(),
        sos=incident.sos,
        candidates=cand_list,
        top_candidate_id=top_id,
        recommended_action=recommended,
        status=incident.status,
    )


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    candidates = (
        db.query(Candidate)
        .filter(Candidate.incident_id == incident_id)
        .order_by(Candidate.score.desc())
        .all()
    )
    return _incident_to_out(incident, candidates)


@router.post("/{incident_id}/verify")
def verify_candidate(incident_id: str, body: VerifyIn, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    candidate = db.query(Candidate).filter(Candidate.id == body.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate not found")

    action = "verify" if body.verified else "reject"
    db.add(AuditLog(
        incident_id=incident_id,
        candidate_id=body.candidate_id,
        operator_id=body.operator_id,
        action=action,
        detail={"verified": body.verified},
    ))
    incident.status = "verified" if body.verified else "rejected"
    db.commit()
    return {"recorded": True, "action": action}


@router.post("/{incident_id}/dispatch_log")
def log_would_dispatch(incident_id: str, body: DispatchLogIn, db: Session = Depends(get_db)):
    """
    Section 0 / Section 7: a real dispatch integration is Tier 2. This
    endpoint only records what *would* have been dispatched, for the audit
    trail and demo purposes - it never contacts a real agency system.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")

    db.add(AuditLog(
        incident_id=incident_id,
        candidate_id=body.candidate_id,
        operator_id=body.operator_id,
        action=body.action,
        detail={"note": body.note},
    ))
    db.commit()
    return {"recorded": True, "action": body.action, "note": "no real dispatch was sent (Tier 1 stub)"}
