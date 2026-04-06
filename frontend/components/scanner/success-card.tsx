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
 * @param props.snappedCover - Optional file of a cover snapped from video
 * @returns {JSX.Element} The component
 */
export function SuccessCard({ isbn, meta, onDismiss, snappedCover }: SuccessCardProps) {
  const [adding, setAdding] = useState(false);
  const router = useRouter();

  // Normalize metadata for display
  const title = meta.title || meta.Title || meta.format || "Unknown Title";
  const authors = meta.authors || meta.Authors || (meta.author ? [meta.author] : []);
  const authorDisplay = authors.length > 0 ? authors.join(", ") : "Unknown Artist/Author";
  const coverUrl = meta.cover_url || "/file.svg";

  const format = (meta.format || meta.Format || "book").toLowerCase();
  const isAudio = isAudioMedia(format);
  const isVideo = format === "video" || format === "dvd" || format === "bluray";
  const isGame = format === "boardgame" || format === "game";
  
  const identifier = isbn || meta.barcode || meta.isbn || "No ID Available";
  const isMissingID = identifier === "No ID Available";

  // Extract extended meta attributes for video/games
  const extendedMeta = (meta as any).meta || {};
  const directors: string[] = (meta as any).directors || extendedMeta.directors || [];
  const cast: string[] = (meta as any).cast || extendedMeta.cast || [];
  const mechanics: string[] = (meta as any).game_mechanics || extendedMeta.game_mechanics || extendedMeta.Mechanics || [];

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
        barcode: identifier,
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
            <div className={`relative w-full md:w-1/3 shrink-0 rounded-xl overflow-hidden shadow-xl bg-muted ${isAudio ? 'aspect-square' : isVideo ? 'aspect-[2/3]' : 'aspect-[2/3]'}`}>
              {coverUrl && coverUrl !== "/file.svg" ? (
                <Image
                  src={coverUrl.startsWith("/static") ? `${process.env.NEXT_PUBLIC_API_URL || ""}${coverUrl}` : coverUrl}
                  alt={title}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 100vw, 33vw"
                  unoptimized={coverUrl.startsWith("http")}
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <div className="flex flex-col items-center gap-2 text-muted-foreground/40">
                    {isAudio ? <Disc className="h-12 w-12" /> : isVideo ? <Film className="h-12 w-12" /> : isGame ? <Gamepad2 className="h-12 w-12" /> : <BookOpen className="h-12 w-12" />}
                    <span className="text-xs font-bold uppercase tracking-widest font-serif">iQoQo</span>
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col flex-1 gap-4">
              <div className="space-y-2">
                <Badge variant="secondary" className="w-fit mb-2">
                  {formatDisplay}
                </Badge>
                <h3 className="text-2xl font-bold leading-tight font-serif text-foreground">{title}</h3>
                
                {authors.length > 0 && <p className="text-lg text-muted-foreground">{authorDisplay}</p>}
                
                {/* Extended Metadata Display */}
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
                  <strong>Warning:</strong> No standard ISBN/Barcode found. You can still add this to your collection, but manual cleanup may be required.
                </div>
              )}

              <div className="grid grid-cols-2 gap-y-3 text-sm mt-2 p-4 bg-muted/30 rounded-xl border border-border/50">
                <div className="text-muted-foreground font-semibold flex items-center gap-2">
                  Identifier
                </div>
                <div className="font-mono text-xs break-all">{identifier}</div>
                {format && (
                  <>
                  <div className="text-muted-foreground font-semibold">Format</div>
                  <div>{format.toUpperCase()}</div>
                  </>
                )}
              </div>

              <div className="flex flex-col sm:flex-row gap-3 mt-auto pt-6 flex-wrap">
                 <Button
                   className="flex-1 min-w-[140px] h-12 rounded-xl shadow-lg shadow-primary/20"
                   variant="default"
                   disabled={adding}
                   onClick={handleAdd}
                   aria-label="Add to Collection"
                 >
                   {adding ? (
                     "Adding..."
                   ) : (
                     <>
                       <Plus className="w-4 h-4 mr-2" strokeWidth={3} />
                       Add to Collection
                     </>
                   )}
                 </Button>
                 <Button
                   variant="outline"
                   className="flex-1 min-w-[140px] h-12 rounded-xl"
                   onClick={onDismiss}
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
