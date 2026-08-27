"""
SQLAlchemy models mirroring the PostGIS schema in project_brief.md Section 4.
Tables are created by infra/init.sql (loaded automatically by the postgis
docker image on first boot) rather than by SQLAlchemy, so the DDL in the
brief stays the single source of truth.
"""
import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geometry
from .db import Base


def gen_uuid():
    return str(uuid.uuid4())


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_hash = Column(String(128), nullable=False)
    created_utc = Column(DateTime(timezone=True), server_default=func.now())
    sos = Column(JSONB, nullable=False)
    geom = Column(Geometry("POINT", srid=4326))
    accuracy_m = Column(Float)
    status = Column(String(32), default="new")


class Tile(Base):
    __tablename__ = "tiles"

    tile_id = Column(String, primary_key=True)
    sensor = Column(String)
    acquisition_utc = Column(DateTime(timezone=True))
    bbox = Column(Geometry("POLYGON", srid=4326))
    resolution_m = Column(Float)
    s3_url = Column(String)


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    incident_id = Column(UUID(as_uuid=False), ForeignKey("incidents.id"))
    geom = Column(Geometry("POINT", srid=4326))
    score = Column(Float)
    uncertainty_m = Column(Float)
    detection_json = Column(JSONB)
    crop_s3 = Column(String)
    created_utc = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Append-only per Section 9: infra/init.sql revokes UPDATE/DELETE on this table."""
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    incident_id = Column(UUID(as_uuid=False))
    candidate_id = Column(UUID(as_uuid=False), nullable=True)
    operator_id = Column(String)
    action = Column(String)
    detail = Column(JSONB)
    created_utc = Column(DateTime(timezone=True), server_default=func.now())
