import axios from "axios";
import type { ApiResponse } from "@/types/frbr";

// NEXT_PUBLIC_API_URL is the full API base URL including any path prefix.
// Local dev default: "http://localhost:5000/api" (Flask on a separate port).
// Production (nginx, same origin): "/api" — set via NEXT_PUBLIC_API_URL in .env.
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000/api";

/**
 * Preconfigured axios instance pointing at the Flask backend.
 * withCredentials is intentionally omitted: no session-based auth is
 * implemented yet. Re-add it alongside CORS_SUPPORTS_CREDENTIALS=true
 * in .env when cookie/session auth is introduced.
 */
export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

/** Unwrap the standard `{ success, data, error }` envelope. */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message: string =
      error.response?.data?.error ??
      error.message ??
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  }
);

/** Helper: GET and unwrap the `data` field from an ApiResponse envelope. */
export async function apiFetch<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const res = await apiClient.get<ApiResponse<T>>(path, { params });
  if (!res.data.success || res.data.data === null) {
    throw new Error(res.data.error ?? "Unknown error");
  }
  return res.data.data;
}
