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

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, apiFetch } from "./client";

export interface SocialFeedback {
  id: number;
  user_id: string;
  user_display_name: string;
  user_username: string | null;
  user_avatar_url: string | null;
  work_id: number | null;
  expression_id: number | null;
  manifestation_id: number | null;
  item_id: number | null;
  rating: number | null;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

export interface FeedbackStats {
  average_rating: number;
  total_count: number;
  total_ratings: number;
  rating_counts: Record<string, number>;
}

export interface FeedbackResponse {
  success: boolean;
  feedbacks: SocialFeedback[];
  stats: FeedbackStats;
}

export const feedbackQueryKeys = {
  feedbacks: (level: string, targetId: number) => ["feedback", level, targetId] as const,
};

/**
 * Hook to retrieve ratings and comments for a given FRBR resource level and ID.
 *
 * @param level - The FRBR level ('work', 'expression', 'manifestation', 'item').
 * @param targetId - The database ID of the target resource.
 * @param enabled - Whether the query is enabled (default true).
 * @returns Query result containing ratings and comments.
 */
export function useSocialFeedback(level: string, targetId: number, enabled = true) {
  return useQuery<FeedbackResponse>({
    queryKey: feedbackQueryKeys.feedbacks(level, targetId),
    queryFn: () => apiFetch<FeedbackResponse>(`/feedback/${level}/${targetId}`),
    enabled: enabled && targetId > 0,
    staleTime: 15_000,
  });
}

/**
 * Hook to submit or update a review.
 *
 * @returns Mutation result to submit feedback.
 */
export function useSubmitFeedback() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async ({
      level,
      targetId,
      rating,
      comment,
    }: {
      level: string;
      targetId: number;
      rating: number | null;
      comment: string | null;
    }) => {
      const res = await apiClient.post<{ success: boolean; data: SocialFeedback }>(`/feedback/${level}/${targetId}`, {
        rating,
        comment,
      });
      return res.data;
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({
        queryKey: feedbackQueryKeys.feedbacks(variables.level, variables.targetId),
      });
    },
  });
}

/**
 * Hook to delete a review.
 *
 * @returns Mutation result to delete feedback.
 */
export function useDeleteFeedback() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async ({ level, targetId }: { level: string; targetId: number }) => {
      const res = await apiClient.delete<{ success: boolean; message: string }>(`/feedback/${level}/${targetId}`);
      return res.data;
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({
        queryKey: feedbackQueryKeys.feedbacks(variables.level, variables.targetId),
      });
    },
  });
}
