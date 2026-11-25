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
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Trash2,
  RefreshCw,
  CloudDownload,
  Pencil,
  Image as ImageIcon,
  ChevronDown,
  ChevronUp,
  ImageDown,
  Clock,
  Shield,
} from "lucide-react";
import { toast } from "sonner";

import { useDeleteItem, useRegenerateCover, queryKeys } from "@/lib/api/hooks";
import { useProfile } from "@/lib/api/hooks";
import { useMyEscalations } from "@/lib/api/escalations";
import { apiClient } from "@/lib/api/client";
import { PermissionName } from "@/lib/permissions";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useQueryClient } from "@tanstack/react-query";

/**
 * Item actions component.
 *
 * @param root0 - The props object
 * @param root0.item - The item
 * @param root0.compact - Whether to omit outer card chrome when embedded in sidebar accordion
 * @returns {JSX.Element | null} The component or null if no profile
 */
export function ItemActions({ item, compact = false }: { item: Item; compact?: boolean }) {
  const router = useRouter();
  const tAdmin = useTranslations("ItemDetail.adminActions");
  const regenerateCover = useRegenerateCover();
  const deleteItem = useDeleteItem();
  const qc = useQueryClient();

  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [regenerateConfirmOpen, setRegenerateConfirmOpen] = useState(false);
  const [isRequesting, setIsRequesting] = useState(false);
  const [isRefetching, setIsRefetching] = useState(false);
  const [isRefetchingCover, setIsRefetchingCover] = useState(false);
  const [isRequestsOpen, setIsRequestsOpen] = useState(false);

  const isPending = item.cover_status === "pending" || item.meta?.cover_status === "pending";

  const { data: profile } = useProfile();

  const hasEscalateRequestForHook = Boolean(profile?.permissions?.includes(PermissionName.ESCALATE_REQUEST));
  const hasWriteMetadataForHook = Boolean(profile?.permissions?.includes(PermissionName.WRITE_METADATA));
  const { data: myEscalations } = useMyEscalations(hasEscalateRequestForHook && !hasWriteMetadataForHook);

  // Filter escalations for this item
  const itemEscalations = myEscalations?.filter(e => e.item_id === item.id) ?? [];
  const pendingEscalation = itemEscalations.find(e => e.status === "pending");

  if (!profile) return null;

  const hasPermission = (perm: PermissionName): boolean => Boolean(profile.permissions?.includes(perm));
  const isOwner = Boolean(item.is_owner || (profile.id && item.owner_id === profile.id));
  const isAdmin = Boolean(profile.roles?.includes("admin"));
  const canModifyItem = isOwner || isAdmin;

  const canRefetchMetadata = hasPermission(PermissionName.REFETCH_METADATA) && Boolean(item.manifestation_id);
  const canEditFrbr = hasPermission(PermissionName.WRITE_METADATA) && Boolean(item.manifestation_id);
  const canRefetchCover = hasPermission(PermissionName.REFETCH_COVER) && Boolean(item.manifestation_id);
  const canRegenerateCover =
    (canModifyItem || hasPermission(PermissionName.WRITE_METADATA)) &&
    hasPermission(PermissionName.REGENERATE_COVER) &&
    Boolean(item.manifestation_id);
  const canEditCoverArt = hasPermission(PermissionName.EDIT_COVER) && Boolean(item.manifestation_id);
  const canDeleteItem = canModifyItem && hasPermission(PermissionName.DELETE_ITEM);

  const showAdminActions =
    canRefetchMetadata || canEditFrbr || canRefetchCover || canRegenerateCover || canEditCoverArt || canDeleteItem;

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

  const handleRefetchCover = async () => {
    if (!item.manifestation_id) return;
    setIsRefetchingCover(true);
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

  const showRequestsSection = hasEscalateRequestForHook && !hasWriteMetadataForHook;
  if (!showAdminActions && !showRequestsSection) {
    return null;
  }

  return (
    <div
      className={
        compact
          ? "flex flex-col gap-2.5"
          : "mt-6 flex flex-col gap-4 rounded-2xl border bg-card/50 p-4 sm:p-5 shadow-sm border-border/40"
      }
    >
      {/* Pending status card above controls */}
      {showRequestsSection && pendingEscalation && (
        <div
          data-testid="escalation-status-card"
          className="rounded-lg border border-border bg-card p-3 text-xs shadow-xs space-y-1.5"
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

      {showAdminActions && compact ? (
        <div className="flex flex-col gap-0.5 w-full" data-testid="admin-actions-inline-list">
          {canRefetchMetadata && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleRefetch}
              disabled={isRefetching}
              className="w-full justify-start h-8 px-2 text-xs gap-2 font-medium"
            >
              <CloudDownload className={`h-3.5 w-3.5 shrink-0 ${isRefetching ? "animate-bounce" : ""}`} />
              <span>{isRefetching ? tAdmin("fetching") : tAdmin("refetchMetadata")}</span>
            </Button>
          )}
          {canEditFrbr && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => router.push(`/admin/content?tab=metadata&manifestationId=${item.manifestation_id}`)}
              className="w-full justify-start h-8 px-2 text-xs gap-2 font-medium"
            >
              <Pencil className="h-3.5 w-3.5 shrink-0" />
              <span>{tAdmin("editFrbr")}</span>
            </Button>
          )}
          {canRefetchCover && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleRefetchCover}
              disabled={isPending || isRefetchingCover}
              className="w-full justify-start h-8 px-2 text-xs gap-2 font-medium"
            >
              <ImageDown className="h-3.5 w-3.5 shrink-0" />
              <span>{tAdmin("refetchCover")}</span>
            </Button>
          )}
          {canRegenerateCover && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleRegenerateClick}
              disabled={isPending || isRequesting}
              className="w-full justify-start h-8 px-2 text-xs gap-2 font-medium"
            >
              <RefreshCw className={`h-3.5 w-3.5 shrink-0 ${isRequesting ? "animate-spin" : ""}`} />
              <span>{tAdmin("regenerateCover")}</span>
            </Button>
          )}
          {canEditCoverArt && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => router.push(`/admin/content?tab=cover-art&manifestationId=${item.manifestation_id}`)}
              className="w-full justify-start h-8 px-2 text-xs gap-2 font-medium"
            >
              <ImageIcon className="h-3.5 w-3.5 shrink-0" />
              <span>{tAdmin("editCoverArt")}</span>
            </Button>
          )}
          {canDeleteItem && (
            <>
              {(canRefetchMetadata || canEditFrbr || canRefetchCover || canRegenerateCover || canEditCoverArt) && (
                <div className="my-1 border-t border-border/40" />
              )}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setDeleteConfirmOpen(true)}
                disabled={deleteItem.isPending}
                className="w-full justify-start h-8 px-2 text-xs gap-2 font-medium text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-3.5 w-3.5 shrink-0" />
                <span>{tAdmin("removeFromLibrary")}</span>
              </Button>
            </>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {showRequestsSection &&
            (itemEscalations.length > 0 ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsRequestsOpen(!isRequestsOpen)}
                className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer px-2"
              >
                {isRequestsOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                <span>Requests ({itemEscalations.length})</span>
              </Button>
            ) : (
              <EscalationTrigger level="item" targetId={item.id} escalations={itemEscalations} alwaysShowDialog />
            ))}

          {showAdminActions && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  data-testid="admin-actions-menu-trigger"
                  className="flex items-center gap-2 text-xs font-semibold"
                >
                  <Shield className="h-3.5 w-3.5" />
                  <span>{tAdmin("trigger")}</span>
                  <ChevronDown className="h-3.5 w-3.5 opacity-70" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                {canRefetchMetadata && (
                  <DropdownMenuItem onSelect={handleRefetch} disabled={isRefetching} className="cursor-pointer gap-2">
                    <CloudDownload className={`h-4 w-4 ${isRefetching ? "animate-bounce" : ""}`} />
                    <span>{isRefetching ? tAdmin("fetching") : tAdmin("refetchMetadata")}</span>
                  </DropdownMenuItem>
                )}
                {canEditFrbr && (
                  <DropdownMenuItem
                    onSelect={() => router.push(`/admin/content?tab=metadata&manifestationId=${item.manifestation_id}`)}
                    className="cursor-pointer gap-2"
                  >
                    <Pencil className="h-4 w-4" />
                    <span>{tAdmin("editFrbr")}</span>
                  </DropdownMenuItem>
                )}
                {canRefetchCover && (
                  <DropdownMenuItem
                    onSelect={handleRefetchCover}
                    disabled={isPending || isRefetchingCover}
                    className="cursor-pointer gap-2"
                  >
                    <ImageDown className="h-4 w-4" />
                    <span>{tAdmin("refetchCover")}</span>
                  </DropdownMenuItem>
                )}
                {canRegenerateCover && (
                  <DropdownMenuItem
                    onSelect={handleRegenerateClick}
                    disabled={isPending || isRequesting}
                    className="cursor-pointer gap-2"
                  >
                    <RefreshCw className={`h-4 w-4 ${isRequesting ? "animate-spin" : ""}`} />
                    <span>{tAdmin("regenerateCover")}</span>
                  </DropdownMenuItem>
                )}
                {canEditCoverArt && (
                  <DropdownMenuItem
                    onSelect={() =>
                      router.push(`/admin/content?tab=cover-art&manifestationId=${item.manifestation_id}`)
                    }
                    className="cursor-pointer gap-2"
                  >
                    <ImageIcon className="h-4 w-4" />
                    <span>{tAdmin("editCoverArt")}</span>
                  </DropdownMenuItem>
                )}
                {canDeleteItem && (
                  <>
                    {(canRefetchMetadata ||
                      canEditFrbr ||
                      canRefetchCover ||
                      canRegenerateCover ||
                      canEditCoverArt) && <DropdownMenuSeparator />}
                    <DropdownMenuItem
                      onSelect={() => setDeleteConfirmOpen(true)}
                      disabled={deleteItem.isPending}
                      className="cursor-pointer gap-2 text-destructive focus:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                      <span>{tAdmin("removeFromLibrary")}</span>
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      )}

      {showAdminActions && compact && showRequestsSection && (
        <div className="pt-1 border-t border-border/40">
          {itemEscalations.length > 0 ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsRequestsOpen(!isRequestsOpen)}
              className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer px-2"
            >
              {isRequestsOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              <span>Requests ({itemEscalations.length})</span>
            </Button>
          ) : (
            <EscalationTrigger level="item" targetId={item.id} escalations={itemEscalations} alwaysShowDialog />
          )}
        </div>
      )}

      {/* Requests accordion content */}
      {showRequestsSection && isRequestsOpen && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-200 space-y-3">
          {itemEscalations.length > 0 && (
            <div className="space-y-2">
              {itemEscalations.map(esc => (
                <div key={esc.id} className="rounded-lg border border-border bg-card p-3 text-xs shadow-xs space-y-1.5">
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

          <EscalationTrigger level="item" targetId={item.id} escalations={itemEscalations} alwaysShowDialog />
        </div>
      )}

      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{tAdmin("removeTitle")}</AlertDialogTitle>
            <AlertDialogDescription>{tAdmin("removeDescription")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteItem.isPending}>{tAdmin("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleteItem.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteItem.isPending ? tAdmin("removing") : tAdmin("remove")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={regenerateConfirmOpen} onOpenChange={setRegenerateConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{tAdmin("regenerateTitle")}</AlertDialogTitle>
            <AlertDialogDescription>{tAdmin("regenerateDescription")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tAdmin("cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleRegenerate}>{tAdmin("regenerate")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
