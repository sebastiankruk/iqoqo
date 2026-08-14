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

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
type FeedbackItem = {
  id: number;
  feedback_type: string;
  description: string;
  status: string;
  created_at: string;
  user_display_name?: string;
};
/**
 * Displays the authenticated user's feedback tickets.
 * @returns Feedback management page.
 */
export default function FeedbackPage() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  useEffect(() => {
    void apiClient
      .get<{ data: FeedbackItem[] }>("/feedback", { params: { status: status || undefined, type: type || undefined } })
      .then(response => setItems(response.data.data));
  }, [status, type]);
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <div>
        <h1 className="font-serif text-3xl font-bold">Feedback</h1>
        <p className="text-muted-foreground">View and filter submitted reports.</p>
      </div>
      <div className="flex gap-3">
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={type}
          onChange={event => setType(event.target.value)}
        >
          <option value="">All types</option>
          <option value="bug">Bugs</option>
          <option value="feature_request">Feature requests</option>
        </select>
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={status}
          onChange={event => setStatus(event.target.value)}
        >
          <option value="">All statuses</option>
          {["new", "accepted", "in_progress", "in_validation", "closed"].map(value => (
            <option key={value} value={value}>
              {value.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-3">
        {items.map(item => (
          <article key={item.id} className="rounded-lg border p-4">
            <div className="flex justify-between gap-4">
              <strong>{item.feedback_type === "bug" ? "Bug" : "Feature request"}</strong>
              <span className="text-sm text-muted-foreground">{item.status.replaceAll("_", " ")}</span>
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm">{item.description}</p>
            <p className="mt-3 text-xs text-muted-foreground">
              {item.user_display_name ?? "User"} · {new Date(item.created_at).toLocaleString()}
            </p>
          </article>
        ))}
      </div>
    </main>
  );
}
