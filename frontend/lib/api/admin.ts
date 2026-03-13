import { apiFetch, apiClient } from "./client";
import type { ApiResponse } from "@/types/frbr";

export async function getUsers(): Promise<any[]> {
  return apiFetch<any[]>('/v1/admin/users');
}

export async function getInstanceSettings(): Promise<Record<string, any>> {
  return apiFetch<Record<string, any>>("/v1/admin/settings");
}

export async function updateInstanceSettings(settings: Record<string, any>): Promise<Record<string, any>> {
  const res = await apiClient.put<ApiResponse<Record<string, any>>>("/v1/admin/settings", settings);
  if (!res.data.success || !res.data.data) {
    throw new Error(res.data.error ?? "Failed to update settings");
  }
  return res.data.data;
}
