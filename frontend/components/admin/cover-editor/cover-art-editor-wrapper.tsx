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

import React, { useState, useRef, useEffect } from "react";
import { type PixelCrop } from "react-image-crop";
import { CoverCanvas } from "@/components/admin/cover-editor/cover-canvas";
import { EditorToolbar } from "@/components/admin/cover-editor/editor-toolbar";
import { InfoSidebar } from "@/components/admin/cover-editor/info-sidebar";
import { uploadEntityCover, searchFrbrEntities, type FrbrSearchResult } from "@/lib/api/admin";
import { useManifestation } from "@/lib/api/hooks";
import { getCoverUrl, getCoverTimestamp } from "@/lib/utils";
import { toast } from "sonner";
import { useMediaQuery } from "@/hooks/use-media-query";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Search, X, Loader2, AlertTriangle } from "lucide-react";

interface CoverArtEditorWrapperProps {
  preselectedManifestationId?: number | null;
}

/**
 * Component that wraps the Cover Art Editor logic and views.
 *
 * @param {Object} props - The component props.
 * @param {number | null} [props.preselectedManifestationId] - Optional manifestation ID to pre-load.
 * @returns {JSX.Element} The wrapper component for editing cover art.
 */
export function CoverArtEditorWrapper({ preselectedManifestationId }: CoverArtEditorWrapperProps) {
  const isDesktop = useMediaQuery("(min-width: 768px)");
  const [selectedEntityId, setSelectedEntityId] = useState<number | null>(preselectedManifestationId ?? null);
  const [entityType, setEntityType] = useState<"manifestation" | "item">("manifestation");

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<FrbrSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const { data: entityData, isLoading: isLoadingEntity } = useManifestation(selectedEntityId ?? 0);

  const imgRef = useRef<HTMLImageElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [imageSrc, setImageSrc] = useState<string>("/images/sample-cover-edit.jpg");
  const [crop, setCrop] = useState<import("react-image-crop").Crop>();
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>();
  const [aspect, setAspect] = useState<number | undefined>(2 / 3);
  const [rotation, setRotation] = useState(0);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    if (entityData) {
      const timestamp = getCoverTimestamp(entityData.meta);
      const url =
        getCoverUrl(entityData.cover_url || undefined, timestamp) ||
        (entityData.meta?.["cover_url"] as string | undefined);

      if (url && url !== imageSrc) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setImageSrc(url);
        // Reset editor state for new image
        setRotation(0);
        setFlipH(false);
        setFlipV(false);
        setCrop(undefined);
        setCompletedCrop(undefined);
      }
    }
  }, [entityData, imageSrc]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setSearchError(null);
    try {
      const results = await searchFrbrEntities(searchQuery.trim(), "manifestation", 20);
      setSearchResults(results);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const handleSelectManifestation = (id: number) => {
    setSelectedEntityId(id);
    setEntityType("manifestation");
  };

  const handleClearSelection = () => {
    setSelectedEntityId(null);
    setImageSrc("/images/sample-cover-edit.jpg");
    setCrop(undefined);
    setCompletedCrop(undefined);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageSrc(URL.createObjectURL(file));
      setRotation(0);
      setFlipH(false);
      setFlipV(false);
      setCrop(undefined);
      setCompletedCrop(undefined);
    }
  };

  const handleSave = async (blob: Blob) => {
    if (!selectedEntityId) {
      toast.error("No manifestation selected.");
      return;
    }

    try {
      setIsUploading(true);
      const response = await uploadEntityCover(entityType, selectedEntityId, blob);

      if (response.success) {
        toast.success("Cover art updated successfully!");
      } else {
        toast.error(response.error || "Failed to upload.");
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "An error occurred.");
    } finally {
      setIsUploading(false);
    }
  };

  const searchView = (
    <Card>
      <CardHeader>
        <CardTitle>Cover Art Editor</CardTitle>
        <CardDescription>Search for a manifestation to edit its cover art.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex gap-4">
          <input
            placeholder="Search by Title, ISBN, UPC, or EAN"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            className="flex h-10 w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
          <Button onClick={handleSearch} disabled={searching}>
            {searching ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Search className="h-4 w-4 mr-2" />}
            Search
          </Button>
        </div>

        {searchError && <p className="text-destructive font-medium">{searchError}</p>}

        {searchResults.length > 0 && (
          <div className="border rounded-lg divide-y">
            {searchResults.map(result => (
              <div
                key={result.id}
                className="flex items-center justify-between p-4 hover:bg-muted/50 cursor-pointer"
                onClick={() => handleSelectManifestation(result.id)}
              >
                <div>
                  <p className="font-medium">{result.title}</p>
                  <p className="text-sm text-muted-foreground">
                    ID: {result.id}
                    {result.isbn13 && ` | ISBN: ${result.isbn13}`}
                    {result.upc && ` | UPC: ${result.upc}`}
                  </p>
                </div>
                <Button variant="outline" size="sm">
                  Select
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );

  const editorView = (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <CardTitle>Cover Art Editor</CardTitle>
          <CardDescription>
            {isLoadingEntity
              ? "Loading manifestation..."
              : `Editing cover for: ${entityData?.title || `#${selectedEntityId}`}`}
          </CardDescription>
        </div>
        <Button variant="ghost" size="sm" onClick={handleClearSelection}>
          <X className="h-4 w-4 mr-2" /> Change Manifestation
        </Button>
      </CardHeader>
      <CardContent>
        <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileChange} className="hidden" />

        <div className="flex bg-background border rounded-md overflow-hidden min-h-[500px]">
          <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
            <EditorToolbar
              aspect={aspect}
              setAspect={setAspect}
              setRotation={setRotation}
              flipH={flipH}
              setFlipH={setFlipH}
              flipV={flipV}
              setFlipV={setFlipV}
            />
            <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-muted/30">
              <CoverCanvas
                imgRef={imgRef}
                imageUrl={imageSrc}
                crop={crop}
                setCrop={setCrop}
                setCompletedCrop={setCompletedCrop}
                aspect={aspect}
                rotation={rotation}
                flipH={flipH}
                flipV={flipV}
              />
            </div>
          </div>
          <InfoSidebar
            imgRef={imgRef}
            completedCrop={completedCrop}
            rotation={rotation}
            flipH={flipH}
            flipV={flipV}
            isUploading={isUploading}
            onSave={handleSave}
            onUploadSelect={() => fileInputRef.current?.click()}
          />
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="w-full">
      {!isDesktop ? (
        <div className="flex flex-col items-center justify-center p-8 text-center border rounded-lg bg-muted/50 min-h-[300px] gap-4">
          <AlertTriangle className="w-12 h-12 text-orange-500" />
          <h3 className="text-lg font-semibold">Screen Too Small</h3>
          <p className="text-muted-foreground text-sm">
            The advanced cover editor requires a larger screen for precise cropping and alignment. Please use an iPad or
            Desktop browser to edit covers.
          </p>
        </div>
      ) : (
        /* Desktop/Tablet View */
        <div className="w-full">{!selectedEntityId ? searchView : editorView}</div>
      )}
    </div>
  );
}
