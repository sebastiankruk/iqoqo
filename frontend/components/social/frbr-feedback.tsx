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

"use client";

import { useState } from "react";
import type { SocialFeedback } from "@/lib/api/social";
import { useSocialFeedback, useSubmitFeedback, useDeleteFeedback } from "@/lib/api/social";
import { useProfile } from "@/lib/api/hooks";
import { StarRating } from "./star-rating";
import { FRBRNotes } from "./frbr-notes";
import { Button } from "@/components/ui/button";
import { Loader2, MessageSquare, Trash2, Edit3, User } from "lucide-react";
import { toast } from "sonner";
import Image from "next/image";

interface FRBRFeedbackProps {
  level: "work" | "expression" | "manifestation" | "item";
  targetId: number;
  title: string;
}

interface FeedbackFormProps {
  level: "work" | "expression" | "manifestation" | "item";
  targetId: number;
  title: string;
  userFeedback: SocialFeedback | undefined;
  refetch: () => Promise<unknown>;
}

/**
 * Dedicated sub-component for rating and comment submission form.
 * Handled via keyed container inside parent to eliminate need for useEffect state updates.
 *
 * @param props - Sub-component props.
 * @param props.level - The target FRBR level.
 * @param props.targetId - Target resource ID.
 * @param props.title - User-friendly title.
 * @param props.userFeedback - Existing user review record, if any.
 * @param props.refetch - Callback to reload feedbacks list.
 * @returns The feedback form component.
 */
