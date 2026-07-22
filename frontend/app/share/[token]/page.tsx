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

import { notFound } from "next/navigation";
import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Library, Share2, Rss } from "lucide-react";

import { resolveApiUrl } from "@/lib/utils";
import { CollectionGrid } from "@/components/collection/collection-grid";
import { EmptyState } from "@/components/ui/empty-state";
import { ShareButton } from "@/components/ui/share-button";
import { Footer } from "@/components/dashboard/footer";
import { Navbar } from "@/components/dashboard/navbar";

interface SharedCollectionPageProps {
  params: Promise<{ token: string }>;
}

/**
 * Fetches a shared collection by its secure token.
 * @param token - The unique share token.
 * @returns The shared collection data or null if not found.
 */
async function getSharedCollection(token: string) {
  try {
    const res = await fetch(resolveApiUrl(`/public/share/${token}`, true), {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Generates SEO metadata for the shared collection page.
 * @param props - Component props.
 * @param props.params - The route parameters.
 * @returns Metadata object for Next.js.
 */
export async function generateMetadata({ params }: SharedCollectionPageProps): Promise<Metadata> {
  const { token } = await params;
  const collectionRes = await getSharedCollection(token);

  if (!collectionRes || !collectionRes.success) {
    return { title: "Collection Not Found - iqoqo" };
  }

  const collection = collectionRes.data;
  return {
    title: `${collection.collection_name} - Shared by ${collection.author} - iqoqo`,
    description:
      collection.collection_description || `A shared collection on iqoqo with ${collection.items.length} items.`,
    alternates: {
      types: {
        "application/rss+xml": [
          { url: `/api/public/share/${token}/feed.xml`, title: `${collection.collection_name} Feed` },
        ],
      },
    },
  };
}

/**
 * Public page for viewing a shared collection via a secure token.
 * @param props - Component props.
 * @param props.params - The route parameters.
 * @returns The rendered page.
 */
export default async function SharedCollectionPage({ params }: SharedCollectionPageProps) {
  const { token } = await params;
  const t = await getTranslations("Public");

  const collectionRes = await getSharedCollection(token);
  if (!collectionRes || !collectionRes.success) {
    notFound();
  }

  const collection = collectionRes.data;
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
              <a
                href={`/api/public/share/${token}/feed.xml`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border bg-background px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground shadow-sm transition-all"
                title="Subscribe to collection RSS feed"
              >
                <Rss className="h-4 w-4 text-orange-500" />
                <span>RSS Feed</span>
              </a>
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
            <CollectionGrid items={items} />
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
