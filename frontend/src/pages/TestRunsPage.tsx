import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import StatusBadge from "../components/StatusBadge";
import { getTestRuns, TestRun } from "../api/testRuns";

export default function TestRunsPage() {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadRuns() {
    setIsLoading(true);
    setError(null);
    getTestRuns()
      .then(setRuns)
      .catch(() => setError("Could not load test runs."))
      .finally(() => setIsLoading(false));
  }

  useEffect(() => {
    loadRuns();
  }, []);

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Test Runs</h1>
        </div>
        <button className="button secondary" type="button" onClick={loadRuns}>
          Refresh
        </button>
      </div>
      {error ? <div className="alert error">{error}</div> : null}
      {isLoading ? <div className="muted">Loading test runs...</div> : null}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Environment</th>
              <th>Duration</th>
              <th>Created</th>
              <th>Report</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>#{run.id}</td>
                <td>
                  <StatusBadge status={run.status} />
                </td>
                <td>{run.environment}</td>
                <td>{formatDuration(run.duration_ms)}</td>
                <td>{formatDate(run.created_at)}</td>
                <td>
                  <Link to={`/test-runs/${run.id}/report`}>Open</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatDuration(durationMs: number | null): string {
  return durationMs === null ? "-" : `${durationMs} ms`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}
