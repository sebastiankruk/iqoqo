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
import { ExpressionStructuredData } from "@/components/expression/expression-structured-data";
import { ExpressionDetailClient } from "@/components/expression/expression-detail-client";
import type { ExpressionDetail } from "@/types/frbr";

interface Props {
  params: Promise<{ id: string }>;
}

/**
 * Server-side data fetcher for Expression detail.
 *
 * @param {string | number} id - The Expression ID.
 * @returns {Promise<ExpressionDetail | null>} Expression data or null if not found.
 */
async function getExpression(id: string | number): Promise<ExpressionDetail | null> {
  try {
    const res = await fetch(resolveApiUrl(`/expressions/${id}`, true), {
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
 * Generates SEO metadata for the Expression detail page.
 *
 * @param {Props} props - Page props containing params promise.
 * @returns {Promise<Metadata>} Metadata object for Next.js.
 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const expr = await getExpression(id);

  if (!expr) {
    return { title: "Expression Not Found - iqoqo" };
  }

  const title = `${expr.work_title} (${expr.language ? expr.language.toUpperCase() + " " : ""}${expr.content_type || "Expression"})`;
  const authors = Array.isArray(expr.authors) ? expr.authors.join(", ") : expr.authors || "";
  const description = authors ? `${title} by ${authors}` : title;

  let coverUrl: string | undefined;
  for (const m of expr.manifestations || []) {
    if (m.cover_url) {
      coverUrl = getCoverUrl(m.cover_url);
      break;
    }
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
            url: `/api/public/expressions/${expr.id}`,
            title: `${title} - Schema.org JSON-LD`,
          },
        ],
      },
    },
  };
}

/**
 * Server Component for the Expression detail page.
 * Emits Schema.org CreativeWork JSON-LD and initial HTML during SSR so non-JS crawlers
 * and AI agents receive full semantic knowledge on HTTP GET.
 *
 * @param {Props} props - Page props containing params promise.
 * @returns {Promise<JSX.Element>} Server-rendered page with JSON-LD and Microdata.
 */
export default async function ExpressionPage({ params }: Props) {
  const { id } = await params;
  const exprId = Number(id);
  const expr = await getExpression(exprId);

  if (!expr) {
    notFound();
  }

  const refManifestations = (expr.manifestations || []).map(m => ({
    id: m.id,
    title: m.title || expr.work_title,
    isbn: m.isbn13 || m.ean,
    language: expr.language,
    contentType: expr.content_type,
    expressionKind: expr.kind,
    format: m.format_type || m.format,
    year: m.year,
  }));

  const exprJsonLdData = {
    id: expr.id,
    workId: expr.work_id,
    workTitle: expr.work_title,
    authors: expr.authors,
    language: expr.language,
    contentType: expr.content_type,
    expressionKind: expr.kind,
    manifestations: refManifestations,
  };

  return (
    <>
      <ExpressionStructuredData data={exprJsonLdData} />
      <ExpressionDetailClient expressionId={exprId} initialExpression={expr} />
    </>
  );
}
