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
import { resolveApiUrl } from "@/lib/utils";
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

interface CheckResult {
  success: boolean;
  data: CheckResultData[];
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
  const [result, setResult] = React.useState<CheckResult | null>(null);
  const [loading, setLoading] = React.useState(false);

  const handleCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const res = await fetch(resolveApiUrl(`/public/u/${username}/check`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        setResult(data);
      }
    } catch (err) {
      console.error("Check failed", err);
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

      {result && (
        <Card className="overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300 text-left">
          <CardContent className="p-4">
            {result.data && result.data.length > 0 ? (
              <div className="flex flex-col gap-2">
                {result.data.map(item => (
                  <Link
                    href={`/manifestation/${item.type === "item" ? item.manifestation_id : item.id}`}
                    key={`${item.type}-${item.id}`}
                    className="block group"
                  >
                    <div className="flex items-start gap-4 p-2 rounded-md hover:bg-muted/30 transition-colors">
                      <div className="flex flex-col items-center gap-1.5 shrink-0">
                        {item.cover_url ? (
                          <div
                            className={`relative h-20 w-14 overflow-hidden rounded shadow-sm ${
                              item.type === "manifestation" ? "opacity-60 grayscale" : ""
                            }`}
                          >
                            <Image src={item.cover_url} alt={item.title} fill className="object-cover" />
                          </div>
                        ) : (
                          <div className="h-20 w-14 bg-muted rounded shadow-sm flex items-center justify-center">
                            {item.type === "item" ? (
                              <CheckCircle2 className="h-6 w-6 text-muted-foreground/30" />
                            ) : (
                              <Info className="h-6 w-6 text-muted-foreground/30" />
                            )}
                          </div>
                        )}
                        {item.type === "item" ? (
                          <div className="flex items-center gap-1 text-[10px] font-bold text-green-600 dark:text-green-400">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            <span>{t("foundItem")}</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-[10px] font-bold text-amber-600 dark:text-amber-400">
                            <Info className="h-3.5 w-3.5" />
                            <span>{t("foundManifestation")}</span>
                          </div>
                        )}
                      </div>
                      <div className="flex-1 min-w-0 py-1">
                        <p className="text-sm font-semibold leading-tight group-hover:underline line-clamp-2">
                          {item.title}
                        </p>
                        {item.type === "item" ? (
                          <p className="text-xs text-muted-foreground mt-1 capitalize">
                            Status: {item.status?.replace(/_/g, " ")}
                          </p>
                        ) : (
                          <p className="text-xs text-muted-foreground mt-1 truncate">{item.publisher}</p>
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
