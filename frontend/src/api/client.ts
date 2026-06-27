import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const TOKEN_STORAGE_KEY = "autotest_access_token";

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL.replace(/\/$/, "")}/api`,
  headers: {
    "Content-Type": "application/json",
  },
});

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) {
    return fallback;
  }

  const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (isApiErrorDetail(detail)) {
    const message = typeof detail.message === "string" ? detail.message : "";
    const errors = Array.isArray(detail.errors)
      ? detail.errors.filter((item): item is string => typeof item === "string").join("; ")
      : "";
    return [message, errors].filter(Boolean).join(": ") || fallback;
  }

  return fallback;
}

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAccessToken();
    }
    return Promise.reject(error);
  },
);

function isApiErrorDetail(value: unknown): value is { message?: unknown; errors?: unknown } {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
