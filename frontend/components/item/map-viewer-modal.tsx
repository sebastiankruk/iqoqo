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

import React, { useState, useRef, useCallback, useEffect } from "react";
import Image from "next/image";
import {
  ZoomIn,
  ZoomOut,
  RotateCw,
  RotateCcw,
  Compass,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  MapPin,
} from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTranslations } from "next-intl";
import { resolveApiUrl } from "@/lib/utils";

export interface MapAttachmentItem {
  id?: string;
  title?: string;
  type?: string;
  image_url?: string | null;
  scale?: string | null;
  projection?: string | null;
}

export interface MapViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  maps: MapAttachmentItem[];
  initialIndex?: number;
  title?: string;
}

const MIN_ZOOM = 1;
const MAX_ZOOM = 5;
const ZOOM_STEP = 0.5;

/**
 * Validates that an image URL is safe to display in an image tag or modal.
 * Rejects javascript:, data:, blob: protocols and protocol-relative links.
 *
 * @param url - URL string candidate to check.
 * @returns True if the URL is a safe http(s) or absolute same-origin path.
 */
function isSafeDisplayUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  const trimmed = url.trim();
  if (
    trimmed === "/api" ||
    trimmed.toLowerCase().startsWith("javascript:") ||
    trimmed.toLowerCase().startsWith("data:") ||
    trimmed.toLowerCase().startsWith("file:") ||
    trimmed.toLowerCase().startsWith("vbscript:") ||
    trimmed.toLowerCase().startsWith("blob:")
  ) {
    return false;
  }
  if (trimmed.startsWith("/")) {
    return !trimmed.startsWith("//") && !trimmed.startsWith("/\\");
  }
  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

/**
 * Interactive zoom/pan/rotate modal dialog for exploring high-resolution map attachments.
 *
 * @param {MapViewerModalProps} props - Component properties.
 * @returns {JSX.Element | null} Rendered map inspector modal.
 */
