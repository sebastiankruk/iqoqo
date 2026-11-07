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

"use client";

import { Boxes, Layers, Users, ExternalLink, Wrench, FileText } from "lucide-react";
import { getCoverTimestamp, getCoverUrl } from "@/lib/utils";
import { DiscoveryPivot } from "./discovery-pivot";

interface ExtendedMetadataLegoProps {
  meta: Record<string, unknown>;
  display?: {
    fields?: Record<string, unknown>;
    sections?: Record<string, unknown>;
  };
}

const BUILD_STATUS_LABELS: Record<string, string> = {
  sealed: "Sealed (In Box)",
  built: "Built",
  incomplete: "Incomplete",
  parted_out: "Parted Out",
};

/**
 * Extended metadata component for LEGO & construction set items.
 *
 * @param props - Component props
 * @param props.meta - The metadata record
 * @param props.display - Display projection from backend
 * @returns {JSX.Element} The rendered component
 */
export function ExtendedMetadataLego({ meta, display }: ExtendedMetadataLegoProps) {
  const fields = display?.fields || {};
  const setNumber = (fields["set_number"] ?? meta["set_number"] ?? meta["set_num"]) as string | undefined;
  const pieceCount = (fields["piece_count"] ?? meta["piece_count"] ?? meta["num_parts"]) as number | string | undefined;
  const minifigCount = (fields["minifig_count"] ?? meta["minifig_count"] ?? meta["num_minifigs"]) as
    number | string | undefined;
  const theme = (fields["theme"] ?? meta["theme"]) as string | undefined;
  const buildStatus = (fields["build_status"] ?? meta["build_status"]) as string | undefined;
  const missingPieces = (fields["missing_pieces_count"] ?? meta["missing_pieces_count"]) as number | string | undefined;
  const instructionsIncluded = (fields["instructions_included"] ?? meta["instructions_included"]) as
    boolean | undefined;

  const timestamp = getCoverTimestamp(meta);
  const coverUrl = getCoverUrl(meta["cover_url"] as string | undefined, timestamp);
  const externalUrl = (meta["external_url"] ?? meta["set_url"]) as string | undefined;

  return (
    <div className="rounded-xl border bg-card/50 p-5 shadow-sm space-y-4">
      {coverUrl && (
        <div className="flex justify-center mb-4">
          <div className="w-full max-w-[300px] aspect-square rounded-xl overflow-hidden shadow-md border bg-secondary/30">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={coverUrl} alt="LEGO Set Box" className="h-full w-full object-contain p-2" />
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h3 className="font-bold text-lg text-foreground font-serif">LEGO Set Details</h3>
        {externalUrl && (
          <a
            href={externalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline font-medium"
          >
            <span>View on Rebrickable</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {setNumber && (
          <div className="flex flex-col gap-1 p-3 bg-background rounded-lg border">
            <span className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground">Set Number</span>
            <span className="text-sm font-semibold font-mono" data-testid="lego-set-number">
              {setNumber}
            </span>
          </div>
        )}

        {pieceCount !== undefined && pieceCount !== null && (
          <div className="flex flex-col gap-1 p-3 bg-background rounded-lg border">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Layers className="h-3.5 w-3.5" />
              <span className="text-[10px] uppercase font-bold tracking-widest">Piece Count</span>
            </div>
            <span className="text-sm font-semibold" data-testid="lego-piece-count">
              {pieceCount} Pieces
            </span>
          </div>
        )}

        {minifigCount !== undefined && minifigCount !== null && (
          <div className="flex flex-col gap-1 p-3 bg-background rounded-lg border">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Users className="h-3.5 w-3.5" />
              <span className="text-[10px] uppercase font-bold tracking-widest">Minifigures</span>
            </div>
            <span className="text-sm font-semibold" data-testid="lego-minifig-count">
              {minifigCount}
            </span>
          </div>
        )}

        {theme && (
          <div className="flex flex-col gap-1 p-3 bg-background rounded-lg border">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Boxes className="h-3.5 w-3.5" />
              <span className="text-[10px] uppercase font-bold tracking-widest">Theme</span>
            </div>
            <DiscoveryPivot type="genres" value={theme} variant="link" className="text-sm font-semibold truncate" />
          </div>
        )}
      </div>

      {(buildStatus || missingPieces !== undefined || instructionsIncluded !== undefined) && (
        <div className="pt-2 border-t border-border/40 space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Physical Item State</span>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            {buildStatus && (
              <div className="flex items-center gap-2 p-2 bg-muted/20 rounded-md">
                <Wrench className="h-3.5 w-3.5 text-primary" />
                <span>
                  Status: <strong>{BUILD_STATUS_LABELS[buildStatus] || buildStatus}</strong>
                </span>
              </div>
            )}
            {instructionsIncluded !== undefined && (
              <div className="flex items-center gap-2 p-2 bg-muted/20 rounded-md">
                <FileText className="h-3.5 w-3.5 text-primary" />
                <span>
                  Instructions: <strong>{instructionsIncluded ? "Included" : "Missing"}</strong>
                </span>
              </div>
            )}
            {missingPieces !== undefined && Number(missingPieces) > 0 && (
              <div className="flex items-center gap-2 p-2 bg-destructive/10 text-destructive rounded-md">
                <span>
                  Missing: <strong>{missingPieces} pieces</strong>
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
