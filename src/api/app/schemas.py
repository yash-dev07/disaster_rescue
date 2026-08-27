"""Pydantic schemas mirroring project_brief.md Section 2 exactly."""
from typing import Optional, List, Literal
from pydantic import BaseModel


class Coords(BaseModel):
    lat: float
    lon: float


class CellCenter(BaseModel):
    lat: float
    lon: float


class CellInfo(BaseModel):
    mcc: Optional[str] = None
    mnc: Optional[str] = None
    lac: Optional[int] = None
    cid: Optional[int] = None
    cell_center: Optional[CellCenter] = None
    cell_uncertainty_m: Optional[float] = None


class SOSIn(BaseModel):
    source: Literal["app", "sms", "carrier"]
    user_hash: str
    timestamp_utc: str
    coords: Optional[Coords] = None
    accuracy_m: Optional[float] = None
    comm_type: Literal["gps", "cell", "sms"]
    cell_info: Optional[CellInfo] = None
    rssi: Optional[float] = None
    battery_pct: Optional[int] = None
    optional_photo_url: Optional[str] = None
    consent_flag: bool
    app_version: Optional[str] = None
    device_make: Optional[str] = None
    device_model: Optional[str] = None


class SOSCreatedOut(BaseModel):
    incident_id: str


class CandidateOut(BaseModel):
    candidate_id: str
    lat: float
    lon: float
    score: float
    uncertainty_m: float
    confidence_components: dict
    bounding_box_geojson: Optional[dict] = None
    best_crop_s3: Optional[str] = None
    detection_class: Optional[str] = None
    source_tiles: List[str] = []
    processing_version: str
    model_version: str


class IncidentOut(BaseModel):
    incident_id: str
    created_utc: str
    sos: dict
    candidates: List[CandidateOut]
    top_candidate_id: Optional[str] = None
    recommended_action: Optional[str] = None
    status: str


class VerifyIn(BaseModel):
    candidate_id: str
    operator_id: str
    verified: bool


class DispatchLogIn(BaseModel):
    candidate_id: str
    operator_id: str
    action: Literal["would_dispatch_boat", "would_dispatch_helicopter", "request_drone"]
    note: Optional[str] = None
