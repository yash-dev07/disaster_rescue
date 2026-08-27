const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function getIncident(id) {
  const res = await fetch(`${BASE}/api/incidents/${id}`);
  if (!res.ok) throw new Error(`Failed to load incident (${res.status})`);
  return res.json();
}

export async function verifyCandidate(incidentId, { candidate_id, operator_id, verified }) {
  const res = await fetch(`${BASE}/api/incidents/${incidentId}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_id, operator_id, verified }),
  });
  if (!res.ok) throw new Error(`Failed to record verification (${res.status})`);
  return res.json();
}

export async function logWouldDispatch(incidentId, body) {
  const res = await fetch(`${BASE}/api/incidents/${incidentId}/dispatch_log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to log dispatch (${res.status})`);
  return res.json();
}

export async function submitSos(sos) {
  const res = await fetch(`${BASE}/api/sos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sos),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Failed to submit SOS (${res.status})`);
  }
  return res.json();
}
