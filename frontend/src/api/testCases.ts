import { apiClient } from "./client";

export type InputSchema = Record<string, unknown>;

export interface TestCase {
  id: number;
  code: string;
  name: string;
  description: string | null;
  module_id: number;
  owner_id: number;
  input_schema: InputSchema;
  tags: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TestCaseFilters {
  module_id?: number;
  tag?: string;
  is_active?: boolean;
}

export async function getTestCases(filters: TestCaseFilters = {}): Promise<TestCase[]> {
  const response = await apiClient.get<TestCase[]>("/test-cases", { params: filters });
  return response.data;
}
