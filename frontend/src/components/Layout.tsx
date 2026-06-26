import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { CurrentUser, getCurrentUser, logout } from "../api/auth";

const navItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/modules", label: "Modules" },
  { to: "/test-cases", label: "Test Cases" },
  { to: "/run-test", label: "Run Test" },
  { to: "/test-runs", label: "Test Runs" },
];

export default function Layout() {
  const navigate = useNavigate();
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    let ignore = false;

    getCurrentUser()
      .then((currentUser) => {
        if (!ignore) {
          setUser(currentUser);
        }
      })
      .catch(() => {
        logout();
        navigate("/login", { replace: true });
      });

    return () => {
      ignore = true;
    };
  }, [navigate]);

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">AP</span>
          <span>Autotest Platform</span>
        </div>
        <nav className="nav-list" aria-label="Main navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <div>
            <div className="eyebrow">Local MVP</div>
            <strong>{user?.full_name || user?.email || "Signed in"}</strong>
            {user?.role ? <span className="role-pill">{user.role}</span> : null}
          </div>
          <button className="button secondary" type="button" onClick={handleLogout}>
            Logout
          </button>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
