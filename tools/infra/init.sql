-- Section 4 schema, copied exactly from project_brief.md, plus an
-- append-only audit_log table required by Section 9's audit checklist.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- for gen_random_uuid()

CREATE TABLE incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_hash varchar(128) NOT NULL,
  created_utc timestamptz NOT NULL DEFAULT now(),
  sos jsonb NOT NULL,
  geom geometry(Point, 4326),
  accuracy_m double precision,
  status varchar(32) DEFAULT 'new'
);

CREATE TABLE tiles (
  tile_id text PRIMARY KEY,
  sensor text,
  acquisition_utc timestamptz,
  bbox geometry(Polygon, 4326),
  resolution_m double precision,
  s3_url text
);

CREATE TABLE candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id uuid REFERENCES incidents(id),
  geom geometry(Point, 4326),
  score double precision,
  uncertainty_m double precision,
  detection_json jsonb,
  crop_s3 text,
  created_utc timestamptz DEFAULT now()
);

CREATE INDEX ON incidents USING GIST (geom);
CREATE INDEX ON tiles USING GIST (bbox);
CREATE INDEX ON candidates USING GIST (geom);

-- Section 9: "Audit logs append-only (a Postgres table with no
-- UPDATE/DELETE grants is enough for T1)".
CREATE TABLE audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id uuid,
  candidate_id uuid,
  operator_id varchar(128),
  action varchar(32),
  detail jsonb,
  created_utc timestamptz NOT NULL DEFAULT now()
);
REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;
