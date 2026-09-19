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
import { notFound } from "next/navigation";
import { resolveApiUrl, getCoverUrl } from "@/lib/utils";
import { WorkStructuredData } from "@/components/work/work-structured-data";
import { WorkDetailClient } from "@/components/work/work-detail-client";
import type { WorkDetail } from "@/types/frbr";

interface Props {
  params: Promise<{ id: string }>;
}

/**
 * Server-side data fetcher for Work detail.
 *
 * @param {string | number} id - The Work ID.
 * @returns {Promise<WorkDetail | null>} Work data or null if not found.
 */
async function getWork(id: string | number): Promise<WorkDetail | null> {
  try {
    const res = await fetch(resolveApiUrl(`/works/${id}`, true), {
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
 * Generates SEO metadata for the Work detail page.
 *
 * @param {Props} props - Page props containing params promise.
 * @returns {Promise<Metadata>} Metadata object for Next.js.
 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const work = await getWork(id);

  if (!work) {
    return { title: "Work Not Found - iqoqo" };
  }

  const title = work.title || "Untitled Work";
  const authors = Array.isArray(work.authors) ? work.authors.join(", ") : work.authors || "";
  const description = authors ? `${title} by ${authors}` : title;

  let coverUrl: string | undefined;
  for (const expr of work.expressions || []) {
    for (const m of expr.manifestations || []) {
      if (m.cover_url) {
        coverUrl = getCoverUrl(m.cover_url);
        break;
      }
    }
    if (coverUrl) break;
  }

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
            url: `/api/public/works/${work.id}`,
            title: `${title} - Schema.org JSON-LD`,
          },
        ],
      },
    },
  };
}

/**
 * Server Component for the Conceptual Work detail page.
 * Emits Schema.org CreativeWork JSON-LD and initial HTML during SSR so non-JS crawlers
 * and AI agents receive full semantic knowledge on HTTP GET.
 *
 * @param {Props} props - Page props containing params promise.
 * @returns {Promise<JSX.Element>} Server-rendered page with JSON-LD and Microdata.
 */
export default async function WorkPage({ params }: Props) {
  const { id } = await params;
  const workId = Number(id);
  const work = await getWork(workId);

  if (!work) {
    notFound();
  }

  // Collect all manifestations across all expressions for Schema.org workExample
  const refManifestations: Array<{
    id: number | string;
    title?: string | null;
    isbn?: string | null;
    language?: string | null;
    contentType?: string | null;
    expressionKind?: string | null;
    format?: string | null;
    year?: number | string | null;
  }> = [];

  for (const expr of work.expressions || []) {
    for (const m of expr.manifestations || []) {
      refManifestations.push({
        id: m.id,
        title: m.title || work.title,
        isbn: m.isbn13 || m.ean,
        language: expr.language,
        contentType: expr.content_type,
        expressionKind: expr.kind,
        format: m.format_type || m.format,
        year: m.year,
      });
    }
  }

  const workJsonLdData = {
    id: work.id,
    title: work.title,
    authors: work.authors,
    manifestations: refManifestations,
  };

  return (
    <>
      <WorkStructuredData data={workJsonLdData} />
      <WorkDetailClient workId={workId} initialWork={work} />
    </>
  );
}
