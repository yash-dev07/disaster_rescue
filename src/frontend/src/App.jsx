import React from "react";
import { Outlet, NavLink } from "react-router-dom";

export default function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <div className="brand-text">
            <span className="brand-name">FloodRescue</span>
            <span className="brand-sub">Operator Console · Tier 1 MVP</span>
          </div>
        </div>
        <nav className="topnav">
          <NavLink to="/simulate" className={({ isActive }) => (isActive ? "active" : "")}>
            Send SOS
          </NavLink>
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="footer">
        Synthetic / replayed data only · Section 0: no asset is ever auto-dispatched by this system.
      </footer>
    </div>
  );
}
