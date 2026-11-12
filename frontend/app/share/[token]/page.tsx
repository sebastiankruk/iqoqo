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

import { resolveApiUrl } from "@/lib/utils";
import { buildCollectionJsonLd } from "@/lib/schema-org";
import { JsonLdScript } from "@/components/json-ld-script";
import { SharedCollectionClient } from "@/components/public/shared-collection-client";
import { Footer } from "@/components/dashboard/footer";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";

interface SharedCollectionItem {
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

interface SharedCollectionData {
  author: string;
  collection_name: string;
  collection_description?: string;
  items: SharedCollectionItem[];
}

interface SharedCollectionResponse {
  success: boolean;
  data: SharedCollectionData;
}

type SharedCollectionResult =
  { kind: "success"; response: SharedCollectionResponse } | { kind: "not-found" } | { kind: "error" };

interface SharedCollectionPageProps {
  params: Promise<{ token: string }>;
}

/** Generates static placeholder params for Capacitor static export builds. */
export function generateStaticParams() {
  return [{ token: "_placeholder" }];
}

/**
 * Fetches a shared collection by its secure token.
 * @param token - The unique share token.
 * @returns The shared collection data, a not-found result, or a server error result.
 */
async function getSharedCollection(token: string): Promise<SharedCollectionResult> {
  try {
    const res = await fetch(resolveApiUrl(`/public/share/${token}?limit=1000`, true), {
      next: { revalidate: 60 },
    });
    if (res.status === 404) return { kind: "not-found" };
    if (!res.ok) return { kind: "error" };

    const response = (await res.json()) as SharedCollectionResponse;
    if (!response.success || !response.data) return { kind: "error" };
    return { kind: "success", response };
  } catch {
    return { kind: "error" };
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
  if (token === "_placeholder") {
    return { title: "iqoqo" };
  }
  const collectionRes = await getSharedCollection(token);

  if (collectionRes.kind !== "success") {
    return {
      title: collectionRes.kind === "not-found" ? "Collection Not Found - iqoqo" : "Shared Collection - iqoqo",
    };
  }

  const collection = collectionRes.response.data;
  return {
    title: `${collection.collection_name} - Shared by ${collection.author} - iqoqo`,
    description:
      collection.collection_description || `A shared collection on iqoqo with ${collection.items.length} items.`,
    alternates: {
      types: {
        "application/rss+xml": [
          { url: `/api/public/share/${token}/feed.xml`, title: `${collection.collection_name} Feed` },
        ],
        "application/ld+json": [
          {
            url: `/api/public/share/${token}?format=json-ld`,
            title: `${collection.collection_name} - Schema.org JSON-LD`,
          },
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
  if (token === "_placeholder") {
    return <SharedCollectionClient initialData={null} initialToken="_placeholder" />;
  }

  const collectionRes = await getSharedCollection(token);
  if (collectionRes.kind === "not-found") {
    notFound();
  }
  if (collectionRes.kind === "error") {
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

  const collection = collectionRes.response.data;
  const items = collection.items || [];

  const collectionJsonLd = buildCollectionJsonLd({
    name: collection.collection_name,
    description: collection.collection_description || undefined,
    totalCount: items.length,
    authorName: collection.author,
    items: items.slice(0, 1000).map((item: SharedCollectionItem) => {
      const sameAs: string[] = [];
      if (item.lod_links) {
        for (const key of ["discogs_uri", "musicbrainz_uri", "wikidata_uri", "opencollections_uri"]) {
          if (item.lod_links[key]) sameAs.push(item.lod_links[key]);
        }
      }
      return {
        id: item.manifestation_id || item.id,
        title: item.title,
        url: `/manifestation/${item.manifestation_id || item.id}`,
        contentType: item.content_type,
        format: item.format,
        authors: item.authors,
        ean: item.ean,
        upc: item.upc,
        publisher: item.publisher,
        catalogNumber: item.catalog_number,
        publicationYear: item.publication_year,
        country: item.country,
        sameAs: sameAs.length > 0 ? sameAs : undefined,
      };
    }),
  });

  return (
    <>
      <JsonLdScript data={collectionJsonLd} />
      <SharedCollectionClient initialData={collection} initialToken={token} />
    </>
  );
}
