import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import App from "./App.jsx";
import IncidentPage from "./pages/IncidentPage.jsx";
import SosSimulator from "./pages/SosSimulator.jsx";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <HashRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<Navigate to="/simulate" replace />} />
          <Route path="simulate" element={<SosSimulator />} />
          <Route path="incident/:id" element={<IncidentPage />} />
        </Route>
      </Routes>
    </HashRouter>
  </React.StrictMode>
);
