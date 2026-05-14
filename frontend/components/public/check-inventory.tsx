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

interface CheckInventoryProps {
  /** The public username of the profile being checked */
  username: string;
}

interface CheckResult {
  has_item: boolean;
  data?: {
    title: string;
    cover_url?: string;
    status?: string;
    publisher?: string;
  };
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
        <Card className="overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300">
          <CardContent className="p-4">
            {result.has_item && result.data ? (
              <div className="flex items-start gap-4">
                <div className="bg-green-100 dark:bg-green-900/30 p-2 rounded-full">
                  <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div className="flex-1 space-y-1">
                  <p className="font-bold text-green-700 dark:text-green-400">{t("foundItem")}</p>
                  <div className="flex gap-3 mt-2">
                    {result.data.cover_url && (
                      <div className="relative h-20 w-14 shrink-0 overflow-hidden rounded shadow-sm">
                        <Image src={result.data.cover_url} alt={result.data.title} fill className="object-cover" />
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-medium leading-tight">{result.data.title}</p>
                      <p className="text-xs text-muted-foreground mt-1 capitalize">
                        Status: {result.data.status?.replace(/_/g, " ")}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : result.data ? (
              <div className="flex items-start gap-4">
                <div className="bg-amber-100 dark:bg-amber-900/30 p-2 rounded-full">
                  <Info className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                </div>
                <div className="flex-1 space-y-1">
                  <p className="font-bold text-amber-700 dark:text-amber-400">{t("foundManifestation")}</p>
                  <div className="flex gap-3 mt-2">
                    {result.data.cover_url && (
                      <div className="relative h-20 w-14 shrink-0 overflow-hidden rounded shadow-sm opacity-60">
                        <Image
                          src={result.data.cover_url}
                          alt={result.data.title}
                          fill
                          className="object-cover grayscale"
                        />
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-medium leading-tight">{result.data.title}</p>
                      <p className="text-xs text-muted-foreground mt-1">{result.data.publisher}</p>
                    </div>
                  </div>
                </div>
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
