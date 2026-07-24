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
import Link from "next/link";
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
  ChevronDown,
  ChevronUp,
  ImagePlus,
  ImageDown,
  Clock,
} from "lucide-react";
import { toast } from "sonner";

import { useDeleteItem, useRegenerateCover, useUpdateItem, queryKeys } from "@/lib/api/hooks";
import { useProfile } from "@/lib/api/hooks";
import { useMyEscalations } from "@/lib/api/escalations";
import { apiClient } from "@/lib/api/client";
import { PermissionName } from "@/lib/permissions";
import { isAudioMedia } from "@/lib/utils";
import type { Item } from "@/types/frbr";
import { EscalationTrigger } from "@/components/escalation/escalation-trigger";
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
import { Button } from "@/components/ui/button";
import { CameraCapture } from "@/components/scanner/camera-capture";
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
  const [isRefetchingCover, setIsRefetchingCover] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isHierarchyOpen, setIsHierarchyOpen] = useState(false);
  const [isRequestsOpen, setIsRequestsOpen] = useState(false);
  const [activeCoverAction, setActiveCoverAction] = useState<"regenerate" | "refetch" | null>(null);

  const isPending = item.cover_status === "pending" || item.meta?.cover_status === "pending";

  const { data: profile } = useProfile();

  const hasEscalateRequestForHook = Boolean(profile?.permissions?.includes(PermissionName.ESCALATE_REQUEST));
  const hasWriteMetadataForHook = Boolean(profile?.permissions?.includes(PermissionName.WRITE_METADATA));
  const { data: myEscalations } = useMyEscalations(hasEscalateRequestForHook && !hasWriteMetadataForHook);

  // Filter escalations for this item
  const itemEscalations = myEscalations?.filter(e => e.item_id === item.id) ?? [];
  const pendingEscalation = itemEscalations.find(e => e.status === "pending");

  // Poll server state every 3s if we are waiting for a cover generation to fix infinite spinner UX
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (isPending) {
      interval = setInterval(() => {
        qc.invalidateQueries({ queryKey: queryKeys.item(item.id) });
      }, 3000);
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setActiveCoverAction(null);
    }
    return () => {
      if (interval !== undefined) {
        clearInterval(interval);
      }
    };
  }, [isPending, item.id, qc]);

  if (!profile) return null;

  const hasPermission = (perm: PermissionName): boolean => Boolean(profile.permissions?.includes(perm));

  const showAdminActions =
    hasPermission(PermissionName.REFETCH_METADATA) ||
    (hasPermission(PermissionName.WRITE_METADATA) && !!item.manifestation_id) ||
    hasPermission(PermissionName.REFETCH_COVER) ||
    hasPermission(PermissionName.REGENERATE_COVER) ||
    hasPermission(PermissionName.UPLOAD_COVER) ||
    (hasPermission(PermissionName.EDIT_COVER) && !!item.manifestation_id) ||
    hasPermission(PermissionName.DELETE_ITEM);

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
    setActiveCoverAction("regenerate");
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

  const handleRefetchCover = async () => {
    if (!item.manifestation_id) return;
    setIsRefetchingCover(true);
    setActiveCoverAction("refetch");
    try {
      await apiClient.post(`/manifestations/${item.manifestation_id}/refetch-cover`);
      qc.setQueryData(queryKeys.item(item.id), (prev: Item | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          cover_status: "pending",
        };
      });
      toast.success("Cover refetch started");
    } catch {
      toast.error("Failed to refetch cover");
    } finally {
      setIsRefetchingCover(false);
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
      <div className="flex flex-wrap items-center gap-4 w-full">
        {/* Polymorphic quick actions */}
        {item.is_owner && isBook && item.status !== "read" && (
          <button
            onClick={() => handleStatusUpdate(item.status === "reading" ? "read" : "reading")}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95 w-full sm:w-auto"
          >
            <BookOpen className="h-3.5 w-3.5" />
            {item.status === "reading" ? "Mark as Read" : "Log Reading Progress"}
          </button>
        )}

        {item.is_owner && isAudio && item.status !== "listened" && (
          <button
            onClick={() => handleStatusUpdate(item.status === "listening" ? "listened" : "listening")}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95 w-full sm:w-auto"
          >
            <Music className="h-3.5 w-3.5" />
            {item.status === "listening" ? "Mark as Listened" : "Now Listening"}
          </button>
        )}

        {item.is_owner && isVideo && item.status !== "watched" && (
          <button
            onClick={() => handleStatusUpdate("watched")}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95 w-full sm:w-auto"
          >
            <Video className="h-3.5 w-3.5" />
            Mark as Watched
          </button>
        )}

        {item.is_owner && isGame && (
          <button
            onClick={() => handleStatusUpdate("played")}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 active:scale-95 w-full sm:w-auto"
          >
            <Gamepad2 className="h-3.5 w-3.5" />
            Log Play
          </button>
        )}
      </div>

      <div className="border-t border-border/40 pt-4 w-full flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              const nextVal = !isHierarchyOpen;
              setIsHierarchyOpen(nextVal);
              if (nextVal) {
                setIsPanelOpen(false);
              }
            }}
            className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer px-2"
          >
            {isHierarchyOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            <span>FRBR Hierarchy</span>
          </Button>

          {showAdminActions && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                const nextVal = !isPanelOpen;
                setIsPanelOpen(nextVal);
                if (nextVal) {
                  setIsHierarchyOpen(false);
                }
              }}
              className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer px-2"
            >
              {isPanelOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              <span>Admin Actions</span>
            </Button>
          )}
        </div>

        {isHierarchyOpen && (
          <dl className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4 animate-in fade-in slide-in-from-top-2 duration-200">
            {item.work && (
              <div className="flex flex-col gap-0.5">
                <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Work ID</dt>
                <dd className="text-sm font-mono text-foreground">#{item.work.id}</dd>
              </div>
            )}
            {item.expression && (
              <div className="flex flex-col gap-0.5">
                <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Expression ID
                </dt>
                <dd className="text-sm font-mono text-foreground">#{item.expression.id}</dd>
              </div>
            )}
            <div className="flex flex-col gap-0.5">
              <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Manifestation ID
              </dt>
              <dd className="text-sm font-mono text-foreground">
                <Link href={`/manifestation/${item.manifestation_id}`} className="hover:underline">
                  #{item.manifestation_id}
                </Link>
              </dd>
            </div>
            <div className="flex flex-col gap-0.5">
              <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Item ID</dt>
              <dd className="text-sm font-mono text-foreground">#{item.id}</dd>
            </div>
          </dl>
        )}

        {showAdminActions && isPanelOpen && (
          <div className="flex flex-col sm:flex-row sm:flex-wrap gap-3 animate-in fade-in slide-in-from-top-2 duration-200">
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

            {hasPermission(PermissionName.WRITE_METADATA) && item.manifestation_id && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push(`/admin/content?tab=metadata&manifestationId=${item.manifestation_id}`)}
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

            {hasPermission(PermissionName.UPLOAD_COVER) && item.manifestation_id && (
              <CameraCapture
                manifestation_id={item.manifestation_id}
                onUploadComplete={() => {
                  toast.success("Cover uploaded and processing started!");
                  qc.setQueryData(queryKeys.item(item.id), (prev: Item | undefined) => {
                    if (!prev) return prev;
                    return {
                      ...prev,
                      cover_status: "processing",
                    };
                  });
                }}
                label={
                  item.cover_url || item.manifestation_meta?.["cover_url"] || item.meta?.["cover_url"]
                    ? "Replace Cover"
                    : "Contribute Cover"
                }
                icon={<ImagePlus className="h-3.5 w-3.5" />}
                confirmTitle={
                  item.cover_url || item.manifestation_meta?.["cover_url"] || item.meta?.["cover_url"]
                    ? "Replace Existing Cover?"
                    : undefined
                }
                confirmMessage={
                  item.cover_url || item.manifestation_meta?.["cover_url"] || item.meta?.["cover_url"]
                    ? "This item already has a cover. Are you sure you want to replace it with your own image?"
                    : undefined
                }
                inline
                variant="outline"
                buttonClassName="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2 h-8 px-3 text-xs"
              />
            )}

            {hasPermission(PermissionName.EDIT_COVER) && item.manifestation_id && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push(`/admin/content?tab=cover-art&manifestationId=${item.manifestation_id}`)}
                className="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2"
              >
                <ImageIcon className="h-3.5 w-3.5" />
                Edit Cover Art
              </Button>
            )}

            {hasPermission(PermissionName.DELETE_ITEM) && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteConfirmOpen(true)}
                disabled={deleteItem.isPending}
                className="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2 text-destructive border-destructive/20 hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Remove from library
              </Button>
            )}
          </div>
        )}

        {hasEscalateRequestForHook && !hasWriteMetadataForHook && (
          <div className="border-t border-border/40 pt-4 w-full">
            {/* Pending status card outside the accordion */}
            {pendingEscalation && (
              <div
                data-testid="escalation-status-card"
                className="rounded-lg border border-border bg-card p-3 text-xs shadow-xs space-y-1.5 mb-3"
              >
                <div className="flex items-center justify-between font-medium">
                  <span className="flex items-center gap-1.5 capitalize">
                    <Clock className="h-4 w-4 text-amber-500 animate-pulse" />
                    Help Request: {pendingEscalation.status}
                  </span>
                  <span className="text-muted-foreground uppercase text-[10px] tracking-wider font-mono">
                    {pendingEscalation.field_name}
                  </span>
                </div>
                <div className="text-muted-foreground">
                  Suggested: <span className="font-mono text-foreground">{pendingEscalation.suggested_value}</span>
                </div>
                {pendingEscalation.resolution_note && (
                  <div className="rounded bg-muted/50 p-1.5 text-[11px] italic text-muted-foreground border-l-2 border-primary/50">
                    Custodian note: &ldquo;{pendingEscalation.resolution_note}&rdquo;
                  </div>
                )}
              </div>
            )}

            {/* Accordion header */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsRequestsOpen(!isRequestsOpen)}
              className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer px-2"
            >
              {isRequestsOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              <span>Requests</span>
            </Button>

            {/* Accordion content */}
            {isRequestsOpen && (
              <div className="mt-3 animate-in fade-in slide-in-from-top-2 duration-200 space-y-3">
                {/* Existing request cards for this target */}
                {itemEscalations.length > 0 && (
                  <div className="space-y-2">
                    {itemEscalations.map(esc => (
                      <div
                        key={esc.id}
                        className="rounded-lg border border-border bg-card p-3 text-xs shadow-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between font-medium">
                          <span className="flex items-center gap-1.5 capitalize">
                            {esc.status === "pending" ? (
                              <Clock className="h-4 w-4 text-amber-500 animate-pulse" />
                            ) : (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full">
                                {esc.status}
                              </span>
                            )}
                            {esc.field_name}
                          </span>
                          <span className="text-muted-foreground text-[10px] tabular-nums">
                            {esc.created_at ? new Date(esc.created_at).toLocaleDateString() : ""}
                          </span>
                        </div>
                        <div className="text-muted-foreground">
                          Suggested: <span className="font-mono text-foreground">{esc.suggested_value}</span>
                        </div>
                        {esc.resolution_note && (
                          <div className="rounded bg-muted/50 p-1.5 text-[11px] italic text-muted-foreground border-l-2 border-primary/50">
                            Custodian note: &ldquo;{esc.resolution_note}&rdquo;
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Ask custodians button - only inside accordion */}
                <EscalationTrigger level="item" targetId={item.id} escalations={itemEscalations} alwaysShowDialog />
              </div>
            )}
          </div>
        )}
      </div>

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
