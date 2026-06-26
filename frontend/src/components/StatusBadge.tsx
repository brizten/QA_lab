import { TestRunStatus } from "../api/testRuns";

interface StatusBadgeProps {
  status: TestRunStatus | string;
}

const toneByStatus: Record<string, string> = {
  QUEUED: "neutral",
  RUNNING: "info",
  PASSED: "success",
  FAILED: "danger",
  BROKEN: "warning",
  CANCELLED: "neutral",
  TIMEOUT: "warning",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const tone = toneByStatus[status] ?? "neutral";
  return <span className={`status-badge ${tone}`}>{status}</span>;
}
