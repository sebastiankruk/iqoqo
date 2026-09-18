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
import { WorkStructuredData } from "@/components/work/work-structured-data";
import { ItemPageClient } from "@/components/item/item-page-client";
import type { Item } from "@/types/frbr";

/** Page props for the Item page. */
interface Props {
  params: Promise<{ id: string }>;
}

/**
 * Server-side data fetcher for item detail.
 *
 * @param {string | number} id - The item ID.
 * @returns {Promise<Item | null>} Item data or null if not found.
 */
async function getItem(id: string | number): Promise<Item | null> {
  try {
    const res = await fetch(resolveApiUrl(`/items/${id}`, true), {
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
 * Generates SEO metadata for the item detail page.
 *
 * @param {Props} props - Page props containing params promise.
 * @returns {Promise<Metadata>} Metadata object for Next.js.
 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const item = await getItem(id);

  if (!item) {
    return { title: "Item Not Found - iqoqo" };
  }

  const title = item.work?.title || item.title || "Untitled Item";
  const authors = item.work?.authors ?? item.authors;
  const authorText = Array.isArray(authors) ? authors.join(", ") : authors || "";
  const description = authorText ? `${title} by ${authorText}` : title;

  const timestamp = getCoverTimestamp(item.manifestation_meta, item.meta);
  const coverUrl =
    getCoverUrl(item.cover_url || undefined, timestamp) ||
    ((item.manifestation_meta?.["cover_url"] as string | undefined) ??
      (item.meta?.["cover_url"] as string | undefined));

  return {
    title: `${title} - iqoqo`,
    description,
    openGraph: {
      title: `${title} - iqoqo`,
      description,
      images: coverUrl ? [{ url: coverUrl }] : [],
    },
  };
}

/**
 * Item detail page showing the full FRBR hierarchy for one item.
 * Renders WorkStructuredData in SSR so search crawlers and AI agents
 * receive canonical FRBR Schema.org JSON-LD without needing JavaScript.
 *
 * @param {Props} props - Page props containing params promise.
 * @returns {Promise<JSX.Element>} Server-rendered page with JSON-LD.
 */
export default async function ItemPage(props: Props) {
  const { params } = props;
  const { id } = await params;
  const itemId = parseInt(id, 10);
  const item = await getItem(itemId);

  const workData = item
    ? {
        id: item.work?.id || item.manifestation_id,
        title: item.work?.title || item.title || "Untitled Work",
        authors: item.work?.authors ?? item.authors,
        manifestations: [
          {
            id: item.manifestation_id,
            title: item.title,
            isbn: item.isbn,
            language: item.expression?.language,
            contentType: item.content_type || item.expression?.content_type,
            expressionKind: item.expression?.kind,
            format: (item.meta?.format as string) || (item.manifestation_meta?.format as string),
          },
        ],
      }
    : null;

  return (
    <>
      {workData && <WorkStructuredData data={workData} />}
      <ItemPageClient itemId={itemId} initialItem={item} />
    </>
  );
}
