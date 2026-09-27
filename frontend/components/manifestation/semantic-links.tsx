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

import { useTranslations } from "next-intl";
import {
  ExternalLink,
  Globe,
  MapPin,
  BookMarked,
  RefreshCw,
  Trash2,
  CheckCircle2,
  Sparkles,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDeleteSemanticLink, useSemanticLinks, useTriggerRelink } from "@/lib/api/hooks";
import type { SemanticLink } from "@/types/frbr";
import { toast } from "sonner";

export interface SemanticLinksProps {
  manifestationId: number;
  canEdit?: boolean;
}

/**
 * Returns an icon and style color matching the external authority.
 *
 * @param authority - The authority name (e.g. "dbpedia", "geonames", "wordnet").
 * @returns Object with name, badgeVariant, badgeClass, and icon component.
 */
function getAuthorityConfig(authority: string) {
  switch (authority.toLowerCase()) {
    case "dbpedia":
      return {
        name: "DBpedia",
        badgeVariant: "default" as const,
        badgeClass: "bg-blue-600/10 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800",
        icon: Globe,
      };
    case "geonames":
      return {
        name: "GeoNames",
        badgeVariant: "default" as const,
        badgeClass:
          "bg-emerald-600/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800",
        icon: MapPin,
      };
    case "wordnet":
      return {
        name: "WordNet",
        badgeVariant: "default" as const,
        badgeClass: "bg-purple-600/10 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800",
        icon: BookMarked,
      };
    default:
      return {
        name: authority,
        badgeVariant: "secondary" as const,
        badgeClass: "",
        icon: Globe,
      };
  }
}

/**
 * Interactive Linked Open Data panel displaying resolved external links
 * for a Manifestation and its parent Work.
 *
 * @param props - Component props.
 * @param props.manifestationId - The ID of the manifestation.
 * @param props.canEdit - Whether the current user has permission to edit or remove links.
 * @returns Rendered SemanticLinks card component.
 */
export function SemanticLinks({ manifestationId, canEdit = false }: SemanticLinksProps) {
  const t = useTranslations("SemanticLinks");
  const { data, isLoading } = useSemanticLinks(manifestationId);
  const relinkMutation = useTriggerRelink(manifestationId);
  const deleteMutation = useDeleteSemanticLink(manifestationId);

  const handleRelink = () => {
    relinkMutation.mutate(undefined, {
      onSuccess: () => {
        toast.success(t("scanStarted"));
      },
      onError: () => {
        toast.error(t("scanFailed"));
      },
    });
  };

  const handleDelete = (link: SemanticLink) => {
    deleteMutation.mutate(link.id, {
      onSuccess: () => {
        toast.success(t("linkDeleted"));
      },
      onError: () => {
        toast.error(t("deleteFailed"));
      },
    });
  };

  const links = data?.links ?? [];

  return (
    <Card className="rounded-xl shadow-sm border border-border mt-6">
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            {t("title")}
          </CardTitle>
          <CardDescription className="text-xs text-muted-foreground mt-0.5">{t("description")}</CardDescription>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRelink}
          disabled={relinkMutation.isPending}
          className="text-xs h-8 gap-1.5"
          title={t("scanButton")}
        >
          {relinkMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          <span>{relinkMutation.isPending ? t("scanning") : t("scanButton")}</span>
        </Button>
      </CardHeader>

      <CardContent className="pt-2">
        {isLoading ? (
          <div className="space-y-2 py-2">
            <div className="h-9 w-full bg-muted/50 animate-pulse rounded-lg" />
            <div className="h-9 w-3/4 bg-muted/50 animate-pulse rounded-lg" />
          </div>
        ) : links.length === 0 ? (
          <div className="text-center py-5 px-4 border border-dashed rounded-lg bg-muted/10">
            <p className="text-xs font-medium text-muted-foreground">{t("noLinks")}</p>
            <p className="text-[11px] text-muted-foreground/75 mt-1">{t("noLinksHint")}</p>
          </div>
        ) : (
          <div className="divide-y divide-border/60">
            {links.map(link => {
              const config = getAuthorityConfig(link.authority);
              const Icon = config.icon;
              const confidencePercent = Math.round((link.confidence || 0) * 100);

              return (
                <div
                  key={link.id}
                  className="py-2.5 first:pt-0 last:pb-0 flex items-center justify-between gap-3 group"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Badge
                      variant="outline"
                      className={`text-[11px] font-medium gap-1 px-2 py-0.5 ${config.badgeClass}`}
                    >
                      <Icon className="h-3 w-3" />
                      <span>{config.name}</span>
                    </Badge>

                    <div className="flex flex-col min-w-0">
                      <a
                        href={link.external_uri}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-medium text-foreground hover:text-primary transition-colors flex items-center gap-1 truncate"
                        title={link.external_uri}
                      >
                        <span className="truncate">{link.pref_label || link.external_uri}</span>
                        <ExternalLink className="h-3 w-3 opacity-60 flex-shrink-0" />
                      </a>
                      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground mt-0.5">
                        <span>{t("confidence", { score: confidencePercent })}</span>
                        <span>•</span>
                        <span className="capitalize">
                          {link.entity_type === "work" ? t("levels.work") : t("levels.manifestation")}
                        </span>
                        {link.verified && (
                          <>
                            <span>•</span>
                            <span className="inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400 font-medium">
                              <CheckCircle2 className="h-2.5 w-2.5" />
                              {t("verified")}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {canEdit && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(link)}
                      disabled={deleteMutation.isPending}
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive transition-colors opacity-70 group-hover:opacity-100"
                      title={t("deleteLink")}
                      aria-label={t("deleteLink")}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
