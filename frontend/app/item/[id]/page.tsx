"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/dashboard/navbar";
import { HeroBanner } from "@/components/item/hero-banner";
import { ItemSidebar } from "@/components/item/item-sidebar";
import { ItemHeader } from "@/components/item/item-header";
import { ItemTabs } from "@/components/item/item-tabs";
import { useItem, useDeleteItem } from "@/lib/api/hooks";

interface Props {
  params: Promise<{ id: string }>;
}

/** Item detail page showing the full FRBR hierarchy for one item. */
export default function ItemPage({ params }: Props) {
  const { id } = use(params);
  const itemId = parseInt(id, 10);
  const router = useRouter();

  const { data: item, isLoading, isError } = useItem(itemId);
  const deleteItem = useDeleteItem();

  const handleDelete = () => {
    if (!confirm("Delete this item from your library? This cannot be undone."))
      return;
    deleteItem.mutate(itemId, {
      onSuccess: () => {
        toast.success("Item removed from library");
        router.push("/collection");
      },
      onError: (e) => toast.error(e.message),
    });
  };

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

  const coverUrl =
    (item.manifestation_meta?.["cover_url"] as string | undefined) ??
    (item.meta?.["cover_url"] as string | undefined);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
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
              <div className="mt-4 border-t border-border pt-4">
                <button
                  onClick={handleDelete}
                  disabled={deleteItem.isPending}
                  className="flex items-center gap-2 text-xs font-medium text-destructive/70 transition-colors hover:text-destructive disabled:opacity-50"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove from library
                </button>
              </div>
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
            {" "}&middot;{" "}Modern Athenaeum
          </p>
        </footer>
      </div>
    </div>
  );
}
