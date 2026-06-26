import { apiClient, clearAccessToken, setAccessToken } from "./client";

export type UserRole = "ADMIN" | "AUTOTESTER" | "QA" | "BUSINESS" | "VIEWER";

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/auth/login", payload);
  setAccessToken(response.data.access_token);
  return response.data;
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const response = await apiClient.get<CurrentUser>("/users/me");
  return response.data;
}

export function logout(): void {
  clearAccessToken();
}
