// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface NotificationItem {
  id: number;
  user_id: string;
  type: string;
  actor_uri?: string | null;
  target_iri?: string | null;
  payload: Record<string, unknown>;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationsResponse {
  notifications: NotificationItem[];
  total: number;
  unread_count: number;
  limit: number;
  offset: number;
}

export const notificationQueryKeys = {
  all: ["notifications"] as const,
  list: (unreadOnly = false) => ["notifications", "list", { unreadOnly }] as const,
};

/**
 * Fetch notifications list with pagination and unread filter.
 *
 * @param unreadOnly - Filter by unread notifications only.
 * @param limit - Max notifications to return.
 * @returns {Promise<NotificationsResponse>} Response containing notifications.
 */
export async function getNotifications(unreadOnly = false, limit = 20): Promise<NotificationsResponse> {
  const query = new URLSearchParams({
    unread_only: unreadOnly ? "true" : "false",
    limit: limit.toString(),
  });
  const res = await apiClient.get<NotificationsResponse>(`/v1/notifications?${query.toString()}`);
  return res.data;
}

/**
 * Hook to retrieve notifications for the current user.
 *
 * @param unreadOnly - Filter by unread notifications only.
 * @param enabled - Whether the query is active.
 * @returns Query result.
 */
export function useNotifications(unreadOnly = false, enabled = true) {
  return useQuery<NotificationsResponse>({
    queryKey: notificationQueryKeys.list(unreadOnly),
    queryFn: () => getNotifications(unreadOnly),
    enabled,
    refetchInterval: 30_000,
    staleTime: 10_000,
  });
}

/**
 * Hook to mark specific notification IDs as read.
 *
 * @returns Mutation result.
 */
export function useMarkNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (notificationIds: number[]) => {
      const res = await apiClient.patch<{ marked_count: number }>("/v1/notifications/read", {
        notification_ids: notificationIds,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.all });
    },
  });
}

/**
 * Hook to mark all notifications as read.
 *
 * @returns Mutation result.
 */
export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post<{ marked_count: number }>("/v1/notifications/read-all", {});
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationQueryKeys.all });
    },
  });
}
