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
import React from "react";
import { HELP_ARTICLES } from "@/lib/help-articles";
import { HelpArticleDetailClient } from "@/components/help/help-article-detail-client";

interface Props {
  params: Promise<{ slug: string }>;
}

/**
 * Generates static placeholder params and all article slugs for Next.js static export.
 *
 * @returns Array of route params.
 */
export function generateStaticParams() {
  const articleParams = HELP_ARTICLES.map(a => ({ slug: a.slug }));
  return [{ slug: "_placeholder" }, ...articleParams];
}

/**
 * Help article detail page.
 *
 * @param props - Component props containing route params promise.
 * @returns Server-rendered page wrapping the client article viewer.
 */
export default async function HelpArticleDetailPage({ params }: Props) {
  const { slug } = await params;
  return <HelpArticleDetailClient initialSlug={slug} />;
}
