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

import * as React from "react";
import { Search, CheckCircle2, XCircle, Info, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useTranslations } from "next-intl";
import { apiClient } from "@/lib/api/client";
import Image from "next/image";
import Link from "next/link";

interface CheckInventoryProps {
  /** The public username of the profile being checked */
  username: string;
}

interface CheckResultData {
  type: "item" | "manifestation";
  id: number;
  manifestation_id?: number;
  title: string;
  cover_url?: string;
  status?: string;
  publisher?: string;
}

/**
 * A search component for visitors to check if a specific item exists in a public collection.
 * @param root0 - The component props.
 * @param root0.username - The public username of the profile being checked.
 * @returns The rendered search component.
 */
export function CheckInventory({ username }: CheckInventoryProps) {
  const t = useTranslations("Public");
  const [query, setQuery] = React.useState("");
  const [result, setResult] = React.useState<CheckResultData[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  const handleCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const res = await apiClient.post<{ success: boolean; data: CheckResultData[] }>(`/public/u/${username}/check`, {
        query: query.trim(),
      });
      // An empty `data` is a real answer ("not in this collection") and must
      // render as such; only a missing/failed request is an error.
      if (!res.data?.success || !Array.isArray(res.data.data)) {
        setError(t("checkFailed"));
        return;
      }
      setResult(res.data.data);
    } catch {
      // The axios interceptor has already normalised the backend's `error`
      // string onto the exception message. The previous raw `fetch` discarded
      // it, so a 404 "User not found" rendered as a blank panel.
      setError(t("checkFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full space-y-4">
      <form onSubmit={handleCheck} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            data-testid="check-inventory-input"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={t("checkPlaceholder")}
            className="h-10 w-full rounded-md border border-input bg-background pl-10 pr-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <Button type="submit" disabled={loading} className="shrink-0">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t("checkInventory")}
        </Button>
      </form>

      {error && (
        <Card id="inventory-error-card" className="overflow-hidden border-destructive/40">
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <div className="bg-destructive/10 p-2 rounded-full">
                <XCircle className="h-6 w-6 text-destructive" />
              </div>
              <p className="font-medium text-destructive" role="alert">
                {error}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {result && (
        <Card
          id="inventory-result-card"
          className="overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300 text-left"
        >
          <CardContent className="p-4">
            {result.length > 0 ? (
              <div className="flex flex-wrap justify-center gap-4">
                {result.map(item => (
                  <Link
                    href={`/manifestation/${item.type === "item" ? item.manifestation_id : item.id}`}
                    key={`${item.type}-${item.id}`}
                    className="block group w-[130px]"
                  >
                    <div className="flex flex-col items-center gap-2 p-2 rounded-md hover:bg-muted/30 transition-colors">
                      <div className="relative shrink-0">
                        {item.cover_url ? (
                          <div
                            className={`relative h-28 w-20 overflow-hidden rounded shadow-sm ${
                              item.type === "manifestation" ? "opacity-60 grayscale" : ""
                            }`}
                          >
                            <Image src={item.cover_url} alt={item.title} fill className="object-cover" />
                          </div>
                        ) : (
                          <div className="h-28 w-20 bg-muted rounded shadow-sm flex items-center justify-center">
                            {item.type === "item" ? (
                              <CheckCircle2 className="h-8 w-8 text-muted-foreground/30" />
                            ) : (
                              <Info className="h-8 w-8 text-muted-foreground/30" />
                            )}
                          </div>
                        )}

                        {/* Floating status badge for extreme compression */}
                        <div className="absolute -bottom-1 -right-1">
                          {item.type === "item" ? (
                            <div className="bg-green-600 dark:bg-green-500 rounded-full p-1 shadow-md border-2 border-background">
                              <CheckCircle2 className="h-3 w-3 text-white" />
                            </div>
                          ) : (
                            <div className="bg-amber-600 dark:bg-amber-500 rounded-full p-1 shadow-md border-2 border-background">
                              <Info className="h-3 w-3 text-white" />
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="w-full text-center space-y-1">
                        <p className="text-[10px] font-semibold text-primary uppercase tracking-tighter">
                          {item.type === "item" ? t("foundItem") : t("foundManifestation")}
                        </p>
                        <p className="text-[11px] font-bold leading-tight group-hover:underline line-clamp-2">
                          {item.title}
                        </p>
                        {item.type === "item" ? (
                          <p className="text-[9px] text-muted-foreground capitalize truncate">
                            {item.status?.replace(/_/g, " ")}
                          </p>
                        ) : (
                          <p className="text-[9px] text-muted-foreground truncate">{item.publisher}</p>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-4">
                <div className="bg-red-100 dark:bg-red-900/30 p-2 rounded-full">
                  <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
                </div>
                <p className="font-medium text-red-700 dark:text-red-400">{t("notFound")}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
