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
import { Trash2, RefreshCw, CloudDownload, ImagePlus, Pencil } from "lucide-react";
import { toast } from "sonner";
import { CameraCapture } from "@/components/scanner/camera-capture";

import { useProfile, useRegenerateCover, queryKeys } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";
import { useQueryClient } from "@tanstack/react-query";
import type { CatalogEntry, Manifestation } from "@/types/frbr";
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

/**
 * Renders a set of action buttons for a manifestation or catalog entry.
 * Includes functionality for refetching metadata, regenerating covers, contributing covers, and deleting the manifestation.
 *
 * @param {Object} props - The component props.
 * @param {Manifestation | CatalogEntry} props.manifestation - The manifestation or catalog entry to provide actions for.
 * @returns {JSX.Element | null} The rendered action buttons or null if the user profile is not loaded.
 */
export function ManifestationActions({ manifestation }: { manifestation: Manifestation | CatalogEntry }) {
  const router = useRouter();
  const regenerateCover = useRegenerateCover();
  const qc = useQueryClient();

  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [regenerateConfirmOpen, setRegenerateConfirmOpen] = useState(false);
  const [isRequesting, setIsRequesting] = useState(false);
  const [isRefetching, setIsRefetching] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const isPending = manifestation.meta?.cover_status === "pending";

  const { data: profile } = useProfile();

  // Poll server state every 3s while cover is pending OR processing
  const isProcessing = isPending || manifestation.meta?.cover_status === "processing";
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (isProcessing && manifestation.id) {
      interval = setInterval(() => {
        qc.invalidateQueries({ queryKey: queryKeys.manifestation(manifestation.id!) });
      }, 3000);
    }
    return () => {
      if (interval !== undefined) {
        clearInterval(interval);
      }
    };
  }, [isProcessing, manifestation.id, qc]);

  if (!profile) return null;

  const hasPermission = (perm: string): boolean => Boolean(profile.permissions?.includes(perm));

  /**
   * Handles the confirmation of manifestation deletion.
   *
   * @returns {Promise<void>} A promise that resolves when the manifestation is deleted.
   */
  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    try {
      await apiClient.delete(`/manifestations/${manifestation.id}`);
      toast.success("Manifestation deleted");
      router.push("/collection");
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to delete manifestation";
      toast.error(msg);
    } finally {
      setIsDeleting(false);
      setDeleteConfirmOpen(false);
    }
  };

  /**
   * Handles the click event for regenerating the cover.
   * If a cover already exists, it opens a confirmation dialog.
   * Otherwise, it directly calls the regeneration function.
   */
  const handleRegenerateClick = () => {
    const hasCover = !!(manifestation.cover_url || manifestation.meta?.["cover_url"]);
    if (hasCover) {
      setRegenerateConfirmOpen(true);
    } else {
      handleRegenerate();
    }
  };

  /**
   * Initiates the cover regeneration process for the manifestation.
   *
   * @returns {Promise<void>} A promise that resolves when the regeneration is scheduled.
   */
  const handleRegenerate = async () => {
    if (!manifestation.id) return;
    setIsRequesting(true);
    setRegenerateConfirmOpen(false);
    try {
      await regenerateCover.mutateAsync(manifestation.id);
      qc.setQueryData(queryKeys.manifestation(manifestation.id), (prev: Manifestation | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          meta: { ...(prev.meta || {}), cover_status: "pending" },
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

  /**
   * Handles refetching metadata for the manifestation.
   *
   * @returns {Promise<void>} A promise that resolves when the metadata is refetched.
   */
  const handleRefetch = async () => {
    if (!manifestation.id) return;
    setIsRefetching(true);
    try {
      await apiClient.post(`/manifestations/${manifestation.id}/refetch-metadata`);
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

      {hasPermission("read:content") && manifestation.id && (
        <button
          onClick={() => router.push(`/admin/content?tab=content&manifestationId=${manifestation.id}`)}
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          <Pencil className="h-3.5 w-3.5" />
          Edit FRBR
        </button>
      )}

      {hasPermission("upload:cover") && (
        <CameraCapture
          manifestation_id={manifestation.id}
          onUploadComplete={() => {
            toast.success("Cover uploaded and processing started!");
            // Optimistically mark as processing so the polling loop kicks in automatically
            qc.setQueryData(queryKeys.manifestation(manifestation.id!), (prev: Manifestation | undefined) => {
              if (!prev) return prev;
              return { ...prev, meta: { ...(prev.meta || {}), cover_status: "processing" } };
            });
          }}
          label={manifestation.cover_url ? "Replace Cover" : "Contribute Cover"}
          icon={<ImagePlus className="h-3.5 w-3.5" />}
          confirmTitle={manifestation.cover_url ? "Replace Existing Cover?" : undefined}
          confirmMessage={
            manifestation.cover_url
              ? "This manifestation already has a cover. Are you sure you want to replace it with your own image?"
              : undefined
          }
          inline
          variant="ghost"
          className="p-0 m-0 w-auto"
          buttonClassName="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground bg-transparent border-none p-0 h-auto hover:bg-transparent"
        />
      )}

      {hasPermission("delete:manifestation") && (
        <button
          onClick={() => setDeleteConfirmOpen(true)}
          disabled={isDeleting}
          className="flex items-center gap-2 text-xs font-medium text-destructive/70 transition-colors hover:text-destructive disabled:opacity-50"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Delete manifestation
        </button>
      )}

      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete manifestation?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete this manifestation and all associated items across the system. This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={regenerateConfirmOpen} onOpenChange={setRegenerateConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Regenerate Cover?</AlertDialogTitle>
            <AlertDialogDescription>
              This manifestation already has a cover image. Regenerating it will overwrite the existing cover.
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
