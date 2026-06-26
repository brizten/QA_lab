import { apiClient } from "./client";

export type TestRunStatus =
  | "QUEUED"
  | "RUNNING"
  | "PASSED"
  | "FAILED"
  | "BROKEN"
  | "CANCELLED"
  | "TIMEOUT";

export interface TestRun {
  id: number;
  test_case_id: number;
  started_by_user_id: number;
  environment: string;
  status: TestRunStatus;
  parameters: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface QueueTestRunPayload {
  test_case_code: string;
  environment: string;
  parameters: Record<string, unknown>;
}

export interface QueueTestRunResponse {
  run_id: number;
  status: TestRunStatus;
}

export interface TestRunReport {
  run: {
    id: number;
    status: TestRunStatus;
    environment: string;
    parameters: Record<string, unknown>;
    result: Record<string, unknown> | null;
    error_message: string | null;
    started_at: string | null;
    finished_at: string | null;
    duration_ms: number | null;
  };
  test_case: {
    id: number;
    code: string;
    name: string;
    tags: string[];
  };
  module: {
    id: number;
    code: string;
    name: string;
  };
  started_by: {
    id: number;
    email: string;
    full_name: string | null;
  };
  steps: Array<{
    id: number;
    name: string;
    status: string;
    duration_ms: number | null;
    error_message: string | null;
    request_json: Record<string, unknown> | null;
    response_json: Record<string, unknown> | null;
  }>;
}

export async function queueTestRun(
  payload: QueueTestRunPayload,
): Promise<QueueTestRunResponse> {
  const response = await apiClient.post<QueueTestRunResponse>("/test-runs", payload);
  return response.data;
}

export async function getTestRuns(): Promise<TestRun[]> {
  const response = await apiClient.get<TestRun[]>("/test-runs");
  return response.data;
}

export async function getTestRunReport(id: number): Promise<TestRunReport> {
  const response = await apiClient.get<TestRunReport>(`/test-runs/${id}/report`);
  return response.data;
}
