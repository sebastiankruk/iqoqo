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
import { Trash2, RefreshCw, CloudDownload, Pencil } from "lucide-react";
import { toast } from "sonner";

import { useDeleteItem, useRegenerateCover, queryKeys } from "@/lib/api/hooks";
import { useProfile } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";
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

  const hasPermission = (perm: string): boolean => Boolean(profile.permissions?.includes(perm));

  const handleConfirmDelete = () => {
    deleteItem.mutate(item.id, {
      onSuccess: () => {
        toast.success("Item removed from library");
        router.push("/collection");
      },
      onError: e => toast.error(e.message),
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

  return (
    <div className="mt-4 border-t border-border pt-4 flex items-center gap-6">
      {hasPermission("refetch:metadata") && (
        <button
          onClick={handleRefetch}
          disabled={isRefetching}
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          <CloudDownload className={`h-3.5 w-3.5 ${isRefetching ? "animate-bounce" : ""}`} />
          {isRefetching ? "Fetching..." : "Refetch Metadata"}
        </button>
      )}

      {hasPermission("regenerate:cover") && (
        <button
          onClick={handleRegenerateClick}
          disabled={isPending || isRequesting}
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isPending ? "animate-spin" : ""}`} />
          {isPending ? "Generating..." : "Regenerate Cover"}
        </button>
      )}

      {hasPermission("read:content") && item.manifestation_id && (
        <button
          onClick={() => router.push(`/admin/content?tab=content&manifestationId=${item.manifestation_id}`)}
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          <Pencil className="h-3.5 w-3.5" />
          Edit FRBR
        </button>
      )}

      {hasPermission("delete:item") && (
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
  );
}
