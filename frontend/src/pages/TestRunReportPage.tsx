import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getTestRunReport, TestRunReport } from "../api/testRuns";
import StatusBadge from "../components/StatusBadge";

export default function TestRunReportPage() {
  const { id } = useParams();
  const runId = Number(id);
  const [report, setReport] = useState<TestRunReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const shouldAutoRefresh = useMemo(
    () => report?.run.status === "QUEUED" || report?.run.status === "RUNNING",
    [report],
  );

  function loadReport() {
    if (!Number.isFinite(runId)) {
      setError("Invalid run id.");
      setIsLoading(false);
      return;
    }

    getTestRunReport(runId)
      .then((data) => {
        setReport(data);
        setError(null);
      })
      .catch(() => setError("Could not load report."))
      .finally(() => setIsLoading(false));
  }

  useEffect(() => {
    loadReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  useEffect(() => {
    if (!shouldAutoRefresh) {
      return undefined;
    }
    const timer = window.setInterval(loadReport, 2500);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldAutoRefresh, runId]);

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Run Report</h1>
          <p>{report ? `${report.test_case.code} in ${report.run.environment}` : `Run #${id}`}</p>
        </div>
        <div className="actions-row">
          <Link className="button secondary" to="/test-runs">
            Back
          </Link>
          <button className="button secondary" type="button" onClick={loadReport}>
            Refresh
          </button>
        </div>
      </div>

      {isLoading ? <div className="muted">Loading report...</div> : null}
      {error ? <div className="alert error">{error}</div> : null}

      {report ? (
        <>
          <div className="report-summary">
            <div className="summary-item">
              <span>Status</span>
              <StatusBadge status={report.run.status} />
            </div>
            <div className="summary-item">
              <span>Duration</span>
              <strong>{formatDuration(report.run.duration_ms)}</strong>
            </div>
            <div className="summary-item">
              <span>Started by</span>
              <strong>{report.started_by.full_name || report.started_by.email}</strong>
            </div>
            <div className="summary-item">
              <span>Module</span>
              <strong>{report.module.code}</strong>
            </div>
          </div>

          <div className="split-grid">
            <section className="panel">
              <h2>Run</h2>
              <dl className="details-list">
                <div>
                  <dt>ID</dt>
                  <dd>#{report.run.id}</dd>
                </div>
                <div>
                  <dt>Environment</dt>
                  <dd>{report.run.environment}</dd>
                </div>
                <div>
                  <dt>Started</dt>
                  <dd>{formatDate(report.run.started_at)}</dd>
                </div>
                <div>
                  <dt>Finished</dt>
                  <dd>{formatDate(report.run.finished_at)}</dd>
                </div>
                <div>
                  <dt>Error</dt>
                  <dd>{report.run.error_message || "-"}</dd>
                </div>
              </dl>
            </section>
            <section className="panel">
              <h2>Test Case</h2>
              <dl className="details-list">
                <div>
                  <dt>Code</dt>
                  <dd className="code">{report.test_case.code}</dd>
                </div>
                <div>
                  <dt>Name</dt>
                  <dd>{report.test_case.name}</dd>
                </div>
                <div>
                  <dt>Tags</dt>
                  <dd>
                    <div className="tag-list">
                      {report.test_case.tags.map((tag) => (
                        <span className="tag" key={tag}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  </dd>
                </div>
              </dl>
            </section>
          </div>

          <section className="panel">
            <h2>Steps</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Error</th>
                    <th>Request</th>
                    <th>Response</th>
                  </tr>
                </thead>
                <tbody>
                  {report.steps.map((step) => (
                    <tr key={step.id}>
                      <td>#{step.id}</td>
                      <td>{step.name}</td>
                      <td>
                        <StatusBadge status={step.status} />
                      </td>
                      <td>{formatDuration(step.duration_ms)}</td>
                      <td>{step.error_message || "-"}</td>
                      <td>
                        <JsonDetails value={step.request_json} />
                      </td>
                      <td>
                        <JsonDetails value={step.response_json} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="split-grid">
            <JsonPanel title="Parameters" value={report.run.parameters} />
            <JsonPanel title="Result" value={report.run.result} />
          </div>
        </>
      ) : null}
    </section>
  );
}

function JsonPanel({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </section>
  );
}

function JsonDetails({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="muted">-</span>;
  }

  return (
    <details className="json-details">
      <summary>JSON</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}

function formatDuration(durationMs: number | null): string {
  return durationMs === null ? "-" : `${durationMs} ms`;
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}
