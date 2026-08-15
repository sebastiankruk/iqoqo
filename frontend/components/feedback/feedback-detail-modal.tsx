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
"use client";

import { useState } from "react";
import Image from "next/image";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiClient } from "@/lib/api/client";
import { resolveApiUrl } from "@/lib/utils";
import {
  AlertCircle,
  Bug,
  Lightbulb,
  MessageSquare,
  Paperclip,
  CheckCircle2,
  Clock,
  Send,
  User as UserIcon,
} from "lucide-react";

export type FeedbackComment = {
  id: string;
  user_id: string;
  user_display_name: string;
  comment: string;
  created_at: string;
};

export type FeedbackItemDetail = {
  id: number;
  user_id: string;
  user_display_name: string;
  user_email?: string | null;
  feedback_type: string;
  description: string;
  status: string;
  attachments: string[];
  comments?: FeedbackComment[];
  comments_count?: number;
  created_at: string;
  updated_at: string;
};

interface FeedbackDetailModalProps {
  item: FeedbackItemDetail | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isAdmin: boolean;
  currentUserId?: string;
  onUpdated?: () => void;
}

const statusColorMap: Record<string, { bg: string; text: string; border: string; label: string }> = {
  new: { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", border: "border-blue-500/20", label: "New" },
  accepted: {
    bg: "bg-purple-500/10",
    text: "text-purple-600 dark:text-purple-400",
    border: "border-purple-500/20",
    label: "Accepted",
  },
  in_progress: {
    bg: "bg-amber-500/10",
    text: "text-amber-600 dark:text-amber-400",
    border: "border-amber-500/20",
    label: "In Progress",
  },
  in_validation: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-600 dark:text-emerald-400",
    border: "border-emerald-500/20",
    label: "In Validation",
  },
  closed: { bg: "bg-muted", text: "text-muted-foreground", border: "border-border", label: "Closed" },
};

/**
 * Detailed view modal for reviewing, updating, and commenting on a feedback ticket.
 *
 * @param root0 - Component props
 * @param root0.item - The feedback item to display
 * @param root0.open - Dialog visibility state
 * @param root0.onOpenChange - Dialog open change handler
 * @param root0.isAdmin - Whether current user has admin privileges
 * @param root0.currentUserId - Authenticated user UUID
 * @param root0.onUpdated - Callback after state changes
 * @returns {JSX.Element | null} Component
 */
