"use client";

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
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, Library, Share2 } from "lucide-react";

import { useResolvedRouteParam } from "@/lib/capacitor/route-params";
import { buildPaginationWindow } from "@/lib/pagination";
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
  content_type?: string | null;
  format?: string | null;
  ean?: string | null;
  upc?: string | null;
  publisher?: string | null;
  publication_year?: string | number | null;
  catalog_number?: string | null;
  country?: string | null;
  lod_links?: Record<string, string> | null;
}

export interface SharedCollectionData {
  author: string;
  collection_name: string;
  collection_description?: string;
  total?: number;
  page?: number;
  per_page?: number;
  pages?: number;
  items: SharedCollectionItem[];
}

interface SharedCollectionClientProps {
  initialData?: SharedCollectionData | null;
  initialToken?: string;
  publicBaseUrl?: string;
}

/**
 * Client-hydrated shared collection view for web and native Capacitor shells.
 *
 * @param {SharedCollectionClientProps} props - Component props.
 * @returns {JSX.Element} Rendered shared collection page.
 */
export function SharedCollectionClient({ initialData, initialToken, publicBaseUrl }: SharedCollectionClientProps) {
  const resolvedToken = useResolvedRouteParam("token") || initialToken;
  const t = useTranslations("Public");

  const [collection, setCollection] = useState<SharedCollectionData | null>(initialData || null);
  const activeCollection = initialData ?? collection;
  const [isLoading, setIsLoading] = useState<boolean>(!initialData && !!resolvedToken);
  const [isError, setIsError] = useState<boolean>(false);
  const [isNotFound, setIsNotFound] = useState<boolean>(false);

  useEffect(() => {
    if (initialData) return;
    if (!resolvedToken || resolvedToken === "_placeholder") return;

    let isMounted = true;

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

  if (isLoading || !activeCollection) {
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

  const items = activeCollection.items || [];
  const totalItems = activeCollection.total ?? items.length;
  const currentPage = activeCollection.page ?? 1;
  const totalPages = activeCollection.pages ?? (totalItems > 0 ? 1 : 0);
  const paginationWindow = buildPaginationWindow(currentPage, totalPages);
  const normalizedBaseUrl = (publicBaseUrl || "").replace(/\/+$/, "");
  const jsonLdPageUrl = resolvedToken
    ? normalizedBaseUrl
      ? `${normalizedBaseUrl}/share/${resolvedToken}?format=jsonld&page=1`
      : `/share/${resolvedToken}?format=jsonld&page=1`
    : "";

  const renderPagination = () => {
    if (totalPages <= 1 || !resolvedToken) return null;
    return (
      <nav aria-label="Collection pagination" className="my-6 flex flex-wrap items-center justify-center gap-1.5">
        {currentPage > 1 && (
          <Link
            href={`/share/${resolvedToken}?page=${currentPage - 1}`}
            aria-label="Previous page"
            className="inline-flex h-9 items-center gap-1 rounded-md border bg-background px-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            <span className="hidden sm:inline">Prev</span>
          </Link>
        )}
        {paginationWindow.map((pageNum, idx) => {
          const prevNum = idx > 0 ? paginationWindow[idx - 1] : null;
          const showEllipsis = prevNum !== null && pageNum - prevNum > 1;
          const isCurrent = pageNum === currentPage;
          return (
            <span key={pageNum} className="inline-flex items-center gap-1.5">
              {showEllipsis && <span className="px-1 text-sm text-muted-foreground">…</span>}
              <Link
                href={`/share/${resolvedToken}?page=${pageNum}`}
                aria-current={isCurrent ? "page" : undefined}
                className={`inline-flex h-9 min-w-9 items-center justify-center rounded-md border px-2.5 text-sm font-medium transition-colors ${
                  isCurrent
                    ? "border-primary bg-primary text-primary-foreground"
                    : "bg-background text-muted-foreground hover:text-foreground"
                }`}
              >
                {pageNum}
              </Link>
            </span>
          );
        })}
        {currentPage < totalPages && (
          <Link
            href={`/share/${resolvedToken}?page=${currentPage + 1}`}
            aria-label="Next page"
            className="inline-flex h-9 items-center gap-1 rounded-md border bg-background px-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight className="h-4 w-4" />
          </Link>
        )}
      </nav>
    );
  };

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
              {activeCollection.collection_name}
            </h1>

            <p className="text-muted-foreground text-sm uppercase tracking-[0.2em] font-bold mb-6">
              Shared by <span className="text-foreground">@{activeCollection.author}</span>
            </p>

            {activeCollection.collection_description && (
              <p className="text-muted-foreground max-w-2xl mx-auto mb-8 leading-relaxed">
                {activeCollection.collection_description}
              </p>
            )}

            <div className="flex flex-wrap items-center justify-center gap-3">
              <ShareButton
                title={activeCollection.collection_name}
                text={`Check out this shared collection by ${activeCollection.author} on iqoqo!`}
              />
              {resolvedToken && <PublicFeedButton feedPath={`/share/${resolvedToken}/feed.xml`} />}
              {resolvedToken && (
                <PublicFeedButton
                  feedPath={jsonLdPageUrl}
                  label={t("jsonLdFeed")}
                  title={t("jsonLdFeedTitle")}
                  variant="jsonld"
                />
              )}
            </div>
          </div>
        </div>

        {/* Content Section */}
        <div className="mx-auto max-w-5xl px-6 py-12">
          <div className="flex items-center justify-between border-b pb-4 mb-8">
            <h2 className="text-xl font-serif font-bold">Items in this Collection</h2>
            <span className="text-sm font-medium bg-muted px-2 py-1 rounded">
              {totalItems} {totalItems === 1 ? "Item" : "Items"}
            </span>
          </div>

          {items.length > 0 ? (
            <>
              {renderPagination()}
              <CollectionGrid items={items as unknown as (Item | CatalogEntry)[]} />
              {renderPagination()}
            </>
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