function FeedbackForm({ level, targetId, title, userFeedback, refetch }: FeedbackFormProps) {
  const submitMutation = useSubmitFeedback();
  const deleteMutation = useDeleteFeedback();

  const [userRating, setUserRating] = useState<number>(userFeedback?.rating ?? 0);
  const [comment, setComment] = useState<string>(userFeedback?.comment ?? "");
  const [isEditing, setIsEditing] = useState<boolean>(!userFeedback);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (userRating === 0) {
      toast.error("Please select a star rating");
      return;
    }

    try {
      await submitMutation.mutateAsync({
        level,
        targetId,
        rating: userRating,
        comment: comment.trim() || null,
      });
      toast.success("Review submitted!");
      await refetch();
      setIsEditing(false);
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to submit review");
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete your review?")) {
      return;
    }

    try {
      await deleteMutation.mutateAsync({ level, targetId });
      toast.success("Review deleted");
      await refetch();
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || "Failed to delete review");
    }
  };

  return (
    <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
      <h4 className="mb-4 font-serif text-base font-bold text-foreground">
        {userFeedback ? "Your Review" : `Rate this ${title}`}
      </h4>

      {userFeedback && !isEditing ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <StarRating rating={userFeedback.rating ?? 0} readOnly size="md" />
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
                <Edit3 className="mr-1.5 h-3.5 w-3.5" />
                Edit
              </Button>
              <Button variant="ghost" size="sm" className="text-destructive" onClick={handleDelete}>
                <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                Delete
              </Button>
            </div>
          </div>
          {userFeedback.comment && (
            <p className="text-sm text-foreground/90 whitespace-pre-wrap pl-0.5 leading-relaxed">
              {userFeedback.comment}
            </p>
          )}
          <p className="text-[10px] text-muted-foreground font-medium pl-0.5">
            Last updated on {new Date(userFeedback.updated_at).toLocaleDateString()}
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-muted-foreground">Your rating:</span>
            <StarRating rating={userRating} onChange={setUserRating} size="lg" />
          </div>

          <div className="space-y-2">
            <textarea
              placeholder={`Write your comments, thoughts, or remarks on this ${title} level...`}
              value={comment}
              onChange={e => setComment(e.target.value)}
              className="min-h-[100px] w-full resize-y rounded-xl border border-border/80 bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={submitMutation.isPending}>
              {submitMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {userFeedback ? "Update Review" : "Post Review"}
            </Button>
            {userFeedback && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setUserRating(userFeedback.rating ?? 0);
                  setComment(userFeedback.comment ?? "");
                  setIsEditing(false);
                }}
              >
                Cancel
              </Button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}

/**
 * Premium review and rating component supporting custom levels of the FRBR hierarchy.
 *
 * @param props - Component props.
 * @param props.level - The FRBR level ('work', 'expression', 'manifestation', 'item').
 * @param props.targetId - The database ID of the target resource.
 * @param props.title - The user-friendly title of the level.
 * @returns The rendered FRBR feedback section.
 */
export function FRBRFeedback({ level, targetId, title }: FRBRFeedbackProps) {
  const { data: profile } = useProfile();
  const { data: feedbackData, isLoading, isError, refetch } = useSocialFeedback(level, targetId, level !== "item");

  if (level === "item") {
    return <FRBRNotes level={level} targetId={targetId} title={title} />;
  }

  // Check if current user already submitted feedback
  const userFeedback = feedbackData?.feedbacks.find(f => {
    if (profile?.id && f.user_id === profile.id) return true;
    if (profile?.public_username && f.user_username === profile.public_username) return true;
    return false;
  });

  if (isLoading) {
    return (
      <div className="flex h-36 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  if (isError || !feedbackData) {
    return <div className="py-6 text-center text-sm text-muted-foreground">Failed to load ratings and comments.</div>;
  }

  const { feedbacks, stats } = feedbackData;
  const otherFeedbacks = feedbacks.filter(f => {
    const isCurrentUser =
      (profile?.id && f.user_id === profile.id) ||
      (profile?.public_username && f.user_username === profile.public_username);
    return !isCurrentUser;
  });

  return (
    <div className="space-y-6">
      {/* Overview Stat Section */}
      <div className="flex flex-col gap-6 rounded-xl border border-border/60 bg-muted/5 p-6 md:flex-row md:items-center">
        <div className="flex flex-col items-center justify-center text-center md:border-r md:pr-8">
          <span className="font-serif text-5xl font-extrabold text-foreground">{stats.average_rating.toFixed(1)}</span>
          <div className="mt-2">
            <StarRating rating={Math.round(stats.average_rating)} readOnly size="md" />
          </div>
          <span className="mt-2 text-xs text-muted-foreground font-medium">
            Based on {stats.total_ratings} {stats.total_ratings === 1 ? "rating" : "ratings"}
          </span>
        </div>

        {/* Star breakdown bar graphs */}
        <div className="flex-1 space-y-2">
          {([5, 4, 3, 2, 1] as const).map(stars => {
            const count = stats.rating_counts[String(stars)] || 0;
            const percentage = stats.total_ratings > 0 ? (count / stats.total_ratings) * 100 : 0;

            return (
              <div key={stars} className="flex items-center gap-3 text-sm">
                <span className="w-12 text-xs font-semibold text-muted-foreground tabular-nums">{stars} stars</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full rounded-full bg-amber-400 transition-all duration-300"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="w-8 text-right text-xs font-semibold text-muted-foreground tabular-nums">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Interactive Form Section */}
      {profile && (
        <FeedbackForm
          key={userFeedback?.id || "new"}
          level={level}
          targetId={targetId}
          title={title}
          userFeedback={userFeedback}
          refetch={refetch}
        />
      )}

      {/* Other Reviews List */}
      <div className="space-y-4">
        <h4 className="font-serif text-base font-bold text-foreground">Community Reviews ({otherFeedbacks.length})</h4>

        {otherFeedbacks.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed p-10 text-center">
            <MessageSquare className="h-8 w-8 text-muted-foreground/40" />
            <span className="mt-2 text-sm font-medium text-muted-foreground">No other reviews yet</span>
            <span className="text-xs text-muted-foreground/80 mt-0.5">Be the first to share your thoughts.</span>
          </div>
        ) : (
          <div className="divide-y divide-border/60 rounded-xl border bg-card shadow-sm overflow-hidden">
            {otherFeedbacks.map(feedback => (
              <div key={feedback.id} className="p-5 space-y-2 transition-colors duration-150 hover:bg-muted/5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary border text-muted-foreground overflow-hidden">
                      {feedback.user_avatar_url ? (
                        <Image
                          src={feedback.user_avatar_url}
                          alt={feedback.user_display_name}
                          fill
                          className="object-cover"
                          unoptimized
                        />
                      ) : (
                        <User className="h-4 w-4" />
                      )}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-foreground">{feedback.user_display_name}</div>
                      <div className="text-[10px] text-muted-foreground font-medium">
                        @{feedback.user_username || "anonymous"} &bull;{" "}
                        {new Date(feedback.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <StarRating rating={feedback.rating ?? 0} readOnly size="sm" />
                </div>
                {feedback.comment && (
                  <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap pl-11">
                    {feedback.comment}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Notes / Remarks Section */}
      <div className="pt-6 border-t border-border/50">
        <FRBRNotes level={level} targetId={targetId} title={title} />
      </div>
    </div>
  );
}
