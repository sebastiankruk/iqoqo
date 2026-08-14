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
 * Feedback submission dialog with optional screenshot attachments.
 * @param root0 - Component properties.
 * @param root0.open - Whether the dialog is visible.
 * @param root0.onOpenChange - Visibility change callback.
 * @returns Feedback submission dialog.
 */
export function FeedbackModal({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [type, setType] = useState("bug");
  const [description, setDescription] = useState("");
  const [screenshots, setScreenshots] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const submit = async () => {
    if (!description.trim()) return;
    setSaving(true);
    try {
      const form = new FormData();
      form.set("type", type);
      form.set("description", description.trim());
      screenshots.forEach(file => form.append("screenshots", file));
      await apiClient.post("/feedback", form, { headers: { "Content-Type": "multipart/form-data" } });
      setDescription("");
      setScreenshots([]);
      setMessage("Thanks — your feedback was submitted.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to submit feedback.");
    } finally {
      setSaving(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send feedback</DialogTitle>
          <DialogDescription>Report a bug or suggest a feature for iqoqo.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <select
            className="h-10 w-full rounded-md border bg-background px-3 text-sm"
            value={type}
            onChange={event => setType(event.target.value)}
          >
            <option value="bug">Bug</option>
            <option value="feature_request">Feature request</option>
          </select>
          <textarea
            className="min-h-32 w-full rounded-md border bg-background p-3 text-sm"
            placeholder="Describe the issue or idea"
            value={description}
            onChange={event => setDescription(event.target.value)}
          />
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            onChange={event => setScreenshots(Array.from(event.target.files ?? []))}
          />
          {message && <p className="text-sm text-muted-foreground">{message}</p>}
        </div>
        <DialogFooter>
          <button
            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
            disabled={saving || !description.trim()}
            onClick={submit}
          >
            {saving ? "Submitting…" : "Submit feedback"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
