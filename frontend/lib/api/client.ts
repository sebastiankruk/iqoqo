import axios from "axios";
import type { ApiResponse } from "@/types/frbr";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000";

/**
 * Preconfigured axios instance pointing at the Flask backend.
 * Requests include cookies so Flask session-based auth works seamlessly.
 */
export const apiClient = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
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