export function MapViewerModal({ isOpen, onClose, maps, initialIndex = 0, title }: MapViewerModalProps) {
  const t = useTranslations("MapViewer");
  const defaultTitle = title || t("title");
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [prevIsOpen, setPrevIsOpen] = useState(isOpen);
  const [prevInitialIndex, setPrevInitialIndex] = useState(initialIndex);

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [rotation, setRotation] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const containerRef = useRef<HTMLDivElement>(null);

  // Sync state during render when props change, avoiding synchronous setState in useEffect
  if (isOpen !== prevIsOpen || initialIndex !== prevInitialIndex) {
    setPrevIsOpen(isOpen);
    setPrevInitialIndex(initialIndex);
    if (isOpen) {
      setCurrentIndex(Math.max(0, Math.min(initialIndex, maps.length - 1)));
      setZoom(1);
      setPan({ x: 0, y: 0 });
      setRotation(0);
    }
  }

  const resetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setRotation(0);
  }, []);

  const handleZoomIn = () => {
    setZoom(prev => Math.min(MAX_ZOOM, prev + ZOOM_STEP));
  };

  const handleZoomOut = () => {
    setZoom(prev => {
      const next = Math.max(MIN_ZOOM, prev - ZOOM_STEP);
      if (next === 1) setPan({ x: 0, y: 0 });
      return next;
    });
  };

  const handleRotate = () => {
    setRotation(prev => (prev + 90) % 360);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      handleZoomIn();
    } else {
      handleZoomOut();
    }
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    if (zoom <= 1) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    setIsDragging(false);
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // Ignore pointer release if target lost
    }
  };

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
        return;
      }

      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        setZoom(prev => Math.min(MAX_ZOOM, prev + ZOOM_STEP));
      } else if (e.key === "-" || e.key === "_") {
        e.preventDefault();
        setZoom(prev => {
          const next = Math.max(MIN_ZOOM, prev - ZOOM_STEP);
          if (next === 1) setPan({ x: 0, y: 0 });
          return next;
        });
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        setRotation(prev => (prev + 90) % 360);
      } else if (e.key === "0") {
        e.preventDefault();
        resetView();
      } else if (e.key === "ArrowLeft") {
        if (maps.length > 1) {
          e.preventDefault();
          setCurrentIndex(prev => (prev > 0 ? prev - 1 : maps.length - 1));
          resetView();
        }
      } else if (e.key === "ArrowRight") {
        if (maps.length > 1) {
          e.preventDefault();
          setCurrentIndex(prev => (prev < maps.length - 1 ? prev + 1 : 0));
          resetView();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, maps.length, resetView]);

  const currentMap = maps[currentIndex] || maps[0];

  if (!currentMap) return null;

  const rawUrl = currentMap.image_url;
  const isSafe = isSafeDisplayUrl(rawUrl);
  const resolved = isSafe && rawUrl ? resolveApiUrl(rawUrl) : "";
  const imageUrl = isSafe && resolved && resolved !== "/api" ? resolved : "";

  return (
    <Dialog open={isOpen} onOpenChange={open => !open && onClose()}>
      <DialogContent className="max-w-5xl h-[88vh] p-0 flex flex-col bg-background/95 backdrop-blur-md overflow-hidden border-border/80 shadow-2xl">
        {/* Header toolbar */}
        <DialogHeader className="px-5 py-3 border-b border-border/60 bg-muted/20 flex flex-row items-center justify-between gap-4 space-y-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <Compass className="h-5 w-5 text-primary shrink-0" />
            <div className="min-w-0">
              <DialogTitle className="text-base font-semibold truncate leading-tight">
                {currentMap.title || defaultTitle}
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground truncate">
                {currentMap.type ? currentMap.type.replace(/_/g, " ") : t("cartographicMap")}
                {currentMap.scale ? ` • ${t("scale", { scale: currentMap.scale })}` : ""}
                {currentMap.projection ? ` • ${t("projection", { projection: currentMap.projection })}` : ""}
              </DialogDescription>
            </div>
          </div>

          {/* Map navigation if multiple maps attached */}
          {maps.length > 1 && (
            <div className="flex items-center gap-1.5 shrink-0 bg-background/80 rounded-lg p-1 border border-border/50">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                disabled={currentIndex === 0}
                onClick={() => {
                  setCurrentIndex(prev => Math.max(0, prev - 1));
                  resetView();
                }}
                aria-label={t("prevMap")}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-xs font-mono px-1.5">
                {currentIndex + 1} / {maps.length}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                disabled={currentIndex === maps.length - 1}
                onClick={() => {
                  setCurrentIndex(prev => Math.min(maps.length - 1, prev + 1));
                  resetView();
                }}
                aria-label={t("nextMap")}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </DialogHeader>

        {/* Viewport Canvas */}
        <div
          ref={containerRef}
          data-testid="map-viewport"
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          className={`flex-1 relative overflow-hidden bg-black/40 flex items-center justify-center select-none ${
            zoom > 1 ? (isDragging ? "cursor-grabbing" : "cursor-grab") : "cursor-default"
          }`}
          style={{ touchAction: "none" }}
        >
          {imageUrl ? (
            <div
              data-testid="map-transform"
              className="relative w-full h-full flex items-center justify-center transition-transform duration-75 will-change-transform"
              style={{
                transform: `translate3d(${pan.x}px, ${pan.y}px, 0px) scale(${zoom}) rotate(${rotation}deg)`,
              }}
            >
              <Image
                src={imageUrl}
                alt={currentMap.title || "Map View"}
                fill
                unoptimized
                priority
                className="object-contain pointer-events-none drop-shadow-2xl"
              />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center text-muted-foreground p-8 text-center">
              <MapPin className="h-10 w-10 mb-2 opacity-50" />
              <p className="text-sm">{t("noMapImage")}</p>
            </div>
          )}
        </div>

        {/* Bottom Inspector Control Bar */}
        <div className="px-5 py-2.5 border-t border-border/60 bg-muted/30 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            {currentMap.type && (
              <Badge variant="outline" className="text-[11px] capitalize">
                {currentMap.type.replace(/_/g, " ")}
              </Badge>
            )}
            <span className="text-xs font-mono text-muted-foreground">{Math.round(zoom * 100)}%</span>
          </div>

          {/* Pan / Zoom / Rotate Actions (Grouped controls) */}
          <div className="flex items-center gap-1 bg-background/80 rounded-lg p-1 border border-border/50">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleZoomOut}
              disabled={zoom <= MIN_ZOOM}
              aria-label={t("zoomOut")}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleZoomIn}
              disabled={zoom >= MAX_ZOOM}
              aria-label={t("zoomIn")}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleRotate} aria-label={t("rotate")}>
              <RotateCw className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={resetView} aria-label={t("resetView")}>
              <RotateCcw className="h-4 w-4" />
            </Button>
            {imageUrl && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-foreground"
                asChild
              >
                <a href={imageUrl} target="_blank" rel="noopener noreferrer" aria-label={t("openFullImage")}>
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
