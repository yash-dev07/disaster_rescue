import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitSos } from "../api.js";

// A couple of plausible starting points for a demo (Bengaluru area, flood-prone
// low-lying zones). Section 13: real evaluation uses replayed historical
// events instead of a manual form like this one.
const PRESETS = [
  { label: "Bellandur lowlands", lat: 12.9351, lon: 77.6785 },
  { label: "Yelahanka lake edge", lat: 13.1007, lon: 77.5963 },
  { label: "Custom", lat: null, lon: null },
];

export default function SosSimulator() {
  const navigate = useNavigate();
  const [preset, setPreset] = useState(PRESETS[0]);
  const [lat, setLat] = useState(PRESETS[0].lat);
  const [lon, setLon] = useState(PRESETS[0].lon);
  const [accuracy, setAccuracy] = useState(15);
  const [commType, setCommType] = useState("gps");
  const [battery, setBattery] = useState(22);
  const [consent, setConsent] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  function selectPreset(p) {
    setPreset(p);
    if (p.lat !== null) {
      setLat(p.lat);
      setLon(p.lon);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const sos = {
        source: "app",
        user_hash: cryptoRandomHash(),
        timestamp_utc: new Date().toISOString().replace(/\.\d+Z$/, "Z"),
        coords: { lat: Number(lat), lon: Number(lon) },
        accuracy_m: Number(accuracy),
        comm_type: commType,
        battery_pct: Number(battery),
        consent_flag: consent,
        app_version: "sim-1.0.0",
      };
      const { incident_id } = await submitSos(sos);
      // small delay so the mock worker has time to produce a candidate
      setTimeout(() => navigate(`/incident/${incident_id}`), 900);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="panel simulate">
      <h1>Simulate an SOS ping</h1>
      <p className="muted">
        Sends a synthetic distress signal into the pipeline, the same shape a real
        app/SMS/carrier ping would use (Section 2.1 schema). The worker will run the
        mock detector and produce a ranked candidate for the operator console.
      </p>

      <form onSubmit={handleSubmit} className="form-grid">
        <label className="field">
          <span>Location preset</span>
          <select
            value={preset.label}
            onChange={(e) => selectPreset(PRESETS.find((p) => p.label === e.target.value))}
          >
            {PRESETS.map((p) => (
              <option key={p.label} value={p.label}>{p.label}</option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Latitude</span>
          <input type="number" step="0.0001" value={lat ?? ""} onChange={(e) => setLat(e.target.value)} required />
        </label>

        <label className="field">
          <span>Longitude</span>
          <input type="number" step="0.0001" value={lon ?? ""} onChange={(e) => setLon(e.target.value)} required />
        </label>

        <label className="field">
          <span>comm_type</span>
          <select value={commType} onChange={(e) => setCommType(e.target.value)}>
            <option value="gps">gps</option>
            <option value="cell">cell</option>
            <option value="sms">sms</option>
          </select>
        </label>

        <label className="field">
          <span>accuracy_m</span>
          <input type="number" value={accuracy} onChange={(e) => setAccuracy(e.target.value)} />
        </label>

        <label className="field">
          <span>battery_pct</span>
          <input type="number" min="0" max="100" value={battery} onChange={(e) => setBattery(e.target.value)} />
        </label>

        <label className="field checkbox">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span>consent_flag (required — Section 0 privacy-first)</span>
        </label>

        {error && <div className="error-banner">{error}</div>}

        <button className="btn primary" type="submit" disabled={busy}>
          {busy ? "Sending…" : "Send SOS"}
        </button>
      </form>
    </div>
  );
}

function cryptoRandomHash() {
  const bytes = new Uint8Array(32);
  (window.crypto || {}).getRandomValues?.(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
