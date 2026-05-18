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

import * as React from "react";
import { ChangeEvent } from "react";
import { Pencil, /* QrCode, */ BookOpen, Disc, ImagePlus, Film, Gamepad2, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import type { Item, MediaFormat } from "@/types/frbr";
import { useUpdateItem, useProfile, useUserSearch } from "@/lib/api/hooks";
import { CameraCapture } from "@/components/scanner/camera-capture";
import { MultiImageUploader } from "@/components/scanner/multi-image-uploader";
import { TaxonomyEditor } from "@/components/item/taxonomy-editor";
import { useRouter } from "next/navigation";
import { PermissionName } from "@/lib/permissions";
import { isAudioMedia, getCoverUrl, getCoverTimestamp } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

const STATUS_LABELS: Record<string, { label: string; class: string }> = {
  // Collection (Physical)
  available: { label: "On Shelf", class: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  lent: { label: "Lent Out", class: "bg-orange-50 text-orange-700 ring-orange-200" },
  lost: { label: "Lost", class: "bg-red-50 text-red-700 ring-red-200" },
  wish_list: { label: "On Wish List", class: "bg-primary/10 text-primary ring-primary/20" },
  ordered: { label: "Ordered", class: "bg-amber-50 text-amber-700 ring-amber-200" },
  damaged: { label: "Damaged", class: "bg-orange-100 text-orange-800 ring-orange-300" },
  // Progress
  reading: { label: "Reading...", class: "bg-accent/10 text-accent ring-accent/20" },
  read: { label: "Read", class: "bg-blue-50 text-blue-700 ring-blue-200" },
  unread: { label: "Unread", class: "bg-zinc-50 text-zinc-700 ring-zinc-200" },
  want_to_read: { label: "Want to Read", class: "bg-primary/10 text-primary ring-primary/20" },
  listening: { label: "Listening...", class: "bg-teal-50 text-teal-700 ring-teal-200" },
  listened: { label: "Listened", class: "bg-cyan-50 text-cyan-700 ring-cyan-200" },
  want_to_listen: { label: "Want to Listen", class: "bg-sky-50 text-sky-700 ring-sky-200" },
  watching: { label: "Watching...", class: "bg-indigo-50 text-indigo-700 ring-indigo-200" },
  watched: { label: "Watched", class: "bg-violet-50 text-violet-700 ring-violet-200" },
  want_to_watch: { label: "Want to Watch", class: "bg-indigo-50/50 text-indigo-600 ring-indigo-200" },
  want_to_play: { label: "Want to Play", class: "bg-rose-50/50 text-rose-600 ring-rose-200" },
  played: { label: "Played", class: "bg-rose-50 text-rose-700 ring-rose-200" },
  playing: { label: "Playing...", class: "bg-pink-50 text-pink-700 ring-pink-200" },
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
  const timestamp = getCoverTimestamp(item.manifestation_meta, item.meta);

  const coverUrl =
    getCoverUrl(item.cover_url || undefined, timestamp) ??
    getCoverUrl(item.manifestation_meta?.["cover_url"] as string | undefined, timestamp) ??
    getCoverUrl(item.meta?.["cover_url"] as string | undefined, timestamp);

  const updateItem = useUpdateItem(item.id);
  const { data: profile } = useProfile();
  const permissions = profile?.permissions ?? [];
  const hasUploadPermission = permissions.includes(PermissionName.UPLOAD_COVER);
  const hasEditPermission = permissions.includes(PermissionName.WRITE_METADATA);
  const hasUpdateItemPermission = permissions.includes(PermissionName.UPDATE_ITEM);

  const isOwner = !!item.is_owner;
  const canModifyItem = isOwner || hasUpdateItemPermission;

  // Media type detection
  const format =
    (item.manifestation_meta?.["format"] as string | undefined) ??
    (item.meta?.["format"] as string | undefined) ??
    "book";
  const isAudio = isAudioMedia(format);
  const isVideo = ["dvd", "bluray", "video", "moving image"].includes(format?.toLowerCase() || "");
  const isGame = ["boardgame", "board_game", "three-dimensional object"].includes(format?.toLowerCase() || "");
  const isBook = !isAudio && !isVideo && !isGame;

  const aspectClass = isAudio || isGame ? "aspect-square" : "aspect-[2/3]";
  const MediaIcon = isAudio ? Disc : isVideo ? Film : isGame ? Gamepad2 : BookOpen;

  const progressStatusInfo = STATUS_LABELS[item.status] ?? {
    label: item.status,
    class: "bg-secondary text-foreground ring-border",
  };
  const collectionStatusInfo = STATUS_LABELS[item.collection_status] ?? {
    label: item.collection_status,
    class: "bg-secondary text-foreground ring-border",
  };
  const router = useRouter();

  const handleUploadComplete = () => {
    toast.success("Cover uploaded and processing started!");
    // Refresh to show 'processing' status
    router.refresh();
  };

  const [isLentDialogOpen, setIsLentDialogOpen] = React.useState(false);
  const [borrowerName, setBorrowerName] = React.useState(item.lent_to_name || "");
  const [borrowerId, setBorrowerId] = React.useState<string | undefined>(item.lent_to_user_id || undefined);

  // Hook for user search, enabled when borrowerName is typed and doesn't exactly match the selected ID
  const [searchFocused, setSearchFocused] = React.useState(false);
  const { data: searchResults, isLoading: isSearching } = useUserSearch(borrowerName, searchFocused);

  const handleStatusChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value as Item["status"];
    updateItem.mutate(
      { status: newStatus },
      {
        onSuccess: () => toast.success(`Progress status updated to ${STATUS_LABELS[newStatus]?.label || newStatus}`),
        onError: e => toast.error((e as Error).message),
      }
    );
  };

  const handleCollectionStatusChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value as Item["collection_status"];

    if (newStatus === "lent") {
      setIsLentDialogOpen(true);
      return;
    }

    // If moving away from 'lent', we should clear the borrower info
    const updatePayload: Partial<Item> = { collection_status: newStatus };
    if (item.collection_status === "lent") {
      updatePayload.lent_to_name = null;
      updatePayload.lent_to_user_id = null;
    }

    updateItem.mutate(updatePayload, {
      onSuccess: () => toast.success(`Collection status updated to ${STATUS_LABELS[newStatus]?.label || newStatus}`),
      onError: e => toast.error((e as Error).message),
    });
  };

  const handleLentSubmit = () => {
    if (!borrowerName.trim()) {
      toast.error("Please enter a borrower name");
      return;
    }

    updateItem.mutate(
      {
        collection_status: "lent",
        lent_to_name: borrowerName.trim(),
        lent_to_user_id: borrowerId || null,
      },
      {
        onSuccess: () => {
          toast.success(`Item marked as lent to ${borrowerName}`);
          setIsLentDialogOpen(false);
        },
        onError: e => toast.error((e as Error).message),
      }
    );
  };

  const handleToggleVisibility = () => {
    const newHidden = !item.is_hidden;
    updateItem.mutate(
      { is_hidden: newHidden },
      {
        onSuccess: () => toast.success(`Item is now ${newHidden ? "hidden" : "public"}`),
        onError: e => toast.error((e as Error).message),
      }
    );
  };

  /**
   * Handles generating and opening the QR code for the item.
   * TODO: Implementation for QR code printing is not ready yet.
   */
  /*
  const handleQrCode = async () => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api";
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
  */

  return (
    <div className="flex flex-col items-center gap-5">
      {/* Book/Audio cover */}
      <div className="-mt-28 w-full max-w-[220px]">
        <div
          className={`relative ${aspectClass} w-full overflow-hidden rounded-lg shadow-xl ring-4 ring-card bg-secondary`}
        >
          {coverUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={coverUrl} alt={item.title ?? "Cover"} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center">
              <MediaIcon className="h-12 w-12 text-muted-foreground/30" />
            </div>
          )}
        </div>
      </div>

      {/* Status badges */}
      <div className="flex flex-wrap justify-center gap-2 px-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold ring-1 transition-all ${collectionStatusInfo.class}`}
          title="Collection Availability"
        >
          <span className="h-1 w-1 rounded-full bg-current opacity-70" />
          {collectionStatusInfo.label?.toUpperCase() || "UNKNOWN"}
        </span>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold ring-1 transition-all ${progressStatusInfo.class}`}
          title="Personal Progress"
        >
          <span className="h-1 w-1 rounded-full bg-current opacity-70" />
          {progressStatusInfo.label?.toUpperCase() || "UNKNOWN"}
        </span>
        {item.is_hidden && (
          <span
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold ring-1 transition-all bg-zinc-900 text-zinc-100 ring-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:ring-zinc-300"
            title="Item is hidden from your public profile"
          >
            <EyeOff className="h-3 w-3" />
            HIDDEN
          </span>
        )}
      </div>

      {/* Lending info */}
      {(item.collection_status === "lent" || item.is_borrowed) && (
        <div className="flex flex-col items-center gap-1">
          {item.collection_status === "lent" && item.lent_to_name && (
            <p className="text-center text-[10px] font-bold uppercase tracking-wider text-orange-600">
              Lent to: <span className="text-foreground">{item.lent_to_name}</span>
            </p>
          )}
          {item.is_borrowed && item.owner_name && (
            <p className="text-center text-[10px] font-bold uppercase tracking-wider text-blue-600">
              Borrowed from: <span className="text-foreground">{item.owner_name}</span>
            </p>
          )}
        </div>
      )}

      {/* ISBN */}
      {item.isbn && <p className="text-center text-xs text-muted-foreground">ISBN: {item.isbn}</p>}

      {/* Action buttons & Status Selects */}
      <div className="flex w-full flex-col gap-3 px-1">
        {canModifyItem ? (
          <div className="flex flex-col gap-2.5">
            {/* Collection Select */}
            <div className="flex flex-col gap-1">
              <span className="px-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
                Availability & Condition
              </span>
              <select
                aria-label="Collection status"
                value={item.collection_status}
                onChange={handleCollectionStatusChange}
                disabled={updateItem.isPending}
                className="w-full rounded-lg bg-secondary/80 px-3 py-2 text-sm font-medium text-foreground outline-none ring-1 ring-border transition-all hover:bg-secondary focus:ring-primary/50 disabled:opacity-60 cursor-pointer appearance-none"
              >
                <optgroup label="Availability & Condition">
                  {["available", "lent", "damaged", "lost"].map(key => (
                    <option key={key} value={key} className="bg-card py-2">
                      {STATUS_LABELS[key]?.label || key}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Acquisition">
                  {["wish_list", "ordered"].map(key => (
                    <option key={key} value={key} className="bg-card py-2">
                      {STATUS_LABELS[key]?.label || key}
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>

            {/* Progress Select */}
            <div className="flex flex-col gap-1">
              <span className="px-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
                {isBook ? "Reading" : isAudio ? "Listening" : isVideo ? "Watching" : isGame ? "Gaming" : "Item"}{" "}
                Progress
              </span>
              <select
                aria-label="Item status"
                value={item.status}
                onChange={handleStatusChange}
                disabled={updateItem.isPending}
                className="w-full rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground outline-none shadow-sm transition-all hover:opacity-90 focus:ring-2 focus:ring-primary/20 disabled:opacity-60 cursor-pointer appearance-none text-center"
              >
                {isBook && (
                  <optgroup label="Reading Progress">
                    {["unread", "reading", "read", "want_to_read"].map(key => (
                      <option key={key} value={key} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[key]?.label || key}
                      </option>
                    ))}
                  </optgroup>
                )}
                {isAudio && (
                  <optgroup label="Listening Progress">
                    {["want_to_listen", "listening", "listened"].map(key => (
                      <option key={key} value={key} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[key]?.label || key}
                      </option>
                    ))}
                  </optgroup>
                )}
                {isVideo && (
                  <optgroup label="Watching Progress">
                    {["want_to_watch", "watching", "watched"].map(key => (
                      <option key={key} value={key} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[key]?.label || key}
                      </option>
                    ))}
                  </optgroup>
                )}
                {isGame && (
                  <optgroup label="Gaming Progress">
                    {["want_to_play", "playing", "played"].map(s => (
                      <option key={s} value={s} className="text-foreground bg-card normal-case py-2">
                        {STATUS_LABELS[s]?.label || s}
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="w-full rounded-lg bg-secondary/50 px-4 py-2 text-xs font-semibold text-center text-secondary-foreground border border-border/50">
              {collectionStatusInfo.label || "Unknown"}
            </div>
            <div className="w-full rounded-lg bg-primary/10 px-4 py-2 text-xs font-semibold text-center text-primary border border-primary/20">
              {progressStatusInfo.label || "Unknown"}
            </div>
          </div>
        )}

        {canModifyItem && onEdit && (
          <button
            onClick={onEdit}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-secondary px-4 py-2.5 text-sm font-semibold text-secondary-foreground transition-colors hover:bg-secondary/80"
          >
            <Pencil className="h-4 w-4" />
            Edit Metadata
          </button>
        )}

        {canModifyItem && (
          <button
            onClick={handleToggleVisibility}
            disabled={updateItem.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-muted disabled:opacity-60"
          >
            {item.is_hidden ? (
              <>
                <Eye className="h-4 w-4" />
                Make Public
              </>
            ) : (
              <>
                <EyeOff className="h-4 w-4" />
                Hide from Public
              </>
            )}
          </button>
        )}
        {/* Print QR Code - Hidden until implementation is ready */}
        {/*
        <button
          onClick={handleQrCode}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-muted"
        >
          <QrCode className="h-4 w-4" />
          Print QR Code
        </button>
        */}

        {canModifyItem && hasUploadPermission && (
          <CameraCapture
            manifestation_id={item.manifestation_id}
            format={format as MediaFormat}
            onUploadComplete={handleUploadComplete}
            label={item.cover_url ? "Replace Cover" : "Contribute Cover"}
            icon={<ImagePlus className="h-3.5 w-3.5" />}
            confirmTitle={item.cover_url ? "Replace Existing Cover?" : undefined}
            confirmMessage={
              item.cover_url
                ? "This manifestation already has a cover. Are you sure you want to replace it with your own image?"
                : undefined
            }
            source="scanner_camera"
            className="[&>button]:flex [&>button]:items-center [&>button]:gap-2 [&>button]:text-xs [&>button]:font-medium [&>button]:text-muted-foreground [&>button]:transition-colors [&>button]:hover:text-foreground [&>button]:bg-transparent [&>button]:border-none [&>button]:p-0"
          />
        )}

        {canModifyItem && hasEditPermission && (
          <MultiImageUploader
            manifestationId={item.manifestation_id}
            currentItemFormat={format}
            onUploadComplete={handleUploadComplete}
          />
        )}

        {canModifyItem && <TaxonomyEditor item={item} />}
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

      <Dialog open={isLentDialogOpen} onOpenChange={setIsLentDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Lent Out Item</DialogTitle>
            <DialogDescription>
              Who are you lending this item to? This helps you keep track of your physical collection.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label
              htmlFor="borrower-name"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Borrower Name
            </label>
            <div className="relative">
              <input
                id="borrower-name"
                className="mt-2 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Search user or enter name..."
                value={borrowerName}
                onChange={e => {
                  setBorrowerName(e.target.value);
                  setBorrowerId(undefined); // Reset ID if user types something new
                }}
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setTimeout(() => setSearchFocused(false), 200)}
                onKeyDown={e => e.key === "Enter" && handleLentSubmit()}
                autoFocus
                autoComplete="off"
              />
              {searchFocused && borrowerName.trim().length >= 2 && (
                <div className="absolute z-50 w-full mt-1 bg-popover text-popover-foreground rounded-md border shadow-md outline-none">
                  <ul className="max-h-48 overflow-y-auto py-1">
                    {isSearching ? (
                      <li className="px-3 py-2 text-sm text-muted-foreground">Searching...</li>
                    ) : searchResults && searchResults.length > 0 ? (
                      searchResults.map(user => (
                        <li
                          key={user.id}
                          className="px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground cursor-pointer flex items-center justify-between"
                          onMouseDown={e => {
                            e.preventDefault(); // Prevent blur
                            setBorrowerName(user.display_name || user.email);
                            setBorrowerId(user.id);
                            setSearchFocused(false);
                          }}
                        >
                          <span className="font-medium">{user.display_name || user.email}</span>
                          <span className="text-xs text-muted-foreground ml-2 truncate max-w-[120px]">
                            {user.email}
                          </span>
                        </li>
                      ))
                    ) : (
                      <li className="px-3 py-2 text-sm text-muted-foreground">
                        No users found. Will save as plain name.
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsLentDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleLentSubmit} disabled={updateItem.isPending}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
