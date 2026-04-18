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

import Image from "next/image";
import { X, ChevronRight, Disc, BookOpen, Film, Gamepad2 } from "lucide-react";
import type { IsbnMeta } from "@/types/frbr";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { isAudioMedia } from "@/lib/utils";

interface DisambiguationSheetProps {
  candidates: IsbnMeta[];
  onSelect: (choice: IsbnMeta) => void;
  onDismiss: () => void;
}

/**
 * DisambiguationSheet component shown when multiple potential matches are found.
 *
 * @param props - Component props
 * @param props.candidates - List of metadata candidates to choose from
 * @param props.onSelect - Function to call when a candidate is selected
 * @param props.onDismiss - Function to call when the sheet is dismissed
 * @returns {JSX.Element} The component
 */
export function DisambiguationSheet({ candidates, onSelect, onDismiss }: DisambiguationSheetProps) {
  return (
    <div className="absolute inset-x-0 bottom-0 z-40 animate-[slide-up_0.4s_cubic-bezier(0.16,1,0.3,1)_forwards] p-4 sm:p-6 lg:p-8">
      <Card className="w-full max-w-xl mx-auto overflow-hidden shadow-2xl border-primary/30 bg-card/95 backdrop-blur-md">
        <div className="flex items-center justify-between border-b border-border bg-muted/50 px-6 py-4">
          <h2 className="text-lg font-bold font-serif text-foreground">Which one did you mean?</h2>
          <Button variant="ghost" size="icon" onClick={onDismiss} className="rounded-full">
            <X className="h-5 w-5" />
          </Button>
        </div>

        <CardContent className="p-0 max-h-[60vh] overflow-y-auto">
          <div className="divide-y divide-border">
            {candidates.map((cand, idx) => {
              const format = (cand.format || cand.Format || "book").toLowerCase();
              const isAudio = isAudioMedia(format);
              const isVideo = ["video", "dvd", "bluray"].includes(format);
              const isGame = ["boardgame", "game"].includes(format);

              const title = cand.title || cand.Title || "Unknown Title";
              const author = (cand.authors || cand.Authors || [cand.author])[0] || "Unknown";
              const coverUrl = cand.cover_url || "/file.svg";

              return (
                <button
                  key={cand.manifestation_id || idx}
                  onClick={() => onSelect(cand)}
                  className="w-full flex items-center gap-4 p-4 text-left hover:bg-accent transition-colors group"
                >
                  <div
                    className={`relative h-16 w-12 shrink-0 rounded bg-muted overflow-hidden ${isAudio ? "aspect-square h-12 w-12" : "aspect-[2/3]"}`}
                  >
                    {coverUrl && coverUrl !== "/file.svg" ? (
                      <Image
                        src={
                          coverUrl.startsWith("/static")
                            ? `${process.env.NEXT_PUBLIC_API_URL || ""}${coverUrl}`
                            : coverUrl
                        }
                        alt={title}
                        fill
                        className="object-cover"
                        unoptimized
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-muted-foreground/30">
                        {isAudio ? (
                          <Disc className="h-6 w-6" />
                        ) : isVideo ? (
                          <Film className="h-6 w-6" />
                        ) : isGame ? (
                          <Gamepad2 className="h-6 w-6" />
                        ) : (
                          <BookOpen className="h-6 w-6" />
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className="text-[10px] h-4 uppercase px-1">
                        {format}
                      </Badge>
                      {cand.already_in_collection && (
                        <Badge
                          variant="secondary"
                          className="text-[10px] h-4 bg-green-500/10 text-green-600 dark:text-green-400 border-none px-1"
                        >
                          In Collection
                        </Badge>
                      )}
                    </div>
                    <h4 className="font-bold text-foreground truncate">{title}</h4>
                    <p className="text-xs text-muted-foreground truncate">{author}</p>
                  </div>

                  <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                </button>
              );
            })}
          </div>
        </CardContent>

        <div className="bg-muted/30 p-4 border-t border-border">
          <p className="text-[10px] text-center text-muted-foreground">
            Found multiple matches in your local database. Please pick one to continue.
          </p>
        </div>
      </Card>
    </div>
  );
}
