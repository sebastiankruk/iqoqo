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

import type { Metadata } from "next";
import { resolveApiUrl, getCoverUrl, getCoverTimestamp } from "@/lib/utils";
import { buildManifestationJsonLd, type OfferOptions } from "@/lib/schema-org";
import type { CatalogEntry } from "@/types/frbr";
import { ManifestationDetailClient } from "@/components/manifestation/manifestation-detail-client";

interface Props {
  params: Promise<{ id: string }>;
}

/**
 * Server-side data fetcher for manifestation detail.
 *
 * @param {string | number} id - The manifestation ID.
 * @returns {Promise<CatalogEntry | null>} Manifestation data or null if not found.
 */
async function getManifestation(id: string | number): Promise<CatalogEntry | null> {
  try {
    const res = await fetch(resolveApiUrl(`/manifestations/${id}`, true), {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json.data || null;
  } catch {
    return null;
  }
}

/**
 * Generates SEO metadata for the manifestation detail page.
 *
 * @param {Props} props - Page props containing params promise.
 * @returns {Promise<Metadata>} Metadata object for Next.js.
 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const manifestation = await getManifestation(id);

  if (!manifestation) {
    return { title: "Manifestation Not Found - iqoqo" };
  }

  const title = manifestation.title || "Untitled Work";
  const authors = Array.isArray(manifestation.authors) ? manifestation.authors.join(", ") : manifestation.authors || "";
  const description = authors ? `${title} by ${authors}` : title;

  const timestamp = getCoverTimestamp(manifestation.meta);
  const coverUrl =
    getCoverUrl(manifestation.cover_url || undefined, timestamp) ||
    (manifestation.meta?.["cover_url"] as string | undefined);

  return {
    title: `${title} - iqoqo`,
    description,
    openGraph: {
      title: `${title} - iqoqo`,
      description,
      images: coverUrl ? [{ url: coverUrl }] : [],
    },
    alternates: {
      types: {
        "application/ld+json": [
          {
            url: `/api/manifestations/${manifestation.id}`,
            title: `${title} - Schema.org JSON-LD`,
          },
        ],
      },
    },
  };
}

/**
 * Server Component for the Manifestation detail page.
 * Emits Schema.org JSON-LD and initial HTML during SSR so non-JS crawlers
 * and AI agents receive full semantic knowledge on HTTP GET.
 *
 * @param {Props} props - Page props containing params promise.
 * @returns {Promise<JSX.Element>} Server-rendered page with JSON-LD.
 */
export default async function ManifestationPage({ params }: Props) {
  const { id } = await params;
  const manifestationId = Number(id);
  const manifestation = await getManifestation(manifestationId);

  let jsonLdData: Record<string, unknown> | null = null;
  if (manifestation) {
    const timestamp = getCoverTimestamp(manifestation.meta);
    const coverUrl =
      getCoverUrl(manifestation.cover_url || undefined, timestamp) ||
      (manifestation.meta?.["cover_url"] as string | undefined);
    const resolved_year = manifestation.year || manifestation.meta?.Year || manifestation.meta?.year;
    const format =
      (manifestation.meta?.format as string | undefined) || (manifestation.meta?.Format as string | undefined);

    const offersList: OfferOptions[] = [];
    const rawItems = (
      manifestation as unknown as {
        items?: Array<{ collection_status?: string; status?: string; price?: number; currency?: string }>;
      }
    ).items;

    if (Array.isArray(rawItems) && rawItems.length > 0) {
      for (const itm of rawItems) {
        offersList.push({
          status: itm.collection_status || itm.status || (manifestation.user_owns ? "owned" : "available"),
          price: itm.price,
          currency: itm.currency,
        });
      }
    } else if (manifestation.user_owns) {
      offersList.push({ status: "owned" });
    } else if (manifestation.wishlist_item_id) {
      offersList.push({ status: "wishlist" });
    } else if (manifestation.meta?.collection_status) {
      offersList.push({ status: String(manifestation.meta.collection_status) });
    } else {
      offersList.push({ status: "available" });
    }

    jsonLdData = buildManifestationJsonLd({
      id: manifestation.id,
      title: manifestation.title || "Untitled Work",
      authors: (manifestation.meta?.authors as string[] | string | undefined) ?? manifestation.authors,
      coverUrl: coverUrl || undefined,
      isbn:
        manifestation.isbn13 ||
        (manifestation.meta?.isbn as string | undefined) ||
        (manifestation.meta?.isbn13 as string | undefined) ||
        undefined,
      publisher:
        (manifestation.meta?.Publisher as string | undefined) || (manifestation.publisher as string | undefined),
      datePublished: resolved_year as string | number | undefined,
      language:
        (manifestation.meta?.language as string | undefined) ||
        (manifestation.meta?.Language as string | undefined) ||
        (manifestation as unknown as { language?: string }).language,
      contentType: manifestation.content_type,
      expressionKind: manifestation.expression_kind,
      format: format,
      offers: offersList,
    });
  }

  return (
    <>
      {jsonLdData && (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdData) }} />
      )}
      <ManifestationDetailClient manifestationId={manifestationId} initialManifestation={manifestation} />
    </>
  );
}
