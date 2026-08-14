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
import { CheckCircle2, AlertCircle } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/**
 * Feedback submission dialog with optional screenshot attachments and clear success state.
 * @param root0 - Component properties.
 * @param root0.open - Whether the dialog is visible.
 * @param root0.onOpenChange - Visibility change callback.
 * @param root0.onSuccess - Optional callback when feedback is submitted.
 * @returns Feedback submission dialog.
 */
export function FeedbackModal({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}) {
  const [type, setType] = useState("bug");
  const [description, setDescription] = useState("");
  const [screenshots, setScreenshots] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleClose = () => {
    onOpenChange(false);
    // Reset state after dialog animation completes
    setTimeout(() => {
      setSubmitted(false);
      setDescription("");
      setScreenshots([]);
      setError("");
    }, 200);
  };

  const submit = async () => {
    if (!description.trim()) return;
    setSaving(true);
    setError("");
    try {
      const form = new FormData();
      form.set("type", type);
      form.set("description", description.trim());
      screenshots.forEach(file => form.append("screenshots", file));
      await apiClient.post("/feedback", form, { headers: { "Content-Type": "multipart/form-data" } });
      setSubmitted(true);
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to submit feedback.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={nextOpen => {
        if (!nextOpen) {
          handleClose();
        } else {
          onOpenChange(true);
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        {submitted ? (
          <div className="flex flex-col items-center justify-center py-6 text-center space-y-4">
            <div className="rounded-full bg-green-500/10 p-3 text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-10 w-10" />
            </div>
            <div className="space-y-1">
              <DialogTitle className="text-xl font-bold">Feedback Submitted</DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground max-w-xs">
                Thanks — your feedback was successfully submitted and logged.
              </DialogDescription>
            </div>
            <DialogFooter className="w-full pt-4 sm:justify-center">
              <button
                type="button"
                className="w-full sm:w-auto min-w-[120px] rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
                onClick={handleClose}
              >
                Close
              </button>
            </DialogFooter>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Send feedback</DialogTitle>
              <DialogDescription>Report a bug or suggest a feature for iqoqo.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              {error && (
                <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Type</label>
                <select
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  value={type}
                  onChange={event => setType(event.target.value)}
                >
                  <option value="bug">Bug</option>
                  <option value="feature_request">Feature request</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Description</label>
                <textarea
                  className="min-h-32 w-full rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Describe the issue or idea..."
                  value={description}
                  onChange={event => setDescription(event.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Attachments (optional)</label>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  multiple
                  className="block w-full text-xs text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-2 file:text-xs file:font-semibold file:text-foreground hover:file:bg-muted/80"
                  onChange={event => setScreenshots(Array.from(event.target.files ?? []))}
                />
              </div>
            </div>
            <DialogFooter>
              <button
                type="button"
                className="w-full sm:w-auto rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50 transition-opacity hover:opacity-90"
                disabled={saving || !description.trim()}
                onClick={submit}
              >
                {saving ? "Submitting…" : "Submit feedback"}
              </button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
