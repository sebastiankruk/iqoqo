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

import { useParams } from "next/navigation";
import Image from "next/image";
import { BookOpen, Loader2, Disc } from "lucide-react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { useManifestation, useProfile, useWorkParts } from "@/lib/api/hooks";
import { getCoverUrl, getCoverTimestamp } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { ManifestationActions } from "@/components/manifestation/manifestation-actions";
import { AddToCollectionDropdown } from "@/components/collection/add-to-collection-dropdown";
import { CameraCapture } from "@/components/scanner/camera-capture";
import { ImagePlus } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

/**
 * Page displaying a single manifestation with metadata and add-to-collection action.
 *
 * @returns {JSX.Element}
 */
export default function ManifestationPage() {
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
          <p className="text-muted-foreground">Manifestation not found.</p>
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
  let baseLabel = "Book";
  if (contentType === "movie") baseLabel = "Movie";
  else if (contentType === "music") baseLabel = "Music";
  else if (contentType === "board_game" || contentType === "puzzle") baseLabel = "Game";

  const badgeLabel = isSeries ? `${baseLabel} (Series)` : isAudio ? "CD / Audio" : "Book";

  return (
    <div className="min-h-screen flex flex-col bg-background">
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
            {!coverUrl && (
              <div className="mt-4">
                <CameraCapture
                  manifestation_id={manifestation.id}
                  format={(manifestation.meta?.format as "book" | "cd" | "vinyl") || "book"}
                  onUploadComplete={() => {
                    toast.success("Cover contributed! Processing started.");
                    router.refresh();
                  }}
                  label="Contribute Cover"
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
              <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
                {manifestation.title || "Untitled Work"}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-1 text-xl text-muted-foreground font-medium">
                {(manifestation.authors ?? []).length > 0 ? (
                  (manifestation.authors ?? []).map((author, idx, arr) => (
                    <span key={author}>
                      <span
                        role="button"
                        tabIndex={0}
                        onClick={() => router.push(`/collection?q=${encodeURIComponent(author)}`)}
                        onKeyDown={e => e.key === "Enter" && router.push(`/collection?q=${encodeURIComponent(author)}`)}
                        className="hover:text-primary hover:underline cursor-pointer transition-colors"
                        title={`Browse all works by ${author}`}
                      >
                        {author}
                      </span>
                      {idx < arr.length - 1 && <span className="text-muted-foreground/60">,&nbsp;</span>}
                    </span>
                  ))
                ) : (
                  <span>Unknown Author</span>
                )}
              </div>
            </div>

            <div className="space-y-3 pt-6 border-t border-border">
              <h2 className="text-lg font-semibold">Publication Details</h2>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3 text-sm">
                {manifestation.isbn13 && (
                  <div>
                    <dt className="text-muted-foreground">ISBN-13</dt>
                    <dd className="font-medium text-foreground">{String(manifestation.isbn13)}</dd>
                  </div>
                )}
                {!!(
                  manifestation.meta?.Publisher &&
                  manifestation.meta.Publisher !== "Unknown" &&
                  manifestation.meta.Publisher !== "N/A"
                ) && (
                  <div>
                    <dt className="text-muted-foreground">Publisher</dt>
                    <dd className="font-medium text-foreground">{String(manifestation.meta.Publisher)}</dd>
                  </div>
                )}
                {!!(resolved_year && resolved_year !== "Unknown" && resolved_year !== "N/A") && (
                  <div>
                    <dt className="text-muted-foreground">Year</dt>
                    <dd className="font-medium text-foreground">{String(resolved_year)}</dd>
                  </div>
                )}
                {!!(
                  manifestation.meta?.Language &&
                  manifestation.meta.Language !== "Unknown" &&
                  manifestation.meta.Language !== "N/A"
                ) && (
                  <div>
                    <dt className="text-muted-foreground">Language</dt>
                    <dd className="font-medium text-foreground">{String(manifestation.meta.Language)}</dd>
                  </div>
                )}
              </dl>
            </div>

            {(manifestation.container_work_id || parts.length > 0) && parts.length > 0 && (
              <div className="pt-6 border-t border-border space-y-3">
                <h2 className="text-lg font-semibold">Series / Complex Work Parts</h2>
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
                              In Collection
                            </span>
                          )}
                          {isCurrent && (
                            <span className="text-xs font-semibold uppercase tracking-wider text-primary px-2 py-0.5 rounded-full bg-primary/10">
                              Current Edition
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
                            View My Item
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
                          View in Collection
                        </Button>
                      </div>
                    ) : (
                      <AddToCollectionDropdown manifestationId={manifestation.id} />
                    )}
                  </div>
                  {manifestation.owner_count !== undefined && manifestation.owner_count > 0 && (
                    <span className="text-xs text-muted-foreground">
                      Owned by <strong className="text-foreground">{manifestation.owner_count}</strong>{" "}
                      {manifestation.owner_count === 1 ? "person" : "people"}
                    </span>
                  )}
                </div>

                {/* Admin Actions extracted to standalone component */}
                <ManifestationActions manifestation={manifestation} />
              </div>
            )}
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
