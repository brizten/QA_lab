import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getTestRunReport, getTestRuns, TestRun } from "../api/testRuns";
import StatusBadge from "../components/StatusBadge";

interface EnrichedTestRun extends TestRun {
  test_case_code?: string;
  started_by_label?: string;
}

export default function TestRunsPage() {
  const [runs, setRuns] = useState<EnrichedTestRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadRuns() {
    setIsLoading(true);
    setError(null);
    getTestRuns()
      .then(async (items) => {
        const enrichedRuns = await Promise.all(
          items.map(async (run) => {
            try {
              const report = await getTestRunReport(run.id);
              return {
                ...run,
                test_case_code: report.test_case.code,
                started_by_label: report.started_by.full_name || report.started_by.email,
              };
            } catch {
              return run;
            }
          }),
        );
        setRuns(enrichedRuns);
      })
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
              <th>Test Case</th>
              <th>Environment</th>
              <th>Status</th>
              <th>Started By</th>
              <th>Created At</th>
              <th>Duration</th>
              <th>Report</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>#{run.id}</td>
                <td className="code">{run.test_case_code || `#${run.test_case_id}`}</td>
                <td>{run.environment}</td>
                <td>
                  <StatusBadge status={run.status} />
                </td>
                <td>{run.started_by_label || `#${run.started_by_user_id}`}</td>
                <td>{formatDate(run.created_at)}</td>
                <td>{formatDuration(run.duration_ms)}</td>
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