export function FeedbackDetailModal({
  item,
  open,
  onOpenChange,
  isAdmin,
  currentUserId,
  onUpdated,
}: FeedbackDetailModalProps) {
  const [selectedStatus, setSelectedStatus] = useState<string>(item?.status || "new");
  const [newComment, setNewComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!item) return null;

  const isCreator = currentUserId ? item.user_id === currentUserId : false;
  const statusInfo = statusColorMap[item.status] || {
    bg: "bg-muted",
    text: "text-foreground",
    border: "border-border",
    label: item.status,
  };

  const handleStatusChange = async (statusToSet: string) => {
    setSaving(true);
    setError("");
    try {
      await apiClient.patch(`/feedback/${item.id}`, { status: statusToSet });
      setSelectedStatus(statusToSet);
      onUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status.");
    } finally {
      setSaving(false);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    setSaving(true);
    setError("");
    try {
      await apiClient.patch(`/feedback/${item.id}`, { comment: newComment.trim() });
      setNewComment("");
      onUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add comment.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col p-0 overflow-hidden">
        <DialogHeader className="p-6 pb-4 border-b border-border">
          <div className="flex flex-wrap items-center justify-between gap-2 pr-6">
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusInfo.bg} ${statusInfo.text} ${statusInfo.border}`}
              >
                {statusInfo.label}
              </span>
              <span className="text-xs text-muted-foreground">Ticket #{item.id}</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {item.feedback_type === "bug" ? (
                <>
                  <Bug className="h-3.5 w-3.5 text-rose-500" />
                  <span>Bug Report</span>
                </>
              ) : (
                <>
                  <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
                  <span>Feature Request</span>
                </>
              )}
            </div>
          </div>
          <DialogTitle className="text-lg font-bold mt-2">
            {item.description.slice(0, 80)}
            {item.description.length > 80 ? "…" : ""}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground flex items-center gap-3 mt-1">
            <span className="flex items-center gap-1">
              <UserIcon className="h-3 w-3" />
              {item.user_display_name}
              {isAdmin && item.user_email && <span className="opacity-75">({item.user_email})</span>}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {new Date(item.created_at).toLocaleString()}
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Description */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Description</h4>
            <div className="rounded-lg border border-border bg-muted/20 p-4 text-sm whitespace-pre-wrap leading-relaxed">
              {item.description}
            </div>
          </div>

          {/* Attachments */}
          {item.attachments && item.attachments.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Paperclip className="h-3.5 w-3.5" />
                Attachments ({item.attachments.length})
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {item.attachments.map((url, idx) => {
                  const resolvedUrl = resolveApiUrl(url);
                  return (
                    <a
                      key={idx}
                      href={resolvedUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group relative aspect-video rounded-md border border-border overflow-hidden bg-muted/40 hover:ring-2 hover:ring-primary transition-all"
                    >
                      <Image
                        src={resolvedUrl}
                        alt={`Attachment ${idx + 1}`}
                        fill
                        unoptimized
                        className="object-cover group-hover:scale-105 transition-transform duration-200"
                      />
                    </a>
                  );
                })}
              </div>
            </div>
          )}

          {/* Lifecycle controls */}
          {(isAdmin || (isCreator && item.status !== "closed")) && (
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Ticket Actions</h4>
              <div className="flex flex-wrap items-center gap-3">
                {isAdmin ? (
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-medium">Status:</label>
                    <select
                      className="rounded-md border border-input bg-background px-3 py-1.5 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-primary"
                      value={selectedStatus}
                      onChange={e => {
                        setSelectedStatus(e.target.value);
                        void handleStatusChange(e.target.value);
                      }}
                      disabled={saving}
                    >
                      <option value="new">New</option>
                      <option value="accepted">Accepted</option>
                      <option value="in_progress">In Progress</option>
                      <option value="in_validation">In Validation</option>
                      <option value="closed">Closed</option>
                    </select>
                  </div>
                ) : null}

                {isCreator && item.status !== "closed" && (
                  <button
                    type="button"
                    onClick={() => void handleStatusChange("closed")}
                    disabled={saving}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted/50 px-3 py-1.5 text-xs font-semibold hover:bg-muted transition-colors disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                    Close My Ticket
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Comments Section */}
          <div className="space-y-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5" />
              Comments ({item.comments?.length ?? 0})
            </h4>

            {item.comments && item.comments.length > 0 ? (
              <div className="space-y-3">
                {item.comments.map(c => (
                  <div key={c.id} className="rounded-lg border border-border/70 bg-card p-3 space-y-1.5">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="font-semibold text-foreground">{c.user_display_name}</span>
                      <span>{new Date(c.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-xs text-muted-foreground/90 whitespace-pre-wrap">{c.comment}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">No comments yet.</p>
            )}

            {/* Add Comment Form */}
            <form onSubmit={handleAddComment} className="flex gap-2 pt-2">
              <input
                type="text"
                placeholder="Leave a comment..."
                value={newComment}
                onChange={e => setNewComment(e.target.value)}
                disabled={saving}
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                type="submit"
                disabled={saving || !newComment.trim()}
                className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-50 hover:opacity-90 transition-opacity"
              >
                <Send className="h-3 w-3" />
                <span>Post</span>
              </button>
            </form>
          </div>
        </div>

        <DialogFooter className="p-4 border-t border-border bg-muted/10 sm:justify-end">
          <button
            type="button"
            className="rounded-md border border-border bg-background px-4 py-2 text-xs font-semibold text-foreground hover:bg-muted transition-colors"
            onClick={() => onOpenChange(false)}
          >
            Close
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
