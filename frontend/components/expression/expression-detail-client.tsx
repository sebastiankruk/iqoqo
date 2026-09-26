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
"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { ArrowLeft, BookOpen, Disc, Film, Gamepad2, Layers, Music, Sparkles } from "lucide-react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { resolveSchemaType } from "@/lib/schema-org";
import { getCoverUrl } from "@/lib/utils";
import type { ExpressionDetail } from "@/types/frbr";

export interface ExpressionDetailClientProps {
  expressionId: number;
  initialExpression: ExpressionDetail;
}

/**
 * Normalizes authors to always be an array.
 * Handles cases where authors might be stored as a string instead of an array.
 *
 * @param authors - The authors value (string, array, or null/undefined)
 * @returns An array of author strings
 */
function normalizeAuthors(authors: unknown): string[] {
  if (!authors) return [];
  if (Array.isArray(authors)) return authors.filter(a => typeof a === "string");
  if (typeof authors === "string") return [authors];
  return [];
}

/**
 * Resolves an icon representing the physical format or content type.
 *
 * @param {string | null} [format] - Physical media format.
 * @param {string | null} [contentType] - FRBR content type.
 * @returns {JSX.Element} Lucide icon.
 */
function getFormatIcon(format?: string | null, contentType?: string | null) {
  const norm = (format || contentType || "").toLowerCase();
  if (norm.includes("audio") || norm.includes("music") || norm.includes("cd") || norm.includes("vinyl")) {
    return <Disc className="h-4 w-4" />;
  }
  if (
    norm.includes("movie") ||
    norm.includes("film") ||
    norm.includes("video") ||
    norm.includes("dvd") ||
    norm.includes("bluray")
  ) {
    return <Film className="h-4 w-4" />;
  }
  if (norm.includes("game")) {
    return <Gamepad2 className="h-4 w-4" />;
  }
  return <BookOpen className="h-4 w-4" />;
}

/**
 * Client component for rendering the detailed FRBR Expression view.
 *
 * @param {ExpressionDetailClientProps} props - Component properties.
 * @returns {JSX.Element} Interactive Expression detail UI.
 */
