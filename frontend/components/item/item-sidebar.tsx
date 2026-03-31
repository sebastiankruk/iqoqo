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

import { ChangeEvent } from "react";
import { Pencil, QrCode, BookOpen, ImagePlus } from "lucide-react";
import { toast } from "sonner";
import type { Item } from "@/types/frbr";
import { useUpdateItem, useProfile } from "@/lib/api/hooks";
import { CameraCapture } from "@/components/scanner/camera-capture";
import { useRouter } from "next/navigation";

const STATUS_LABELS: Record<Item["status"], { label: string; class: string }> = {
  available: { label: "On Shelf", class: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  reading: { label: "Reading...", class: "bg-accent/10 text-accent ring-accent/20" },
  lent: { label: "Lent Out", class: "bg-orange-50 text-orange-700 ring-orange-200" },
  lost: { label: "Lost", class: "bg-red-50 text-red-700 ring-red-200" },
  wish_list: { label: "On Wish List", class: "bg-primary/10 text-primary ring-primary/20" },
  ordered: { label: "Ordered", class: "bg-amber-50 text-amber-700 ring-amber-200" },
  damaged: { label: "Damaged", class: "bg-orange-100 text-orange-800 ring-orange-300" },
  read: { label: "Read", class: "bg-blue-50 text-blue-700 ring-blue-200" },
  unread: { label: "Unread", class: "bg-zinc-50 text-zinc-700 ring-zinc-200" },
  listening: { label: "Listening...", class: "bg-teal-50 text-teal-700 ring-teal-200" },
  listened: { label: "Listened", class: "bg-cyan-50 text-cyan-700 ring-cyan-200" },
  want_to_listen: { label: "Want to Listen", class: "bg-sky-50 text-sky-700 ring-sky-200" },
};

/** Props for ItemSidebar component */
interface ItemSidebarProps {
  item: Item;
  onEdit?: () => void;
}

/**
 * Left sidebar of the item detail page – cover, status, actions, quick stats.
 *
 * @param root0 - The props object
 * @param root0.item - The item
 * @param root0.onEdit - Callback when edit is clicked
 * @returns {JSX.Element} The component
 */
export function ItemSidebar({ item, onEdit }: ItemSidebarProps) {
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000/api";
  const coverUrl =
    (item.cover_url ? `${apiBase}${item.cover_url}` : undefined) ??
    (item.manifestation_meta?.["cover_url"] as string | undefined) ??
    (item.meta?.["cover_url"] as string | undefined);

  const updateItem = useUpdateItem(item.id);
  const { data: profile } = useProfile();
  const hasUploadPermission = profile?.permissions?.includes("upload:cover");

  const statusInfo = STATUS_LABELS[item.status] ?? {
    label: item.status,
    class: "bg-secondary text-foreground ring-border",
  };
  const router = useRouter();

  const handleUploadComplete = () => {
    toast.success("Cover uploaded and processing started!");
    // Refresh to show 'processing' status
    router.refresh();
  };

  const handleStatusChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value as Item["status"];
    updateItem.mutate(
      { status: newStatus },
      {
        onSuccess: () => toast.success(`Item status updated to ${STATUS_LABELS[newStatus]?.label || newStatus}`),
        onError: e => toast.error((e as Error).message),
      }
    );
  };

  /**
   * Handles generating and opening the QR code for the item.
   */

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
            <img src={coverUrl} alt={item.title ?? "Cover"} className="h-full w-full object-cover" />
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
      {item.isbn && <p className="text-center text-xs text-muted-foreground">ISBN: {item.isbn}</p>}

      {/* Action buttons & Status Select */}
      <div className="flex w-full flex-col gap-2.5">
        <select
          aria-label="Item status"
          value={item.status}
          onChange={handleStatusChange}
          disabled={updateItem.isPending}
          className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground outline-none transition-opacity hover:opacity-90 disabled:opacity-60 cursor-pointer text-center appearance-none"
        >
          {Object.entries(STATUS_LABELS).map(([key, info]) => (
            <option key={key} value={key} className="text-foreground bg-card">
              {info.label}
            </option>
          ))}
        </select>

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

        {hasUploadPermission && (
          <CameraCapture
            manifestationId={item.manifestation_id}
            onUploadComplete={handleUploadComplete}
            label={item.cover_url ? "Replace Cover" : "Contribute Cover"}
            icon={<ImagePlus className="h-4 w-4 mr-2" />}
            confirmTitle={item.cover_url ? "Replace Existing Cover?" : undefined}
            confirmMessage={
              item.cover_url
                ? "This manifestation already has a cover. Are you sure you want to replace it with your own image?"
                : undefined
            }
            className="w-full [&>button]:w-full [&>button]:h-10 [&>button]:rounded-lg [&>button]:bg-accent/10 [&>button]:text-accent [&>button]:hover:bg-accent/20 [&>button]:border-none [&>button]:font-semibold [&>button]:text-xs"
          />
        )}
      </div>

      {/* FRBR quick info */}
      <div className="w-full rounded-lg border border-border bg-muted/50 p-4">
        <div className="flex flex-col gap-3">
          {item.expression && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Format</span>
              <span className="text-xs font-semibold capitalize text-foreground">{item.expression.content_type}</span>
            </div>
          )}
          {item.expression?.language && (
            <>
              <div className="h-px bg-border" />
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Language</span>
                <span className="text-xs font-semibold uppercase text-foreground">{item.expression.language}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
