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

import { buildCollectionJsonLd } from "@/lib/schema-org";
import {
  getSharedCollection,
  renderSharedCollectionError,
  renderSharedCollectionJsonLdView,
  resolvePublicOrigin,
  SHARE_UI_PER_PAGE,
  type SharedCollectionItem,
} from "@/lib/share-server";
import { JsonLdScript } from "@/components/json-ld-script";
import { SharedCollectionClient } from "@/components/public/shared-collection-client";

interface SharedCollectionPageProps {
  params: Promise<{ token: string }>;
  searchParams?: Promise<{ page?: string; format?: string }>;
}

/** Generates static placeholder params for Capacitor static export builds. */
export function generateStaticParams() {
  return [{ token: "_placeholder" }];
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
  const totalCount = collection.total ?? collection.items.length;
  return {
    title: `${collection.collection_name} - Shared by ${collection.author} - iqoqo`,
    description: collection.collection_description || `A shared collection on iqoqo with ${totalCount} items.`,
    alternates: {
      types: {
        "application/rss+xml": [{ url: `/share/${token}/feed.xml`, title: `${collection.collection_name} Feed` }],
        "application/ld+json": [
          {
            url: `/share/${token}/catalog.jsonld`,
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
 * @param props.searchParams - Optional query parameters (`page`, `format`).
 * @returns The rendered page.
 */
export default async function SharedCollectionPage({ params, searchParams }: SharedCollectionPageProps) {
  const { token } = await params;
  if (token === "_placeholder") {
    return <SharedCollectionClient initialData={null} initialToken="_placeholder" />;
  }

  const resolvedSearch = process.env.CAPACITOR_BUILD === "true" ? undefined : await searchParams;
  const formatParam = (resolvedSearch?.format || "").trim().toLowerCase();
  const isJsonLdHtmlView = formatParam === "jsonld" || formatParam === "json-ld";
  const parsedPage = Number.parseInt(resolvedSearch?.page || "1", 10);
  const requestedPage = Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  if (isJsonLdHtmlView) {
    return renderSharedCollectionJsonLdView(token, requestedPage);
  }

  const collectionRes = await getSharedCollection(token, requestedPage, SHARE_UI_PER_PAGE);
  if (collectionRes.kind === "not-found") {
    notFound();
  }
  if (collectionRes.kind === "error") {
    return renderSharedCollectionError();
  }

  const collection = collectionRes.response.data;
  const items = collection.items || [];
  const totalItems = collection.total ?? items.length;
  const publicBaseUrl = resolvePublicOrigin();

  const collectionJsonLd = buildCollectionJsonLd({
    name: collection.collection_name,
    description: collection.collection_description || undefined,
    totalCount: totalItems,
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
      <SharedCollectionClient initialData={collection} initialToken={token} publicBaseUrl={publicBaseUrl} />
      <JsonLdScript data={collectionJsonLd} />
    </>
  );
}
