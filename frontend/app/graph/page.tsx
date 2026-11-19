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
import { FRBRRelationGraph } from "@/components/graph/frbr-relation-graph";
import { useCatalogGraph } from "@/lib/api/hooks/catalog";
import type { GraphAnchorEntityType } from "@/types/frbr";

const VALID_TYPES = new Set<string>(["work", "expression", "manifestation", "item"]);

/** Inner client graph explorer reading query params inside a Suspense boundary. */
function GraphExplorerContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const t = useTranslations("graph");

  const rawType = (searchParams.get("type") || "").toLowerCase();
  const rawId = Number(searchParams.get("id") || 0);
  const rawDepth = Number(searchParams.get("depth") || 2);
  const depth = rawDepth === 1 ? 1 : 2;

  const isValidAnchor = VALID_TYPES.has(rawType) && Number.isInteger(rawId) && rawId > 0;

  const { data: graph, isLoading, isError } = useCatalogGraph(rawType, rawId, depth, isValidAnchor);

  const handleDepthChange = (nextDepth: 1 | 2) => {
    if (!isValidAnchor) return;
    router.push(`/graph?type=${encodeURIComponent(rawType)}&id=${rawId}&depth=${nextDepth}`);
  };

  const handleRecenter = (entityType: GraphAnchorEntityType, entityId: number) => {
    router.push(`/graph?type=${encodeURIComponent(entityType)}&id=${entityId}&depth=${depth}`);
  };

  return (
    <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            {isValidAnchor && (
              <Button asChild variant="ghost" size="sm" className="-ml-2 gap-1.5 text-muted-foreground">
                <Link href={`/${rawType}/${rawId}`}>
                  <ArrowLeft className="h-4 w-4" />
                  <span>{t("openEntity")}</span>
                </Link>
              </Button>
            )}
          </div>
          <h1 className="font-serif text-2xl font-bold text-foreground flex items-center gap-2">
            <GitBranch className="h-6 w-6 text-primary" />
            <span>{t("title")}</span>
          </h1>
          <p className="text-xs text-muted-foreground">{t("subtitle")}</p>
        </div>

        {isValidAnchor && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">{t("depthLabel")}:</span>
            <Button
              type="button"
              size="sm"
              variant={depth === 1 ? "default" : "outline"}
              data-testid="graph-depth-1"
              onClick={() => handleDepthChange(1)}
            >
              {t("hop1")}
            </Button>
            <Button
              type="button"
              size="sm"
              variant={depth === 2 ? "default" : "outline"}
              data-testid="graph-depth-2"
              onClick={() => handleDepthChange(2)}
            >
              {t("hop2")}
            </Button>
          </div>
        )}
      </div>

      {!isValidAnchor ? (
        <div className="rounded-xl border border-dashed border-border p-10 text-center space-y-3">
          <h2 className="font-serif text-lg font-semibold text-foreground">{t("missingParamsTitle")}</h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">{t("missingParamsDescription")}</p>
          <Button asChild variant="outline" size="sm">
            <Link href="/collection">{t("backToCollection")}</Link>
          </Button>
        </div>
      ) : isLoading ? (
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
              <span>{t("truncatedBanner", { max: graph.meta.max_nodes })}</span>
            </div>
          )}

          <FRBRRelationGraph key={`${rawType}:${rawId}:${depth}`} graph={graph} onRecenter={handleRecenter} />
        </>
      )}
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
