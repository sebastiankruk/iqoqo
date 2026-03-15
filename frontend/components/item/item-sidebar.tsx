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

import { Send, Pencil, QrCode, BookOpen } from "lucide-react";
import { toast } from "sonner";
import type { Item } from "@/types/frbr";
import { useUpdateItem } from "@/lib/api/hooks";

const STATUS_LABELS: Record<string, { label: string; class: string }> = {
  available: {
    label: "On Shelf",
    class: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
  reading: {
    label: "Reading",
    class: "bg-accent/10 text-accent ring-accent/20",
  },
  lent: { label: "Lent Out", class: "bg-orange-50 text-orange-700 ring-orange-200" },
  lost: { label: "Lost", class: "bg-red-50 text-red-700 ring-red-200" },
  wish_list: {
    label: "On Wish List",
    class: "bg-primary/10 text-primary ring-primary/20",
  },
  read: {
    label: "Read",
    class: "bg-blue-50 text-blue-700 ring-blue-200",
  },
};

interface ItemSidebarProps {
  item: Item;
  onEdit?: () => void;
}

/** Left sidebar of the item detail page – cover, status, actions, quick stats. */
export function ItemSidebar({ item, onEdit }: ItemSidebarProps) {
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000/api";
  const coverUrl =
    (item.cover_url ? `${apiBase}${item.cover_url}` : undefined) ??
    (item.manifestation_meta?.["cover_url"] as string | undefined) ??
    (item.meta?.["cover_url"] as string | undefined);

  const updateItem = useUpdateItem(item.id);

  const statusInfo = STATUS_LABELS[item.status] ?? {
    label: item.status,
    class: "bg-secondary text-foreground ring-border",
  };

  const handleLend = () => {
    updateItem.mutate(
      { status: "lent" },
      {
        onSuccess: () => toast.success("Item marked as lent out"),
        onError: (e) => toast.error(e.message),
      }
    );
  };

  const handleQrCode = async () => {
    const url = `${apiBase}/qrcode/${item.id}`;
    try {
      const response = await fetch(url, { method: "HEAD" });

      if (!response.ok) {
      toast.error("Unable to generate QR code. Please try again later.");
      return;
      }

      window.open(url, "_blank");
    } catch {
      toast.error("Failed to contact QR code service. Please check your connection and try again.");
    }
  };

  return (
    <div className="flex flex-col items-center gap-5">
      {/* Book cover */}
      <div className="-mt-28 w-full max-w-[220px]">
        <div className="relative aspect-[2/3] w-full overflow-hidden rounded-lg shadow-xl ring-4 ring-card bg-secondary">
          {coverUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={coverUrl}
              alt={item.title ?? "Cover"}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <BookOpen className="h-12 w-12 text-muted-foreground/30" />
            </div>
          )}
        </div>
      </div>

      {/* Status badge */}
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ${statusInfo.class}`}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
        {statusInfo.label}
      </span>

      {/* ISBN */}
      {item.isbn && (
        <p className="text-center text-xs text-muted-foreground">
          ISBN: {item.isbn}
        </p>
      )}

      {/* Action buttons */}
      <div className="flex w-full flex-col gap-2.5">
        <button
          onClick={handleLend}
          disabled={updateItem.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          <Send className="h-4 w-4" />
          Lend to Friend
        </button>
        {onEdit && (
          <button
            onClick={onEdit}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-secondary px-4 py-2.5 text-sm font-semibold text-secondary-foreground transition-colors hover:bg-secondary/80"
          >
            <Pencil className="h-4 w-4" />
            Edit Metadata
          </button>
        )}
        <button
          onClick={handleQrCode}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-muted"
        >
          <QrCode className="h-4 w-4" />
          Print QR Code
        </button>
      </div>

      {/* FRBR quick info */}
      <div className="w-full rounded-lg border border-border bg-muted/50 p-4">
        <div className="flex flex-col gap-3">
          {item.expression && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Format</span>
              <span className="text-xs font-semibold capitalize text-foreground">
                {item.expression.content_type}
              </span>
            </div>
          )}
          {item.expression?.language && (
            <>
              <div className="h-px bg-border" />
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Language</span>
                <span className="text-xs font-semibold uppercase text-foreground">
                  {item.expression.language}
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
