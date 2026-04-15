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

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Trash2,
  RefreshCw,
  CloudDownload,
  Pencil,
  Image as ImageIcon,
  BookOpen,
  Music,
  Video,
  Gamepad2,
} from "lucide-react";
import { toast } from "sonner";

import { useDeleteItem, useRegenerateCover, useUpdateItem, queryKeys } from "@/lib/api/hooks";
import { useProfile } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";
import { PermissionName } from "@/lib/permissions";
import { isAudioMedia } from "@/lib/utils";
import type { Item } from "@/types/frbr";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useQueryClient } from "@tanstack/react-query";

/**
 * Item actions component.
 *
 * @param root0 - The props object
 * @param root0.item - The item
 * @returns {JSX.Element | null} The component or null if no profile
 */
export function ItemActions({ item }: { item: Item }) {
  const router = useRouter();
  const regenerateCover = useRegenerateCover();
  const updateItem = useUpdateItem(item.id);
  const deleteItem = useDeleteItem();
  const qc = useQueryClient();

  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [regenerateConfirmOpen, setRegenerateConfirmOpen] = useState(false);
  const [isRequesting, setIsRequesting] = useState(false);
  const [isRefetching, setIsRefetching] = useState(false);

  const isPending = item.cover_status === "pending" || item.meta?.cover_status === "pending";

  const { data: profile } = useProfile();

  // Poll server state every 3s if we are waiting for a cover generation to fix infinite spinner UX
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (isPending) {
      interval = setInterval(() => {
        qc.invalidateQueries({ queryKey: queryKeys.item(item.id) });
      }, 3000);
    }
    return () => {
      if (interval !== undefined) {
        clearInterval(interval);
      }
    };
  }, [isPending, item.id, qc]);

  if (!profile) return null;

  const hasPermission = (perm: PermissionName): boolean => Boolean(profile.permissions?.includes(perm));

  const handleConfirmDelete = () => {
    deleteItem.mutate(item.id, {
      onSuccess: () => {
        toast.success("Item removed from library");
        router.push("/collection");
      },
      onError: e => toast.error(e instanceof Error ? e.message : String(e)),
    });
  };

  const handleRegenerateClick = () => {
    const hasCover = !!(item.cover_url || item.manifestation_meta?.["cover_url"] || item.meta?.["cover_url"]);
    if (hasCover) {
      setRegenerateConfirmOpen(true);
    } else {
      handleRegenerate();
    }
  };

  const handleRegenerate = async () => {
    if (!item.manifestation_id) return;
    setIsRequesting(true);
    setRegenerateConfirmOpen(false);
    try {
      await regenerateCover.mutateAsync(item.manifestation_id);
      qc.setQueryData(queryKeys.item(item.id), (prev: Item | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          cover_status: "pending",
        };
      });
      toast.success("Cover regeneration started");
    } catch (error) {
      console.error("Failed to schedule regeneration:", error);
      toast.error("Failed to schedule regeneration");
    } finally {
      setIsRequesting(false);
    }
  };

  const handleRefetch = async () => {
    if (!item.manifestation_id) return;
    setIsRefetching(true);
    try {
      await apiClient.post(`/manifestations/${item.manifestation_id}/refetch-metadata`);
      toast.success("Metadata refetched successfully. Reloading...");
      window.location.reload();
    } catch {
      toast.error("Failed to refetch metadata");
    } finally {
      setIsRefetching(false);
    }
  };

  const handleStatusUpdate = (status: Item["status"]) => {
    updateItem.mutate(
      { status },
      {
        onSuccess: () => toast.success(`Status updated to ${status.replace(/_/g, " ")}`),
        onError: e => toast.error(e instanceof Error ? e.message : String(e)),
      }
    );
  };

  // Media type checks
  const format =
    (item.manifestation_meta?.["format"] as string | undefined) ??
    (item.meta?.["format"] as string | undefined) ??
    "book";
  const isAudio = isAudioMedia(format);
  const isVideo = ["dvd", "bluray", "video", "moving image"].includes(format?.toLowerCase() || "");
  const isGame = ["boardgame", "board_game", "three-dimensional object"].includes(format?.toLowerCase() || "");
  const isBook = !isAudio && !isVideo && !isGame;

  return (
    <div className="mt-8 flex flex-col gap-6 rounded-2xl border bg-card/50 p-6 shadow-sm border-border/40">
      <div className="flex flex-wrap items-center gap-4">
        {/* Polymorphic quick actions */}
        {isBook && item.status !== "read" && (
          <button
            onClick={() => handleStatusUpdate(item.status === "reading" ? "read" : "reading")}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95"
          >
            <BookOpen className="h-3.5 w-3.5" />
            {item.status === "reading" ? "Mark as Read" : "Log Reading Progress"}
          </button>
        )}

        {isAudio && item.status !== "listened" && (
          <button
            onClick={() => handleStatusUpdate(item.status === "listening" ? "listened" : "listening")}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95"
          >
            <Music className="h-3.5 w-3.5" />
            {item.status === "listening" ? "Mark as Listened" : "Now Listening"}
          </button>
        )}

        {isVideo && item.status !== "watched" && (
          <button
            onClick={() => handleStatusUpdate(item.status === "watching" ? "watched" : "watching")}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95"
          >
            <Video className="h-3.5 w-3.5" />
            {item.status === "watching" ? "Mark as Watched" : "Now Watching"}
          </button>
        )}

        {isGame && (
          <button
            onClick={() => handleStatusUpdate("played")}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95"
          >
            <Gamepad2 className="h-3.5 w-3.5" />
            Log Play
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-6 border-t border-border/40 pt-4">
        {hasPermission(PermissionName.REFETCH_METADATA) && (
          <button
            onClick={handleRefetch}
            disabled={isRefetching}
            className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
          >
            <CloudDownload className={`h-3.5 w-3.5 ${isRefetching ? "animate-bounce" : ""}`} />
            {isRefetching ? "Fetching..." : "Refetch Metadata"}
          </button>
        )}

        {hasPermission(PermissionName.REGENERATE_COVER) && (
          <button
            onClick={handleRegenerateClick}
            disabled={isPending || isRequesting}
            className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isPending ? "animate-spin" : ""}`} />
            {isPending ? "Generating..." : "Regenerate Cover"}
          </button>
        )}

        {hasPermission(PermissionName.READ_METADATA) && item.manifestation_id && (
          <button
            onClick={() => router.push(`/admin/content?tab=metadata&manifestationId=${item.manifestation_id}`)}
            className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
          >
            <Pencil className="h-3.5 w-3.5" />
            Edit FRBR
          </button>
        )}

        {hasPermission(PermissionName.EDIT_COVER) && item.manifestation_id && (
          <button
            onClick={() => router.push(`/admin/content?tab=cover-art&manifestationId=${item.manifestation_id}`)}
            className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
          >
            <ImageIcon className="h-3.5 w-3.5" />
            Edit Cover Art
          </button>
        )}

        {hasPermission(PermissionName.DELETE_ITEM) && (
          <button
            onClick={() => setDeleteConfirmOpen(true)}
            disabled={deleteItem.isPending}
            className="flex items-center gap-2 text-xs font-medium text-destructive/70 transition-colors hover:text-destructive disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Remove from library
          </button>
        )}

        <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Remove from library?</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently remove this item from your library. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={deleteItem.isPending}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleConfirmDelete}
                disabled={deleteItem.isPending}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleteItem.isPending ? "Removing…" : "Remove"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <AlertDialog open={regenerateConfirmOpen} onOpenChange={setRegenerateConfirmOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Regenerate Cover?</AlertDialogTitle>
              <AlertDialogDescription>
                This item already has a cover image. Regenerating it will overwrite the existing cover.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleRegenerate}>Regenerate</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
