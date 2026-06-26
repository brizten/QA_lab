import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getModules } from "../api/modules";
import { getTestCases } from "../api/testCases";
import { getTestRuns } from "../api/testRuns";

interface DashboardStats {
  modules: number;
  testCases: number;
  activeTestCases: number;
  testRuns: number;
  runningRuns: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getModules(), getTestCases(), getTestRuns()])
      .then(([modules, testCases, testRuns]) => {
        setStats({
          modules: modules.length,
          testCases: testCases.length,
          activeTestCases: testCases.filter((testCase) => testCase.is_active).length,
          testRuns: testRuns.length,
          runningRuns: testRuns.filter((run) => run.status === "QUEUED" || run.status === "RUNNING")
            .length,
        });
      })
      .catch(() => setError("Could not load dashboard data."));
  }, []);

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Dashboard</h1>
        </div>
        <Link className="button primary" to="/run-test">
          Run Test
        </Link>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      <div className="metrics-grid">
        <Metric label="Modules" value={stats?.modules} />
        <Metric label="Test Cases" value={stats?.testCases} />
        <Metric label="Active Cases" value={stats?.activeTestCases} />
        <Metric label="Test Runs" value={stats?.testRuns} />
        <Metric label="Queued / Running" value={stats?.runningRuns} />
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value?: number }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value ?? "-"}</strong>
    </div>
  );
}