export function ExpressionDetailClient({ initialExpression }: ExpressionDetailClientProps) {
  const router = useRouter();
  const expr = initialExpression;

  const primaryCoverManifestation = (expr.manifestations || []).find(m => m.cover_url);
  const primaryCoverUrl = primaryCoverManifestation
    ? getCoverUrl(primaryCoverManifestation.cover_url || undefined)
    : undefined;

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Navbar />

      <main
        className="flex-1 pb-16"
        itemScope
        itemType="https://schema.org/CreativeWork"
        vocab="http://iflastandards.info/ns/frbr/frbrer/"
        typeof="Expression"
        resource={`#expression-${expr.id}`}
        prefix="schema: https://schema.org/ frbr: http://iflastandards.info/ns/frbr/frbrer/"
      >
        {/* Top bar navigation */}
        <div className="border-b border-border/60 bg-muted/20">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.back()}
              className="gap-2 text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Back</span>
            </Button>
            <Badge variant="outline" className="gap-1.5 px-3 py-1 font-mono text-xs uppercase tracking-wider">
              <Layers className="h-3 w-3 text-primary" />
              FRBR Expression #{expr.id}
            </Badge>
          </div>
        </div>

        {/* Hero Section */}
        <div className="border-b border-border/40 bg-gradient-to-b from-muted/30 to-background py-10 sm:py-14">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="flex flex-col gap-8 md:flex-row md:items-start">
              {/* Cover Artwork */}
              <div className="relative mx-auto h-64 w-48 shrink-0 overflow-hidden rounded-xl border border-border/60 bg-muted/40 shadow-md md:mx-0">
                {primaryCoverUrl ? (
                  <Image
                    src={primaryCoverUrl}
                    alt={expr.work_title}
                    fill
                    sizes="(max-width: 768px) 192px, 240px"
                    className="object-cover"
                    priority
                  />
                ) : (
                  <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-muted-foreground/60">
                    <Sparkles className="h-10 w-10 stroke-[1.5]" />
                    <span className="text-xs font-medium">Expression</span>
                  </div>
                )}
              </div>

              {/* Expression Metadata Header */}
              <div className="flex flex-1 flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant="secondary"
                    className="gap-1.5 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider"
                  >
                    <Layers className="h-3 w-3" />
                    FRBR Expression
                  </Badge>
                  {expr.language && (
                    <Badge variant="outline" className="text-xs uppercase">
                      {expr.language}
                    </Badge>
                  )}
                  {expr.is_live_performance && (
                    <Badge variant="secondary" className="gap-1 text-xs">
                      <Music className="h-3 w-3" />
                      Live Performance
                    </Badge>
                  )}
                </div>

                <h1
                  className="font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl"
                  property="schema:name"
                  itemProp="name"
                >
                  {expr.work_title}
                </h1>

                {/* Link to Conceptual Work */}
                <div className="text-sm font-medium text-muted-foreground">
                  <span>Part of Conceptual Work: </span>
                  <Link
                    href={`/work/${expr.work_id}`}
                    rel="expressionOf"
                    className="font-semibold text-foreground transition-colors hover:text-primary hover:underline"
                  >
                    {expr.work_title} &rarr;
                  </Link>
                </div>

                {normalizeAuthors(expr.authors).length > 0 && (
                  <div
                    className="flex flex-wrap items-center gap-1.5 text-base font-medium text-muted-foreground"
                    property="schema:author"
                    typeof="Person"
                    itemProp="author"
                    itemScope
                    itemType="https://schema.org/Person"
                  >
                    <span>By</span>
                    {normalizeAuthors(expr.authors).map((author, idx) => (
                      <span key={author} property="schema:name" itemProp="name">
                        <Link
                          href={`/collection?q=${encodeURIComponent(author)}`}
                          className="text-foreground transition-colors hover:text-primary hover:underline"
                        >
                          {author}
                        </Link>
                        {idx < expr.authors.length - 1 && <span className="text-muted-foreground/60">, </span>}
                      </span>
                    ))}
                  </div>
                )}

                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  This page represents an intellectual or artistic realization of the Work. Physical editions and
                  recordings embodying this expression are listed below.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Embodied Manifestations Section */}
        <div className="mx-auto max-w-6xl px-4 pt-10 sm:px-6">
          <h2 className="mb-6 font-serif text-xl font-bold text-foreground">
            Embodied Editions & Manifestations ({expr.manifestations ? expr.manifestations.length : 0})
          </h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {expr.manifestations && expr.manifestations.length > 0 ? (
              expr.manifestations.map(m => {
                const mSchemaType = resolveSchemaType(expr.content_type, expr.kind, m.format);
                const cover = getCoverUrl(m.cover_url || undefined);
                return (
                  <Link
                    key={m.id}
                    href={`/manifestation/${m.id}`}
                    className="group flex gap-4 rounded-lg border border-border/40 bg-card p-3 shadow-sm transition-all hover:border-primary/40 hover:bg-muted/40 hover:shadow-md"
                    itemProp="workExample"
                    itemScope
                    itemType={`https://schema.org/${mSchemaType}`}
                    typeof="Manifestation"
                    resource={`#manifestation-${m.id}`}
                  >
                    {/* Thumbnail */}
                    <div className="relative h-24 w-18 shrink-0 overflow-hidden rounded-md border border-border/60 bg-muted/40">
                      {cover ? (
                        <Image
                          src={cover}
                          alt={m.title || expr.work_title}
                          fill
                          sizes="72px"
                          className="object-cover transition-transform group-hover:scale-105"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-muted-foreground/50">
                          {getFormatIcon(m.format, expr.content_type)}
                        </div>
                      )}
                    </div>

                    {/* Details */}
                    <div className="flex flex-1 flex-col justify-between overflow-hidden">
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-muted-foreground">{getFormatIcon(m.format, expr.content_type)}</span>
                          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            {m.format || expr.content_type || "Edition"}
                          </span>
                        </div>
                        <h3
                          className="mt-1 line-clamp-2 text-sm font-semibold text-foreground group-hover:text-primary"
                          itemProp="name"
                        >
                          {m.title || expr.work_title}
                        </h3>
                      </div>

                      <div className="mt-2 text-xs text-muted-foreground">
                        {m.publisher && <div>{m.publisher}</div>}
                        <div className="flex items-center gap-2">
                          {m.year && <span itemProp="datePublished">{m.year}</span>}
                          {(m.isbn13 || m.ean) && (
                            <span className="font-mono text-[11px] text-muted-foreground/80">{m.isbn13 || m.ean}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                );
              })
            ) : (
              <p className="col-span-full py-8 text-center text-sm text-muted-foreground">
                No manifestations recorded for this expression.
              </p>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
