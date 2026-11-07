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
import { Compass, Map as MapIcon, Maximize2, Plus, CheckCircle2, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { resolveApiUrl } from "@/lib/utils";
import { apiClient } from "@/lib/api/client";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { DisplayProjection } from "@/types/frbr";
import { MapViewerModal, type MapAttachmentItem } from "./map-viewer-modal";

interface ExtendedMetadataMapsProps {
  meta: Record<string, unknown>;
  display?: DisplayProjection | null;
  manifestationId?: number;
  canEdit?: boolean;
}

export function ExtendedMetadataMaps({ meta, display, manifestationId, canEdit = false }: ExtendedMetadataMapsProps) {
  const queryClient = useQueryClient();
  const fields = display?.fields || {};

  const mapScale = (fields["map_scale"] ?? meta["map_scale"] ?? meta["scale"]) as string | undefined;
  const mapProjection = (fields["map_projection"] ?? meta["map_projection"] ?? meta["projection"]) as
    string | undefined;
  const rawAttachments = (fields["map_attachments"] ?? meta["map_attachments"]) as MapAttachmentItem[] | undefined;
  const attachments: MapAttachmentItem[] = Array.isArray(rawAttachments) ? rawAttachments : [];

  const mapInsertPresent = fields["map_insert_present"] as boolean | undefined;

  const [viewerOpen, setViewerOpen] = useState(false);
  const [selectedMapIndex, setSelectedMapIndex] = useState(0);

  // Upload dialog state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadType, setUploadType] = useState("fold_out_insert");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const hasMaps = Boolean(meta["has_map"]) || attachments.length > 0 || Boolean(mapScale) || Boolean(mapProjection);

  if (!hasMaps && meta["format"] !== "cartographic_map" && meta["format"] !== "atlas") {
    return null;
  }

  const handleOpenViewer = (index: number) => {
    setSelectedMapIndex(index);
    setViewerOpen(true);
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manifestationId) return;
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append("title", uploadTitle.trim() || "Map Supplement");
      formData.append("type", uploadType);
      if (uploadFile) {
        formData.append("file", uploadFile);
      }

      const res = await apiClient.post(`/manifestations/${manifestationId}/map-attachments`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (res.data?.success) {
        toast.success("Map attachment uploaded successfully");
        setUploadOpen(false);
        setUploadTitle("");
        setUploadFile(null);
        queryClient.invalidateQueries({ queryKey: ["item"] });
        queryClient.invalidateQueries({ queryKey: ["manifestation"] });
      } else {
        toast.error(res.data?.error || "Failed to add map attachment");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add map attachment";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border bg-card/50 p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Compass className="h-5 w-5 text-teal-600 dark:text-teal-400" />
          <h3 className="font-bold text-lg text-foreground font-serif">Cartography & Map Supplements</h3>
        </div>

        {canEdit && manifestationId && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setUploadOpen(true)}
            className="flex items-center gap-1.5 h-8 text-xs"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Map
          </Button>
        )}
      </div>

      {/* Cartographic Spec Badges */}
      <div className="flex flex-wrap gap-2 text-xs">
        {mapScale && (
          <Badge variant="secondary" className="px-2.5 py-1">
            Scale: <span className="font-mono font-bold ml-1">{mapScale}</span>
          </Badge>
        )}
        {mapProjection && (
          <Badge variant="secondary" className="px-2.5 py-1">
            Projection: <span className="font-medium ml-1">{mapProjection}</span>
          </Badge>
        )}
        {mapInsertPresent !== undefined && (
          <Badge
            variant="outline"
            className={`px-2.5 py-1 flex items-center gap-1 ${
              mapInsertPresent ? "text-green-600 dark:text-green-400" : "text-amber-600 dark:text-amber-400"
            }`}
          >
            {mapInsertPresent ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
            {mapInsertPresent ? "Map Insert Present" : "Missing Map Insert"}
          </Badge>
        )}
      </div>

      {/* Attachments List */}
      {attachments.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-1">
          {attachments.map((att, idx) => {
            const rawUrl = att.image_url;
            const img = rawUrl ? resolveApiUrl(rawUrl) : null;
            return (
              <div
                key={att.id || idx}
                className="group relative rounded-lg border border-border/70 bg-card overflow-hidden p-3 flex flex-col justify-between transition-all hover:border-primary/50 hover:shadow-md"
              >
                <div className="flex items-start gap-3">
                  <div className="relative h-14 w-14 shrink-0 rounded-md bg-muted overflow-hidden border border-border/40 flex items-center justify-center">
                    {img ? (
                      <Image src={img} alt={att.title || "Map"} fill unoptimized className="object-cover" />
                    ) : (
                      <MapIcon className="h-6 w-6 text-muted-foreground/50" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold truncate leading-tight">{att.title || `Map #${idx + 1}`}</p>
                    <p className="text-[11px] text-muted-foreground capitalize mt-0.5">
                      {att.type ? att.type.replace(/_/g, " ") : "Map supplement"}
                    </p>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-border/40 flex items-center justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs flex items-center gap-1 text-primary hover:text-primary"
                    onClick={() => handleOpenViewer(idx)}
                  >
                    <Maximize2 className="h-3 w-3" />
                    Inspect Map
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/20 border border-border/40 text-xs text-muted-foreground">
          <MapIcon className="h-5 w-5 shrink-0 opacity-60" />
          <span>Includes cartographic materials or folding maps.</span>
        </div>
      )}

      {/* Map Inspector Viewer Dialog */}
      {attachments.length > 0 && (
        <MapViewerModal
          isOpen={viewerOpen}
          onClose={() => setViewerOpen(false)}
          maps={attachments}
          initialIndex={selectedMapIndex}
          title={typeof meta["title"] === "string" ? meta["title"] : "Map Inspector"}
        />
      )}

      {/* Upload Map Dialog */}
      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Map Attachment</DialogTitle>
            <DialogDescription>Attach a high-resolution map insert, fold-out, or world map.</DialogDescription>
          </DialogHeader>

          <form onSubmit={handleUploadSubmit} className="space-y-4 pt-2">
            <div>
              <label className="text-xs font-semibold">Map Title</label>
              <input
                type="text"
                value={uploadTitle}
                onChange={e => setUploadTitle(e.target.value)}
                placeholder="e.g. World Map Insert"
                className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs"
              />
            </div>

            <div>
              <label className="text-xs font-semibold">Map Type</label>
              <select
                value={uploadType}
                onChange={e => setUploadType(e.target.value)}
                className="mt-1 flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-xs"
              >
                <option value="world_map">World Map</option>
                <option value="fold_out_insert">Fold-out Insert</option>
                <option value="cloth_map">Cloth Map</option>
                <option value="game_board">Game Board</option>
                <option value="topographic">Topographic Map</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold">Map Image File</label>
              <input
                type="file"
                accept="image/*"
                onChange={e => setUploadFile(e.target.files?.[0] || null)}
                className="mt-1 flex w-full text-xs file:mr-4 file:py-1 file:px-2 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setUploadOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSubmitting}>
                {isSubmitting ? "Uploading..." : "Save Attachment"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
