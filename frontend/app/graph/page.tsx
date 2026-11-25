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

import React, { Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { AlertTriangle, ArrowLeft, GitBranch, Loader2 } from "lucide-react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FRBRRelationGraph } from "@/components/graph/frbr-relation-graph";
import { GraphRootPicker } from "@/components/graph/graph-root-picker";
import { useCatalogGraph, useCatalogLibraryGraph } from "@/lib/api/hooks/catalog";
import type { GraphAnchorEntityType } from "@/types/frbr";

const VALID_TYPES = new Set<string>(["work", "expression", "manifestation", "item", "person", "contributor", "series"]);
const PRIMARY_LIBRARY_ENTITY_TYPES = ["work", "expression", "manifestation", "item"] as const;
const SECONDARY_LIBRARY_ENTITY_TYPES = ["series", "contributor", "map", "lod"] as const;
const LIBRARY_ENTITY_TYPES = [...PRIMARY_LIBRARY_ENTITY_TYPES, ...SECONDARY_LIBRARY_ENTITY_TYPES] as const;

/** Inner client graph explorer reading query params inside a Suspense boundary. */
function GraphExplorerContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const t = useTranslations("graph");

  const rawType = (searchParams.get("type") || "").toLowerCase();
  const rawId = Number(searchParams.get("id") || 0);
  const rawDepth = Number(searchParams.get("depth") || 2);
  const depth: 1 | 2 | 3 | 4 = rawDepth === 1 ? 1 : rawDepth === 3 ? 3 : rawDepth >= 4 ? 4 : 2;
  const rawMode = (searchParams.get("mode") || "").toLowerCase();
  const rawEntities = searchParams.get("entities") || "";

  const isValidAnchor = VALID_TYPES.has(rawType) && Number.isInteger(rawId) && rawId > 0;
  const isLibraryMode = rawMode === "library" || !isValidAnchor;
  const [showMoreEntityTypes, setShowMoreEntityTypes] = React.useState(false);
  const [pickerOpen, setPickerOpen] = React.useState(false);

  const {
    data: anchorGraph,
    isLoading: anchorLoading,
    isError: anchorError,
  } = useCatalogGraph(rawType, rawId, depth, !isLibraryMode && isValidAnchor);

  const {
    data: libraryGraph,
    isLoading: libraryLoading,
    isError: libraryError,
  } = useCatalogLibraryGraph(rawEntities || undefined, undefined, isLibraryMode);

  const graph = isLibraryMode ? libraryGraph : anchorGraph;
  const isLoading = isLibraryMode ? libraryLoading : anchorLoading;
  const isError = isLibraryMode ? libraryError : anchorError;

  const anchorNode = graph?.nodes.find(n => n.is_anchor);
  const anchorUrl = anchorNode?.url && anchorNode.url.startsWith("/") ? anchorNode.url : null;
  const fallbackAnchorUrl =
    rawType === "series"
      ? `/work/${rawId}`
      : rawType === "person" || rawType === "contributor"
        ? null
        : `/${rawType}/${rawId}`;
  const openEntityHref = anchorUrl ?? fallbackAnchorUrl;

  const handleDepthChange = (nextDepth: 1 | 2 | 3 | 4) => {
    if (!isValidAnchor) return;
    router.push(`/graph?type=${encodeURIComponent(rawType)}&id=${rawId}&depth=${nextDepth}`);
  };

  const handleRecenter = (entityType: GraphAnchorEntityType, entityId: number) => {
    router.push(`/graph?type=${encodeURIComponent(entityType)}&id=${entityId}&depth=${depth}`);
  };

  const activeEntityTypes = new Set(
    rawEntities
      .split(",")
      .map(s => s.trim().toLowerCase())
      .filter(Boolean)
  );

  const toggleEntityType = (ent: string) => {
    const next = new Set(activeEntityTypes.size > 0 ? activeEntityTypes : LIBRARY_ENTITY_TYPES);
    if (next.has(ent)) {
      if (next.size > 1) next.delete(ent);
    } else {
      next.add(ent);
    }
    const param = next.size === LIBRARY_ENTITY_TYPES.length ? "" : `&entities=${Array.from(next).join(",")}`;
    router.push(`/graph?mode=library${param}`);
  };

  return (
    <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            {!isLibraryMode && isValidAnchor && openEntityHref && (
              <Button asChild variant="ghost" size="sm" className="-ml-2 gap-1.5 text-muted-foreground">
                <Link href={openEntityHref}>
                  <ArrowLeft className="h-4 w-4" />
                  <span>{t("openEntity")}</span>
                </Link>
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              data-testid="graph-switch-root-button"
              onClick={() => setPickerOpen(true)}
            >
              {t("switchRoot")}
            </Button>
            {!isLibraryMode && (
              <Button asChild variant="outline" size="sm" data-testid="graph-mode-library">
                <Link href="/graph?mode=library">{t("libraryMode")}</Link>
              </Button>
            )}
          </div>
          <h1 className="font-serif text-2xl font-bold text-foreground flex items-center gap-2">
            <GitBranch className="h-6 w-6 text-primary" />
            <span>{t("title")}</span>
          </h1>
          <p className="text-xs text-muted-foreground">{t("subtitle")}</p>
        </div>

        {!isLibraryMode && isValidAnchor ? (
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-muted-foreground mr-1">{t("depthLabel")}:</span>
            {([1, 2, 3, 4] as const).map(d => (
              <Button
                key={d}
                type="button"
                size="sm"
                variant={depth === d ? "default" : "outline"}
                data-testid={`graph-depth-${d}`}
                onClick={() => handleDepthChange(d)}
              >
                {t(`hop${d}`)}
              </Button>
            ))}
          </div>
        ) : (
          <div
            className="relative flex flex-wrap items-center gap-1.5"
            role="group"
            aria-label="Entity type filters"
            data-testid="graph-entity-type-filters"
          >
            {PRIMARY_LIBRARY_ENTITY_TYPES.map(ent => {
              const active = activeEntityTypes.size === 0 || activeEntityTypes.has(ent);
              return (
                <Button
                  key={ent}
                  type="button"
                  size="sm"
                  variant={active ? "default" : "outline"}
                  data-testid={`graph-entity-${ent}`}
                  onClick={() => toggleEntityType(ent)}
                >
                  {t(`nodeTypes.${ent}`)}
                </Button>
              );
            })}
            <Button
              type="button"
              size="sm"
              variant="outline"
              aria-expanded={showMoreEntityTypes}
              data-testid="graph-entity-more-toggle"
              onClick={() => setShowMoreEntityTypes(prev => !prev)}
            >
              {t("moreTypes")}
            </Button>
            {showMoreEntityTypes && (
              <div
                className="absolute right-0 top-full z-20 mt-1 flex flex-wrap gap-1.5 rounded-lg border border-border bg-card p-2 shadow-md"
                data-testid="graph-entity-more-menu"
              >
                {SECONDARY_LIBRARY_ENTITY_TYPES.map(ent => {
                  const active = activeEntityTypes.size === 0 || activeEntityTypes.has(ent);
                  return (
                    <Button
                      key={ent}
                      type="button"
                      size="sm"
                      variant={active ? "default" : "outline"}
                      data-testid={`graph-entity-${ent}`}
                      onClick={() => toggleEntityType(ent)}
                    >
                      {t(`nodeTypes.${ent}`)}
                    </Button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex h-96 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : isError || !graph ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-6 text-sm text-destructive">
          {t("loadError")}
        </div>
      ) : (
        <>
          {graph.meta.truncated && (
            <div
              data-testid="graph-truncated-banner"
              className="flex items-center gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-800 dark:text-amber-200"
            >
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>
                {graph.meta.max_edges
                  ? t("truncatedEdgesBanner", { maxNodes: graph.meta.max_nodes, maxEdges: graph.meta.max_edges })
                  : t("truncatedBanner", { max: graph.meta.max_nodes })}
              </span>
            </div>
          )}

          <FRBRRelationGraph
            key={isLibraryMode ? `library:${rawEntities}` : `${rawType}:${rawId}:${depth}`}
            graph={graph}
            onRecenter={handleRecenter}
          />
        </>
      )}

      <Dialog open={pickerOpen} onOpenChange={setPickerOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("pickerDialogTitle")}</DialogTitle>
            <DialogDescription>{t("pickerDialogDescription")}</DialogDescription>
          </DialogHeader>
          <GraphRootPicker
            onSelect={(entityType, entityId) => {
              setPickerOpen(false);
              router.push(`/graph?type=${encodeURIComponent(entityType)}&id=${entityId}&depth=${depth}`);
            }}
          />
        </DialogContent>
      </Dialog>
    </main>
  );
}

/** Dedicated full-screen FRBR Relation Graph explorer page (`/graph?type=...&id=...&depth=...`). */
export default function GraphPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      <Suspense
        fallback={
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        }
      >
        <GraphExplorerContent />
      </Suspense>
      <Footer />
    </div>
  );
}
