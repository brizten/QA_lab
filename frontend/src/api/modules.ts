import { apiClient } from "./client";

export interface Module {
  id: number;
  code: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export async function getModules(): Promise<Module[]> {
  const response = await apiClient.get<Module[]>("/modules");
  return response.data;
}
