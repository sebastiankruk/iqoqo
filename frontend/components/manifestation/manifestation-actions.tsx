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
  ImagePlus,
  Pencil,
  Image as ImageIcon,
  ChevronDown,
  ChevronUp,
  ImageDown,
} from "lucide-react";
import { toast } from "sonner";
import { CameraCapture } from "@/components/scanner/camera-capture";

import { useProfile, useRegenerateCover, queryKeys } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";
import { useQueryClient } from "@tanstack/react-query";
import { PermissionName } from "@/lib/permissions";
import type { CatalogEntry, Manifestation } from "@/types/frbr";
import { Button } from "@/components/ui/button";
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
  const [isRefetchingCover, setIsRefetchingCover] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [activeCoverAction, setActiveCoverAction] = useState<"regenerate" | "refetch" | null>(null);

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
    } else {
      setActiveCoverAction(null);
    }
    return () => {
      if (interval !== undefined) {
        clearInterval(interval);
      }
    };
  }, [isProcessing, manifestation.id, qc]);

  if (!profile) return null;

  const hasPermission = (perm: PermissionName): boolean => Boolean(profile.permissions?.includes(perm));

  const showAdminActions =
    hasPermission(PermissionName.REFETCH_METADATA) ||
    hasPermission(PermissionName.REFETCH_COVER) ||
    hasPermission(PermissionName.REGENERATE_COVER) ||
    (hasPermission(PermissionName.READ_METADATA) && !!manifestation.id) ||
    (hasPermission(PermissionName.EDIT_COVER) && !!manifestation.id) ||
    hasPermission(PermissionName.UPLOAD_COVER) ||
    hasPermission(PermissionName.DELETE_MANIFESTATION);

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
    setActiveCoverAction("regenerate");
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

  const handleRefetchCover = async () => {
    if (!manifestation.id) return;
    setIsRefetchingCover(true);
    setActiveCoverAction("refetch");
    try {
      await apiClient.post(`/manifestations/${manifestation.id}/refetch-cover`);
      qc.setQueryData(queryKeys.manifestation(manifestation.id), (prev: Manifestation | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          meta: { ...(prev.meta || {}), cover_status: "pending" },
        };
      });
      toast.success("Cover refetch started");
    } catch {
      toast.error("Failed to refetch cover");
    } finally {
      setIsRefetchingCover(false);
    }
  };

  return (
    <>
      {showAdminActions && (
        <div className="border-t border-border pt-4 w-full">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsPanelOpen(!isPanelOpen)}
            className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer px-2"
          >
            {isPanelOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            <span>Admin Actions</span>
          </Button>

          {isPanelOpen && (
            <div className="mt-4 flex flex-col sm:flex-row sm:flex-wrap gap-3 animate-in fade-in slide-in-from-top-2 duration-200">
              {hasPermission(PermissionName.REFETCH_METADATA) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRefetch}
                  disabled={isRefetching}
                  className="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2"
                >
                  <CloudDownload className={`h-3.5 w-3.5 ${isRefetching ? "animate-bounce" : ""}`} />
                  {isRefetching ? "Fetching..." : "Refetch Metadata"}
                </Button>
              )}

              {hasPermission(PermissionName.READ_METADATA) && manifestation.id && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(`/admin/content?tab=metadata&manifestationId=${manifestation.id}`)}
                  className="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2"
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Edit FRBR
                </Button>
              )}

              {hasPermission(PermissionName.REFETCH_COVER) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRefetchCover}
                  disabled={isPending || isRefetchingCover}
                  className="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2"
                >
                  <ImageDown
                    className={`h-3.5 w-3.5 ${isPending && activeCoverAction === "refetch" ? "animate-bounce" : ""}`}
                  />
                  {isPending && activeCoverAction === "refetch" ? "Refetching..." : "Refetch Cover"}
                </Button>
              )}

              {hasPermission(PermissionName.REGENERATE_COVER) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRegenerateClick}
                  disabled={isPending || isRequesting}
                  className="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2"
                >
                  <RefreshCw
                    className={`h-3.5 w-3.5 ${isPending && (activeCoverAction === "regenerate" || !activeCoverAction) ? "animate-spin" : ""}`}
                  />
                  {isPending && (activeCoverAction === "regenerate" || !activeCoverAction)
                    ? "Generating..."
                    : "Regenerate Cover"}
                </Button>
              )}

              {hasPermission(PermissionName.UPLOAD_COVER) && (
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
                  variant="outline"
                  buttonClassName="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2 h-8 px-3 text-xs"
                />
              )}

              {hasPermission(PermissionName.EDIT_COVER) && manifestation.id && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(`/admin/content?tab=cover-art&manifestationId=${manifestation.id}`)}
                  className="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2"
                >
                  <ImageIcon className="h-3.5 w-3.5" />
                  Edit Cover Art
                </Button>
              )}

              {hasPermission(PermissionName.DELETE_MANIFESTATION) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setDeleteConfirmOpen(true)}
                  disabled={isDeleting}
                  className="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2 text-destructive border-destructive/20 hover:bg-destructive/10 hover:text-destructive"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete manifestation
                </Button>
              )}
            </div>
          )}
        </div>
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
    </>
  );
}
