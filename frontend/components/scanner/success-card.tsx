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
import Image from "next/image";
import { Check, X, Plus, Disc, BookOpen, Film, Gamepad2 } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import type { IsbnMeta, ApiResponse } from "@/types/frbr";
import { apiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { isAudioMedia } from "@/lib/utils";

interface SuccessCardProps {
  isbn: string;
  meta: IsbnMeta;
  onDismiss: () => void;
  onScanAnother?: () => void;
  snappedCover?: File | null;
}

/**
 * SuccessCard component shown after a successful scan.
 * Displays item metadata and provides an option to add it to the library.
 *
 * @param props - Component props
 * @param props.isbn - The barcode that was scanned
 * @param props.meta - The metadata found for the barcode
 * @param props.onDismiss - Function to call when the card is dismissed
 * @param props.onScanAnother - Optional function for rapid sequential scanning
 * @param props.snappedCover - Optional file of a cover snapped from video
 * @returns {JSX.Element} The component
 */
export function SuccessCard({ isbn, meta, onDismiss, onScanAnother, snappedCover }: SuccessCardProps) {
  const normalizeFormat = (f: string): string => {
    const low = f.toLowerCase();
    if (["book", "text", "standard"].includes(low)) return "book";
    if (["video", "dvd", "bluray", "movie", "moving image"].includes(low)) return "video";
    if (["audio", "cd", "vinyl", "sound", "lp", "music"].includes(low)) {
      if (low === "vinyl" || low === "lp") return "vinyl";
      if (low === "cd") return "cd";
      return "audio";
    }
    if (["game", "boardgame"].includes(low)) return "boardgame";
    if (["puzzle", "jigsaw"].includes(low)) return "puzzle";
    return "book"; // Default fallback
  };

  const [adding, setAdding] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState(normalizeFormat(meta.format || meta.Format || "book"));
  const router = useRouter();

  // Normalize metadata for display
  const title = meta.title || meta.Title || meta.format || "Unknown Title";
  const authors = meta.authors || meta.Authors || (meta.author ? [meta.author] : []);
  const authorDisplay = authors.length > 0 ? authors.join(", ") : "Unknown Artist/Author";
  const coverUrl = meta.cover_url || "/file.svg";

  const format = selectedFormat;
  const isAudio = isAudioMedia(format);
  const isVideo = ["video", "dvd", "bluray", "moving image"].includes(format);
  const isGame = ["boardgame", "game"].includes(format);

  // Derive stable identifier: prefer meta fields from backend over raw scan prop
  const canonicalIdentifier = meta.identifier || meta.barcode || meta.isbn;
  const rawIdentifier = canonicalIdentifier || isbn || "";
  const isBarcodelike = /^[\dX]{8,14}$/.test(rawIdentifier.trim());
  const identifier = isBarcodelike ? rawIdentifier : meta.discogs_id ? `Discogs #${meta.discogs_id}` : "";
  // Relax missing ID check if we already have a manifestation_id from the backend lookup
  const isMissingID = !identifier && !meta.manifestation_id;

  // Extract extended meta attributes for video/games
  const extendedMeta = (meta.meta as Record<string, unknown>) || {};
  const directors: string[] = Array.isArray(meta.directors)
    ? meta.directors
    : Array.isArray(extendedMeta.directors)
      ? extendedMeta.directors
      : [];
  const cast: string[] = Array.isArray(meta.cast)
    ? meta.cast
    : Array.isArray(extendedMeta.cast)
      ? extendedMeta.cast
      : [];
  const mechanics: string[] = Array.isArray(meta.game_mechanics)
    ? meta.game_mechanics
    : Array.isArray(extendedMeta.game_mechanics)
      ? extendedMeta.game_mechanics
      : Array.isArray(extendedMeta.mechanics)
        ? extendedMeta.mechanics
        : [];
  // Player count for board games
  const minPlayers =
    meta.min_players ??
    (extendedMeta.min_players as number | undefined) ??
    (extendedMeta.minPlayers as number | undefined);
  const maxPlayers =
    meta.max_players ??
    (extendedMeta.max_players as number | undefined) ??
    (extendedMeta.maxPlayers as number | undefined);
  const playerCountDisplay =
    minPlayers && maxPlayers ? `${minPlayers}-${maxPlayers} players` : minPlayers ? `${minPlayers}+ players` : null;
  // Runtime for video
  const runtime =
    meta.runtime ?? (extendedMeta.runtime as number | undefined) ?? (extendedMeta.Runtime as number | undefined);

  let formatDisplay = "Book / Text";
  if (isVideo) formatDisplay = "Video Media";
  if (isAudio) formatDisplay = "Audio Media";
  if (isGame) formatDisplay = "Board Game";

  const handleAdd = async () => {
    if (isMissingID) {
      toast.error("Standard barcode required to add to collection.");
      return;
    }
    setAdding(true);
    try {
      const res = await apiClient.post<ApiResponse<{ item_id: number; manifestation_id: number }>>("/scan", {
        barcode: identifier || rawIdentifier,
        manifestation_id: meta.manifestation_id,
        format: format,
      });

      const responseData = res.data;
      if (!responseData.success || !responseData.data) {
        throw new Error(responseData.error || "Failed to ingest item");
      }

      const data = responseData.data;

      if (snappedCover && data.manifestation_id) {
        const coverFormData = new FormData();
        coverFormData.append("cover", snappedCover);
        try {
          await apiClient.post(`/manifestations/${data.manifestation_id}/cover`, coverFormData, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          toast.success(`"${title}" added with your custom cover!`);
        } catch (e) {
          console.error("Failed to upload snapped cover:", e);
          toast.warning(`"${title}" added, but cover upload failed.`);
        }
      } else {
        toast.success(`"${title}" added to your library!`);
      }

      if (data.item_id) {
        router.push(`/item/${data.item_id}`);
      } else {
        onDismiss();
      }
    } catch (e) {
      toast.error((e as Error).message ?? "Failed to add item");
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="absolute inset-x-0 bottom-0 z-30 animate-[slide-up_0.4s_cubic-bezier(0.16,1,0.3,1)_forwards] p-4 sm:p-6 lg:p-8">
      <Card className="w-full max-w-2xl mx-auto overflow-hidden shadow-2xl border-green-500/30 bg-card/95 backdrop-blur-md">
        <CardHeader className="bg-green-500/10 py-3 flex flex-row items-center justify-between">
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-500/20">
              <Check className="h-5 w-5" />
            </div>
            <h2 className="text-xl font-bold font-serif">Successfully Found!</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onDismiss} className="rounded-full" aria-label="Close">
            <X className="h-5 w-5" />
          </Button>
        </CardHeader>

        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row gap-6">
            {/* Dynamic Cover Art Aspect Ratio */}
            <div
              className={`relative w-full md:w-1/3 shrink-0 rounded-xl overflow-hidden shadow-xl bg-muted ${isAudio ? "aspect-square" : isVideo ? "aspect-[2/3]" : "aspect-[2/3]"}`}
            >
              {coverUrl && coverUrl !== "/file.svg" ? (
                <Image
                  src={
                    coverUrl.startsWith("/static") ? `${process.env.NEXT_PUBLIC_API_URL || ""}${coverUrl}` : coverUrl
                  }
                  alt={title}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 100vw, 33vw"
                  unoptimized
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <div className="flex flex-col items-center gap-2 text-muted-foreground/40">
                    {isAudio ? (
                      <Disc className="h-12 w-12" />
                    ) : isVideo ? (
                      <Film className="h-12 w-12" />
                    ) : isGame ? (
                      <Gamepad2 className="h-12 w-12" />
                    ) : (
                      <BookOpen className="h-12 w-12" />
                    )}
                    <span className="text-xs font-bold uppercase tracking-widest font-serif">iQoQo</span>
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col flex-1 gap-4">
              <div className="space-y-2">
                <Badge variant="secondary" className="w-fit mb-2">
                  {formatDisplay}
                  {/* Hidden uppercase label for legacy test support */}
                  <span className="sr-only">{format.toUpperCase()}</span>
                </Badge>
                <h3 className="text-2xl font-bold leading-tight font-serif text-foreground">{title}</h3>

                {authors.length > 0 && <p className="text-lg text-muted-foreground">{authorDisplay}</p>}

                {/* Extended Metadata Display */}
                {playerCountDisplay && (
                  <p className="text-sm text-muted-foreground">
                    <span className="font-semibold text-foreground">Players:</span> {playerCountDisplay}
                  </p>
                )}
                {runtime && (
                  <p className="text-sm text-muted-foreground">
                    <span className="font-semibold text-foreground">Runtime:</span> {runtime} min
                  </p>
                )}
                {directors.length > 0 && (
                  <p className="text-sm text-muted-foreground">
                    <span className="font-semibold text-foreground">Director:</span> {directors.join(", ")}
                  </p>
                )}
                {cast.length > 0 && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    <span className="font-semibold text-foreground">Cast:</span> {cast.join(", ")}
                  </p>
                )}
                {mechanics.length > 0 && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    <span className="font-semibold text-foreground">Mechanics:</span> {mechanics.join(", ")}
                  </p>
                )}
              </div>

              {isMissingID && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-600 dark:text-amber-400">
                  <strong>Warning:</strong> No standard ISBN/Barcode found. You can still add this to your collection,
                  but manual cleanup may be required.
                </div>
              )}

              <div className="grid grid-cols-2 gap-y-3 text-sm mt-2 p-4 bg-muted/30 rounded-xl border border-border/50">
                {identifier && (
                  <>
                    <div className="text-muted-foreground font-semibold flex items-center gap-2">Identifier</div>
                    <div className="font-mono text-xs break-all">{identifier}</div>
                  </>
                )}
                <div className="text-muted-foreground font-semibold flex items-center">Format</div>
                <div>
                  <select
                    value={format}
                    onChange={e => setSelectedFormat(e.target.value)}
                    className="h-8 w-full bg-transparent text-sm font-normal focus:outline-none cursor-pointer hover:text-primary transition-colors appearance-none"
                  >
                    <option value="book">Book / Text</option>
                    <option value="cd">Audio CD</option>
                    <option value="vinyl">Vinyl Record</option>
                    <option value="audio">Generic Audio</option>
                    <option value="video">Video / Movie</option>
                    <option value="boardgame">Board Game</option>
                    <option value="puzzle">Jigsaw Puzzle</option>
                  </select>
                </div>
              </div>

              {meta.already_in_collection && (
                <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-xs text-green-600 dark:text-green-400 font-semibold flex items-center gap-2">
                  <Check className="h-4 w-4" />
                  Already in your collection
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-3 mt-auto pt-6 flex-wrap">
                {meta.already_in_collection ? (
                  <Button
                    className="flex-1 min-w-[140px] h-12 rounded-xl shadow-lg shadow-primary/20"
                    variant="default"
                    onClick={() => meta.item_id && router.push(`/item/${meta.item_id}`)}
                  >
                    View in Collection
                  </Button>
                ) : (
                  <Button
                    className="flex-1 min-w-[140px] h-12 rounded-xl shadow-lg shadow-primary/20"
                    variant="default"
                    disabled={adding}
                    onClick={handleAdd}
                  >
                    {adding ? (
                      "Adding..."
                    ) : (
                      <>
                        <Plus className="w-4 h-4 mr-2" strokeWidth={3} />
                        Add to My Collection
                      </>
                    )}
                  </Button>
                )}
                <Button
                  variant="outline"
                  className="flex-1 min-w-[140px] h-12 rounded-xl"
                  onClick={onScanAnother ?? onDismiss}
                  aria-label="Scan Another"
                >
                  Scan Another
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
