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

import { useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import { BookOpen, Loader2, Disc } from "lucide-react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { useManifestation, useProfile, useWorkParts } from "@/lib/api/hooks";
import { getCoverUrl, getCoverTimestamp } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { CatalogEntry } from "@/types/frbr";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { ManifestationActions } from "@/components/manifestation/manifestation-actions";
import { AddToCollectionDropdown } from "@/components/collection/add-to-collection-dropdown";
import { CameraCapture } from "@/components/scanner/camera-capture";
import { ImagePlus } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { FRBRFeedback } from "@/components/social/frbr-feedback";
import { ExtendedMetadata } from "@/components/item/extended-metadata";
import { CoverProvenance } from "@/components/cover/cover-provenance";
import { useTranslations } from "next-intl";

/**
 * Page displaying a single manifestation with metadata and add-to-collection action.
 *
 * @returns {JSX.Element}
 */
export default function ManifestationPage() {
  const t = useTranslations("Manifestation");
  const params = useParams();
  const manifestationId = Number(params?.id);

  const { data: userProfile } = useProfile();
  const { data: manifestation, isLoading, isError } = useManifestation(manifestationId);
  const { data: partsResponse } = useWorkParts(manifestation?.container_work_id ?? manifestation?.work_id ?? 0);
  const parts = partsResponse?.data ?? [];
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
        <Footer />
      </div>
    );
  }

  if (isError || !manifestation) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-muted-foreground">{t("notFound")}</p>
        </div>
        <Footer />
      </div>
    );
  }

  const timestamp = getCoverTimestamp(manifestation.meta);
  const coverUrl =
    getCoverUrl(manifestation.cover_url || undefined, timestamp) ||
    (manifestation.meta?.["cover_url"] as string | undefined);
  const resolved_year = manifestation.year || manifestation.meta?.Year || manifestation.meta?.year;

  const isSeries = parts.length > 0;
  const childCovers = parts.map(p => p.cover_url).filter(Boolean) as string[];

  const format =
    (manifestation.meta?.format as string | undefined) || (manifestation.meta?.Format as string | undefined) || "book";
  const isAudio =
    manifestation.content_type === "audiobook" ||
    manifestation.content_type === "music" ||
    format.toLowerCase() === "cd" ||
    format.toLowerCase() === "vinyl" ||
    format.toLowerCase() === "audiobook_cd";

  // Resolve special series label
  const contentType = manifestation.content_type ?? "text";
  let baseLabel = t("book");
  if (contentType === "movie") baseLabel = t("movie");
  else if (contentType === "music") baseLabel = t("music");
  else if (contentType === "board_game" || contentType === "puzzle") baseLabel = t("game");

  const badgeLabel = isSeries ? t("seriesSuffix", { label: baseLabel }) : isAudio ? t("cdAudio") : t("book");

  const isBoardGame = manifestation.content_type === "board_game";
  const schemaType = isBoardGame ? "Game" : "Book";

  const jsonLdData = {
    "@context": "https://schema.org",
    "@type": schemaType,
    name: manifestation.title || "Untitled Work",
    author: {
      "@type": "Person",
      name: manifestation.authors?.[0] || "Unknown Author",
    },
    isbn: manifestation.isbn13,
    identifier: manifestation.id,
    publisher: manifestation.meta?.Publisher,
    datePublished: resolved_year,
  };

  const resolvedIsbn =
    (manifestation.isbn13 || "").trim() ||
    (manifestation.meta?.isbn as string | undefined) ||
    (manifestation.meta?.isbn13 as string | undefined);
  const resolvedEan =
    (manifestation.ean || "").trim() ||
    (manifestation.meta?.ean as string | undefined) ||
    (manifestation.meta?.barcode as string | undefined);
  const resolvedUpc = (manifestation.upc || "").trim() || (manifestation.meta?.upc as string | undefined);
  const tags = (manifestation.meta?.tags || manifestation.meta?.genres || []) as string[];

  return (
    <div
      className="min-h-screen flex flex-col bg-background"
      vocab="http://iflastandards.info/ns/frbr/frbrer/"
      prefix="sioc: http://rdfs.org/sioc/ns# schema: https://schema.org/"
      typeof="Manifestation"
      resource={`#manifestation-${manifestation.id}`}
    >
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdData) }} />
      <Navbar />
      <div className="flex-1 mx-auto w-full max-w-5xl px-6 py-12">
        <div className="flex flex-col md:flex-row gap-8">
          {/* Cover Art */}
          <div className="w-full md:w-1/3 max-w-sm mx-auto">
            <div className="relative aspect-[2/3] w-full overflow-hidden rounded-xl border border-border bg-secondary shadow-lg">
              {coverUrl && manifestation.meta?.format !== "series" && manifestation.meta?.format !== "Series" ? (
                <Image
                  src={coverUrl}
                  alt={`Cover of ${manifestation.title}`}
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  unoptimized
                  priority
                  className="object-cover"
                />
              ) : childCovers.length > 0 ? (
                <div className="grid grid-cols-2 grid-rows-2 h-full w-full gap-0.5 bg-background">
                  {childCovers.slice(0, 4).map((url, idx) => (
                    <div key={url + idx} className="relative h-full w-full">
                      <Image src={url} alt={`Collage Part ${idx + 1}`} fill className="object-cover" unoptimized />
                    </div>
                  ))}
                  {childCovers.length < 4 &&
                    Array.from({ length: 4 - childCovers.length }).map((_, idx) => (
                      <div
                        key={`empty-${idx}`}
                        className="flex h-full w-full items-center justify-center bg-muted text-muted-foreground/30"
                      >
                        <BookOpen className="h-6 w-6" />
                      </div>
                    ))}
                </div>
              ) : coverUrl ? (
                <Image
                  src={coverUrl}
                  alt={`Cover of ${manifestation.title}`}
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  unoptimized
                  priority
                  className="object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <BookOpen className="h-24 w-24 text-muted-foreground/30" />
                </div>
              )}
            </div>
            <div className="mt-2.5 flex justify-center">
              <CoverProvenance source={manifestation.meta?.["cover_source"] as string | undefined} />
            </div>
            {!coverUrl && (
              <div className="mt-4">
                <CameraCapture
                  manifestation_id={manifestation.id}
                  format={(manifestation.meta?.format as "book" | "cd" | "vinyl") || "book"}
                  onUploadComplete={() => {
                    toast.success(t("coverContributed"));
                    router.refresh();
                  }}
                  label={t("contributeCover")}
                  icon={<ImagePlus className="mr-2 h-4 w-4" />}
                  className="[&>button]:w-full [&>button]:rounded-xl [&>button]:py-6"
                />
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className="flex-1 space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Badge
                  variant={isSeries ? "default" : isAudio ? "secondary" : "outline"}
                  className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold uppercase tracking-wider"
                >
                  {isAudio ? <Disc className="h-3 w-3" /> : <BookOpen className="h-3 w-3" />}
                  {badgeLabel}
                </Badge>
              </div>
              <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground" property="schema:name">
                {manifestation.title || "Untitled Work"}
              </h1>
              <div
                className="mt-2 flex flex-wrap items-center gap-1 text-xl text-muted-foreground font-medium"
                property="schema:author"
                typeof="Person"
              >
                {(manifestation.authors ?? []).length > 0 ? (
                  (manifestation.authors ?? []).map((author, idx, arr) => (
                    <span key={author} property="schema:name">
                      <span
                        role="button"
                        tabIndex={0}
                        onClick={() => router.push(`/collection?q=${encodeURIComponent(author)}`)}
                        onKeyDown={e => e.key === "Enter" && router.push(`/collection?q=${encodeURIComponent(author)}`)}
                        className="hover:text-primary hover:underline cursor-pointer transition-colors"
                        title={t("browseAuthor", { author })}
                      >
                        {author}
                      </span>
                      {idx < arr.length - 1 && <span className="text-muted-foreground/60">,&nbsp;</span>}
                    </span>
                  ))
                ) : (
                  <span>{t("unknownAuthor")}</span>
                )}
              </div>
            </div>

            <div className="space-y-3 pt-6 border-t border-border">
              <h2 className="text-lg font-semibold">{t("pubDetails")}</h2>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3 text-sm">
                {resolvedIsbn && (
                  <div>
                    <dt className="text-muted-foreground">{t("isbn13")}</dt>
                    <dd className="font-medium text-foreground" property="schema:isbn">
                      {String(resolvedIsbn)}
                    </dd>
                  </div>
                )}
                {resolvedEan && (
                  <div>
                    <dt className="text-muted-foreground">{t("ean")}</dt>
                    <dd className="font-medium text-foreground">{String(resolvedEan)}</dd>
                  </div>
                )}
                {resolvedUpc && (
                  <div>
                    <dt className="text-muted-foreground">{t("upc")}</dt>
                    <dd className="font-medium text-foreground">{String(resolvedUpc)}</dd>
                  </div>
                )}
                {manifestation.work_id && (
                  <a rel="embodimentOf" href={`/api/public/works/${manifestation.work_id}`} className="hidden" />
                )}
                {!!(
                  manifestation.meta?.Publisher &&
                  manifestation.meta.Publisher !== "Unknown" &&
                  manifestation.meta.Publisher !== "N/A"
                ) && (
                  <div>
                    <dt className="text-muted-foreground">{t("publisher")}</dt>
                    <dd className="font-medium text-foreground">{String(manifestation.meta.Publisher)}</dd>
                  </div>
                )}
                {!!(resolved_year && resolved_year !== "Unknown" && resolved_year !== "N/A") && (
                  <div>
                    <dt className="text-muted-foreground">{t("year")}</dt>
                    <dd className="font-medium text-foreground">{String(resolved_year)}</dd>
                  </div>
                )}
                {!!(
                  manifestation.meta?.Language &&
                  manifestation.meta.Language !== "Unknown" &&
                  manifestation.meta.Language !== "N/A"
                ) && (
                  <div>
                    <dt className="text-muted-foreground">{t("language")}</dt>
                    <dd className="font-medium text-foreground">{String(manifestation.meta.Language)}</dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Rich metadata including audio tracklists and descriptions */}
            <div className="pt-6 border-t border-border">
              <ExtendedMetadata meta={manifestation.meta ?? {}} owner_count={manifestation.owner_count} />
            </div>

            {tags.length > 0 && (
              <div className="pt-6 border-t border-border space-y-3">
                <h2 className="text-lg font-semibold">{t("indexedTags")}</h2>
                <div className="flex flex-wrap gap-2">
                  {tags.map((tag: string) => (
                    <span
                      key={tag}
                      property="sioc:topic"
                      content={tag}
                      className="inline-flex items-center rounded-md bg-orange-50 px-2 py-1 text-xs font-medium text-orange-700 ring-1 ring-inset ring-orange-600/10 dark:bg-orange-400/10 dark:text-orange-400 dark:ring-orange-400/20"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(manifestation.container_work_id || parts.length > 0) && parts.length > 0 && (
              <div className="pt-6 border-t border-border space-y-3">
                <h2 className="text-lg font-semibold">{t("seriesComplexParts")}</h2>
                <div className="border border-border/60 rounded-xl divide-y bg-muted/5 overflow-hidden">
                  {parts.map(part => {
                    const isCurrent = part.part_work_id === manifestation.work_id;
                    const isLinkable = !!(part.item_id || part.manifestation_id);
                    const linkUrl = part.item_id ? `/item/${part.item_id}` : `/manifestation/${part.manifestation_id}`;

                    const content = (
                      <div className="flex items-center gap-3">
                        <span
                          className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                            isCurrent ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {part.sequence}
                        </span>
                        {part.cover_url ? (
                          <div className="relative h-12 w-8 shrink-0 overflow-hidden rounded-md border border-border/80 bg-secondary shadow-sm">
                            <Image
                              src={part.cover_url}
                              alt={`Cover of ${part.title}`}
                              fill
                              sizes="32px"
                              className="object-cover"
                              unoptimized
                            />
                          </div>
                        ) : (
                          <div className="flex h-12 w-8 shrink-0 items-center justify-center rounded-md border border-border/80 bg-muted text-muted-foreground/30 shadow-sm">
                            <BookOpen className="h-4 w-4" />
                          </div>
                        )}
                        <span
                          className={
                            isCurrent
                              ? "text-primary font-semibold"
                              : "text-foreground hover:text-primary transition-colors"
                          }
                        >
                          {part.title}
                        </span>
                      </div>
                    );

                    return (
                      <div
                        key={part.part_work_id}
                        className={`flex items-center justify-between p-3 text-sm transition-all duration-200 ${
                          isCurrent ? "bg-primary/5 font-semibold" : "hover:bg-muted/40"
                        }`}
                      >
                        {isLinkable ? (
                          <Link href={linkUrl} className="flex-1">
                            {content}
                          </Link>
                        ) : (
                          <div className="flex-1">{content}</div>
                        )}
                        <div className="flex items-center gap-2">
                          {part.item_id && (
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-green-600 dark:text-green-400 px-2 py-0.5 rounded-full bg-green-500/10">
                              {t("inCollection")}
                            </span>
                          )}
                          {isCurrent && (
                            <span className="text-xs font-semibold uppercase tracking-wider text-primary px-2 py-0.5 rounded-full bg-primary/10">
                              {t("currentEdition")}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {userProfile && (
              <div className="pt-6 space-y-4">
                <div className="flex flex-col items-start gap-2">
                  <div>
                    {manifestation.user_owns ? (
                      <div className="flex flex-wrap gap-2">
                        {manifestation.item_id && (
                          <Button onClick={() => router.push(`/item/${manifestation.item_id}`)} size="sm">
                            <BookOpen className="mr-2 h-4 w-4" />
                            {t("viewMyItem")}
                          </Button>
                        )}
                        <Button
                          onClick={() =>
                            router.push(
                              `/collection?view=items&q=${encodeURIComponent(
                                manifestation.isbn13 || manifestation.title || ""
                              )}`
                            )
                          }
                          variant="secondary"
                          size="sm"
                        >
                          {t("viewInCollection")}
                        </Button>
                      </div>
                    ) : (
                      <AddToCollectionDropdown
                        manifestationId={manifestation.id}
                        wishlistItemId={manifestation.wishlist_item_id}
                      />
                    )}
                  </div>
                  {manifestation.owner_count !== undefined && manifestation.owner_count > 0 && (
                    <span className="text-xs text-muted-foreground">
                      {manifestation.owner_count === 1
                        ? t.rich("ownedByOne", {
                            count: manifestation.owner_count,
                            bold: chunks => <strong className="text-foreground">{chunks}</strong>,
                          })
                        : t.rich("ownedByMultiple", {
                            count: manifestation.owner_count,
                            bold: chunks => <strong className="text-foreground">{chunks}</strong>,
                          })}
                    </span>
                  )}
                </div>

                {/* Admin Actions extracted to standalone component */}
                <ManifestationActions manifestation={manifestation} />
              </div>
            )}
          </div>
        </div>

        {/* Reviews Section */}
        <ManifestationReviews manifestation={manifestation} />
      </div>
      <Footer />
    </div>
  );
}

/**
 * Renders the reviews section for a manifestation, supporting Work, Expression, and Manifestation levels.
 *
 * @param props - Component props.
 * @param props.manifestation - The catalog entry to display reviews for.
 * @returns The rendered manifestation reviews tab.
 */
function ManifestationReviews({ manifestation }: { manifestation: CatalogEntry }) {
  const t = useTranslations("Manifestation");
  const [activeLevel, setActiveLevel] = useState<"work" | "expression" | "manifestation">("work");

  const subtabs = [
    { id: "work", label: t("tabWork"), targetId: manifestation.work_id, description: t("descWork") },
    {
      id: "expression",
      label: t("tabExpression"),
      targetId: manifestation.expression_id,
      description: t("descExpression"),
    },
    { id: "manifestation", label: t("tabEdition"), targetId: manifestation.id, description: t("descEdition") },
  ] as const;

  return (
    <div className="mt-12 border-t pt-10 space-y-6">
      <h3 className="font-serif text-2xl font-bold text-foreground">{t("reviewsFeedback")}</h3>
      <div className="overflow-hidden rounded-xl bg-card border p-6 shadow-sm">
        <div className="flex flex-wrap gap-2 border-b pb-4 mb-6">
          {subtabs.map(({ id, label, targetId, description }) => {
            if (!targetId) return null;
            const isSelected = activeLevel === id;
            return (
              <button
                key={id}
                onClick={() => setActiveLevel(id)}
                className={`flex flex-col items-start gap-0.5 rounded-xl border px-4 py-2.5 text-left transition-all cursor-pointer ${
                  isSelected
                    ? "border-primary bg-primary/5 text-primary shadow-sm"
                    : "border-border/60 hover:bg-muted/30 text-muted-foreground hover:text-foreground"
                }`}
              >
                <span className="text-xs font-bold leading-none">{label}</span>
                <span className="text-[10px] text-muted-foreground/80 leading-none mt-1">{description}</span>
              </button>
            );
          })}
        </div>

        <div>
          {activeLevel === "work" && manifestation.work_id && (
            <FRBRFeedback level="work" targetId={manifestation.work_id} title={t("feedbackTitleWork")} />
          )}
          {activeLevel === "expression" && manifestation.expression_id && (
            <FRBRFeedback
              level="expression"
              targetId={manifestation.expression_id}
              title={t("feedbackTitleExpression")}
            />
          )}
          {activeLevel === "manifestation" && (
            <FRBRFeedback level="manifestation" targetId={manifestation.id} title={t("feedbackTitleManifestation")} />
          )}
        </div>
      </div>
    </div>
  );
}
