import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { MapContainer, TileLayer, Circle, CircleMarker, Popup } from "react-leaflet";
import { getIncident, verifyCandidate, logWouldDispatch } from "../api.js";

const OPERATOR_ID = "demo-operator";

function scoreColor(score) {
  if (score >= 0.75) return "#3FBF8F"; // high confidence - flood-teal green
  if (score >= 0.5) return "#E8A33D"; // amber - needs review
  return "#D64545"; // red - low confidence
}

export default function IncidentPage() {
  const { id } = useParams();
  const [incident, setIncident] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [log, setLog] = useState([]);

  const load = useCallback(async () => {
    try {
      const data = await getIncident(id);
      setIncident(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    load();
    // Candidates arrive asynchronously from the worker - poll briefly like a
    // real operator console would while waiting on the pipeline.
    const interval = setInterval(load, 2500);
    return () => clearInterval(interval);
  }, [load]);

  if (error) return <div className="panel"><p className="error-banner">{error}</p></div>;
  if (!incident) return <div className="panel"><p className="muted">Loading incident…</p></div>;

  const sos = incident.sos;
  const sosLat = sos?.coords?.lat;
  const sosLon = sos?.coords?.lon;
  const accuracy = sos?.accuracy_m || 50;
  const candidates = [...incident.candidates].sort((a, b) => b.score - a.score).slice(0, 5);

  async function act(candidateId, verified) {
    setBusyId(candidateId);
    try {
      await verifyCandidate(id, { candidate_id: candidateId, operator_id: OPERATOR_ID, verified });
      setLog((l) => [{ ts: new Date().toISOString(), action: verified ? "verify" : "reject", candidateId }, ...l]);
      await load();
    } finally {
      setBusyId(null);
    }
  }

  async function requestDrone(candidateId) {
    setBusyId(candidateId);
    try {
      await logWouldDispatch(id, {
        candidate_id: candidateId,
        operator_id: OPERATOR_ID,
        action: "request_drone",
        note: "Operator requested drone confirmation pass (Tier 2 - logged only)",
      });
      setLog((l) => [{ ts: new Date().toISOString(), action: "request_drone", candidateId }, ...l]);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="incident-layout">
      <div className="incident-header">
        <div>
          <h1>Incident {incident.incident_id.slice(0, 8)}</h1>
          <p className="muted">
            {sos.source} · {sos.comm_type} · consent {sos.consent_flag ? "yes" : "no"}
            {sos.battery_pct != null && ` · battery ${sos.battery_pct}%`}
          </p>
        </div>
        <div className={`status-pill status-${incident.status}`}>{incident.status.replace("_", " ")}</div>
      </div>

      <div className="incident-body">
        <div className="map-pane">
          {sosLat != null && (
            <MapContainer center={[sosLat, sosLon]} zoom={16} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
              <TileLayer
                attribution='&copy; OpenStreetMap contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <Circle
                center={[sosLat, sosLon]}
                radius={accuracy}
                pathOptions={{ color: "#4FA3D1", fillOpacity: 0.08, weight: 1.5, dashArray: "4 4" }}
              />
              <CircleMarker
                center={[sosLat, sosLon]}
                radius={7}
                pathOptions={{ color: "#4FA3D1", fillColor: "#4FA3D1", fillOpacity: 1 }}
              >
                <Popup>SOS ping ± {accuracy}m</Popup>
              </CircleMarker>
              {candidates.map((c) => (
                <React.Fragment key={c.candidate_id}>
                  <Circle
                    center={[c.lat, c.lon]}
                    radius={c.uncertainty_m}
                    pathOptions={{ color: scoreColor(c.score), fillOpacity: 0.06, weight: 1 }}
                  />
                  <CircleMarker
                    center={[c.lat, c.lon]}
                    radius={6}
                    pathOptions={{ color: scoreColor(c.score), fillColor: scoreColor(c.score), fillOpacity: 0.9 }}
                  >
                    <Popup>
                      score {c.score.toFixed(2)} · ±{Math.round(c.uncertainty_m)}m · {c.detection_class}
                    </Popup>
                  </CircleMarker>
                </React.Fragment>
              ))}
            </MapContainer>
          )}
        </div>

        <aside className="candidate-panel">
          <h2>Top candidates</h2>
          {candidates.length === 0 && (
            <p className="muted">No candidates yet — worker is still processing (or none found; system degrades to manual triage per Section 0).</p>
          )}
          {candidates.map((c, i) => (
            <article key={c.candidate_id} className="candidate-card" style={{ "--accent": scoreColor(c.score) }}>
              <div className="candidate-card-head">
                <span className="rank">#{i + 1}</span>
                <span className="score">{(c.score * 100).toFixed(0)}%</span>
                {c.candidate_id === incident.top_candidate_id && <span className="top-badge">top pick</span>}
              </div>
              <dl className="score-breakdown">
                {Object.entries(c.confidence_components)
                  .filter(([k]) => ["image_confidence", "location_likelihood", "temporal_consistency"].includes(k))
                  .map(([k, v]) => (
                    <div key={k} className="score-row">
                      <dt>{k.replace(/_/g, " ")}</dt>
                      <div className="bar-track">
                        <div className="bar-fill" style={{ width: `${Math.min(100, v * 100)}%` }} />
                      </div>
                      <dd>{typeof v === "number" ? v.toFixed(3) : v}</dd>
                    </div>
                  ))}
              </dl>
              <p className="candidate-meta">
                {c.detection_class} · ±{Math.round(c.uncertainty_m)}m uncertainty · model {c.model_version}
              </p>
              <div className="candidate-actions">
                <button className="btn small ghost-danger" disabled={busyId === c.candidate_id} onClick={() => act(c.candidate_id, false)}>
                  Reject
                </button>
                <button className="btn small ghost" disabled={busyId === c.candidate_id} onClick={() => requestDrone(c.candidate_id)}>
                  Request drone
                </button>
                <button className="btn small primary" disabled={busyId === c.candidate_id} onClick={() => act(c.candidate_id, true)}>
                  Verify
                </button>
              </div>
            </article>
          ))}

          {incident.recommended_action && (
            <p className="recommendation">
              System recommendation: <strong>{incident.recommended_action.replace("_", " ")}</strong> — shown only;
              nothing is dispatched automatically (Section 0).
            </p>
          )}

          {log.length > 0 && (
            <div className="audit-log">
              <h3>Session audit log</h3>
              <ul>
                {log.map((entry, idx) => (
                  <li key={idx}>
                    <span className="mono">{entry.ts.slice(11, 19)}</span> {entry.action} · {entry.candidateId.slice(0, 8)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
