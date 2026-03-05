"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Trash2, RefreshCw, CloudDownload } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/dashboard/navbar";
import { HeroBanner } from "@/components/item/hero-banner";
import { ItemSidebar } from "@/components/item/item-sidebar";
import { ItemHeader } from "@/components/item/item-header";
import { ItemTabs } from "@/components/item/item-tabs";
import { useItem, useDeleteItem, useManifestationWithPolling, useRegenerateCover, queryKeys } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";
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
import type { Item } from "@/types/frbr";
import { useQueryClient } from "@tanstack/react-query";

interface Props {
  params: Promise<{ id: string }>;
}

function ItemDetail({ item: initialItem }: { item: Item }) {
  const router = useRouter();
  const { item } = useManifestationWithPolling(initialItem);
  const qc = useQueryClient(); // Add this to access the React Query cache!
  const deleteItem = useDeleteItem();
  const regenerateCover = useRegenerateCover();

  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [regenerateConfirmOpen, setRegenerateConfirmOpen] = useState(false);
  const [isRequesting, setIsRequesting] = useState(false);
  const [isRefetching, setIsRefetching] = useState(false);

  const isPending = item.cover_status === 'pending';

  const handleConfirmDelete = () => {
    deleteItem.mutate(item.id, {
      onSuccess: () => {
        toast.success("Item removed from library");
        router.push("/collection");
      },
      onError: (e) => toast.error(e.message),
    });
  };

  const handleRegenerateClick = () => {
    const hasCover = !!(item.cover_path || item.manifestation_meta?.["cover_url"] || item.meta?.["cover_url"]);
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
      // Tell React Query to update the cache for this specific item
      qc.setQueryData(queryKeys.item(item.id), (prev: Item | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          cover_status: 'pending'
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
    } catch (error) {
      toast.error("Failed to refetch metadata");
    } finally {
      setIsRefetching(false);
    }
  };

  const coverUrl = item.cover_path
    ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api"}${item.cover_path}`
    : (item.manifestation_meta?.["cover_url"] as string | undefined) ??
      (item.meta?.["cover_url"] as string | undefined);

  return (
    <>
      <HeroBanner coverUrl={coverUrl} title={item.work?.title ?? item.title} />

      <div className="relative z-10 mx-auto -mt-12 max-w-6xl px-4 pb-12 sm:px-6">
        <div className="overflow-hidden rounded-xl bg-card shadow-lg ring-1 ring-border/60">
          <div className="flex flex-col lg:flex-row">
            {/* Sidebar – 30% */}
            <aside className="w-full border-b border-border bg-card p-6 lg:w-[30%] lg:border-b-0 lg:border-r">
              <ItemSidebar item={item} />
            </aside>

            {/* Main content – 70% */}
            <div className="flex w-full flex-col gap-6 p-6 lg:w-[70%] lg:p-8">
              <ItemHeader item={item} />
              <ItemTabs item={item} />

              {/* Danger zone */}
              <div className="mt-4 border-t border-border pt-4 flex items-center gap-6">
                <button
                  onClick={handleRefetch}
                  disabled={isRefetching}
                  className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
                >
                  <CloudDownload className={`h-3.5 w-3.5 ${isRefetching ? 'animate-bounce' : ''}`} />
                  {isRefetching ? "Fetching..." : "Refetch Metadata"}
                </button>

                <button
                  onClick={handleRegenerateClick}
                  disabled={isPending || isRequesting}
                  className="flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${isPending ? 'animate-spin' : ''}`} />
                  {isPending ? "Generating..." : "Regenerate Cover"}
                </button>

                <button
                  onClick={() => setDeleteConfirmOpen(true)}
                  disabled={deleteItem.isPending}
                  className="flex items-center gap-2 text-xs font-medium text-destructive/70 transition-colors hover:text-destructive disabled:opacity-50"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove from library
                </button>
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
                    <AlertDialogAction onClick={handleRegenerate}>
                      Regenerate
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-8 flex items-center justify-between px-2">
          <Link
            href="/collection"
            className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to collection
          </Link>
          <p className="text-xs text-muted-foreground">
            <span className="font-serif font-bold text-foreground">iqoqo</span>
            {" "}&middot;{" "}The Library of Everything
          </p>
        </footer>
      </div>
    </>
  );
}

/** Item detail page showing the full FRBR hierarchy for one item. */
export default function ItemPage({ params }: Props) {
  const { id } = use(params);
  const itemId = parseInt(id, 10);

  const { data: item, isLoading, isError } = useItem(itemId);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="h-[200px] animate-pulse bg-primary/20" />
        <div className="mx-auto -mt-12 max-w-6xl px-4 pb-12 sm:px-6">
          <div className="h-96 animate-pulse rounded-xl bg-card" />
        </div>
      </div>
    );
  }

  if (isError || !item) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="flex flex-col items-center justify-center py-32">
          <p className="text-muted-foreground">Item not found.</p>
          <Link
            href="/collection"
            className="mt-4 text-sm font-medium text-accent hover:underline"
          >
            Back to collection
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <ItemDetail item={item} />
    </div>
  );
}
