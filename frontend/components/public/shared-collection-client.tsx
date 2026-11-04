"useclient";

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

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Library, Share2 } from "lucide-react";

import { useResolvedRouteParam } from "@/lib/capacitor/route-params";
import { resolveApiUrl } from "@/lib/utils";
import type { Item, CatalogEntry } from "@/types/frbr";
import { CollectionGrid } from "@/components/collection/collection-grid";
import { EmptyState } from "@/components/ui/empty-state";
import { ShareButton } from "@/components/ui/share-button";
import { PublicFeedButton } from "@/components/ui/public-feed-button";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";

export interface SharedCollectionItem {
  id: number | string;
  manifestation_id?: number | string;
  title: string;
  authors?: string[];
  cover_url?: string;
  status?: string;
  collection_status?: string;
}

export interface SharedCollectionData {
  author: string;
  collection_name: string;
  collection_description?: string;
  items: SharedCollectionItem[];
}

interface SharedCollectionClientProps {
  initialData?: SharedCollectionData | null;
  initialToken?: string;
}

export function SharedCollectionClient({ initialData, initialToken }: SharedCollectionClientProps) {
  const resolvedToken = useResolvedRouteParam("token") || initialToken;
  const t = useTranslations("Public");

  const [collection, setCollection] = useState<SharedCollectionData | null>(initialData || null);
  const [isLoading, setIsLoading] = useState<boolean>(!initialData && !!resolvedToken);
  const [isError, setIsError] = useState<boolean>(false);
  const [isNotFound, setIsNotFound] = useState<boolean>(false);

  useEffect(() => {
    if (initialData) return;
    if (!resolvedToken || resolvedToken === "_placeholder") return;

    let isMounted = true;
    setIsLoading(true);
    setIsError(false);
    setIsNotFound(false);

    fetch(resolveApiUrl(`/public/share/${resolvedToken}`, false))
      .then(async res => {
        if (!isMounted) return;
        if (res.status === 404) {
          setIsNotFound(true);
          return;
        }
        if (!res.ok) {
          setIsError(true);
          return;
        }
        const json = await res.json();
        if (json.success && json.data) {
          setCollection(json.data);
        } else {
          setIsError(true);
        }
      })
      .catch(() => {
        if (isMounted) setIsError(true);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [initialData, resolvedToken]);

  if (isNotFound) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navbar />
        <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-16">
          <section role="alert" className="rounded-lg border border-muted bg-muted/20 p-6 text-center">
            <h1 className="text-2xl font-serif font-bold">Collection Not Found</h1>
            <p className="mt-3 text-muted-foreground">The requested shared collection does not exist or has expired.</p>
          </section>
        </main>
        <Footer />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navbar />
        <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-16">
          <section role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center">
            <h1 className="text-2xl font-serif font-bold">Server Error</h1>
            <p className="mt-3 text-muted-foreground">Please Try Again Later</p>
          </section>
        </main>
        <Footer />
      </div>
    );
  }

  if (isLoading || !collection) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navbar />
        <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-16 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </main>
        <Footer />
      </div>
    );
  }

  const items = collection.items || [];

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <main className="flex-1">
        {/* Header Section */}
        <div className="bg-primary/5 border-b">
          <div className="mx-auto max-w-5xl px-6 py-12 md:py-16 text-center">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 mb-6">
              <Share2 className="h-6 w-6 text-primary" />
            </div>

            <h1 className="text-3xl md:text-4xl font-serif font-bold tracking-tight mb-4">
              {collection.collection_name}
            </h1>

            <p className="text-muted-foreground text-sm uppercase tracking-[0.2em] font-bold mb-6">
              Shared by <span className="text-foreground">@{collection.author}</span>
            </p>

            {collection.collection_description && (
              <p className="text-muted-foreground max-w-2xl mx-auto mb-8 leading-relaxed">
                {collection.collection_description}
              </p>
            )}

            <div className="flex justify-center gap-4">
              <ShareButton
                title={collection.collection_name}
                text={`Check out this shared collection by ${collection.author} on iqoqo!`}
              />
              {resolvedToken && <PublicFeedButton feedPath={`/api/public/share/${resolvedToken}/feed.xml`} />}
            </div>
          </div>
        </div>

        {/* Content Section */}
        <div className="mx-auto max-w-5xl px-6 py-12">
          <div className="flex items-center justify-between border-b pb-4 mb-8">
            <h2 className="text-xl font-serif font-bold">Items in this Collection</h2>
            <span className="text-sm font-medium bg-muted px-2 py-1 rounded">
              {items.length} {items.length === 1 ? "Item" : "Items"}
            </span>
          </div>

          {items.length > 0 ? (
            <CollectionGrid items={items as unknown as (Item | CatalogEntry)[]} />
          ) : (
            <EmptyState
              title="Empty Collection"
              description="This shared collection doesn't contain any items yet."
              icon={Library}
            />
          )}
        </div>
      </main>
      <Footer />

      {/* Disclaimer footer */}
      <div className="bg-muted/30 py-4 text-center border-t">
        <p className="text-xs text-muted-foreground italic">{t("hiddenItemNote")}</p>
      </div>
    </div>
  );
}
