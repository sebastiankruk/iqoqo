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

import { use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { HeroBanner } from "@/components/item/hero-banner";
import { ItemSidebar } from "@/components/item/item-sidebar";
import { ItemHeader } from "@/components/item/item-header";
import { ItemActions } from "@/components/item/item-actions";
import { ItemTabs } from "@/components/item/item-tabs";
import { useItem, useManifestationWithPolling } from "@/lib/api/hooks";
import { getCoverUrl, getCoverTimestamp } from "@/lib/utils";
import type { Item } from "@/types/frbr";

/** Page props for the Item page. */
interface Props {
  params: Promise<{ id: string }>;
}

/**
 * Renders the item detail content (hero, sidebar, tabs, actions).
 *
 * @param {{ item: Item }} props - Component props.
 * @param {Item} props.item - The item to display.
 * @returns {JSX.Element}
 */
function ItemDetail(props: { item: Item }) {
  const { item: initialItem } = props;
  const { item } = useManifestationWithPolling(initialItem);
  const router = useRouter();

  const timestamp = getCoverTimestamp(item.manifestation_meta, item.meta);

  const coverUrl =
    getCoverUrl(item.cover_url || undefined, timestamp) ||
    ((item.manifestation_meta?.["cover_url"] as string | undefined) ??
      (item.meta?.["cover_url"] as string | undefined));

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
              <ItemActions item={item} />
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-8 flex items-center justify-between px-2">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to collection
          </button>
          <p className="text-xs text-muted-foreground">
            <span className="font-serif font-bold text-foreground">iqoqo</span> &middot; The Library of Everything
          </p>
        </footer>
      </div>
    </>
  );
}

/**
 * Item detail page showing the full FRBR hierarchy for one item.
 *
 * @param {Props} props - Page props containing `params` promise.
 * @param {Promise<{id: string}>} props.params - Route params promise provided by Next.js.
 * @returns {JSX.Element}
 */
export default function ItemPage(props: Props) {
  const { params } = props;
  const { id } = use(params);
  const itemId = parseInt(id, 10);
  const router = useRouter();

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
          <button onClick={() => router.back()} className="mt-4 text-sm font-medium text-accent hover:underline">
            Back to collection
          </button>
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
