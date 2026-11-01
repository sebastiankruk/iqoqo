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

import React, { useEffect, useState } from "react";
import { getFederationDirectory } from "@/lib/api/federation";
import type { FederationDirectoryData } from "@/types/federation";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Globe, Library, Server, ShieldCheck, Clock, ExternalLink, Search } from "lucide-react";
import { useTranslations } from "next-intl";

/**
 * Connected libraries directory page rendering peer instances and local library statistics.
 *
 * @returns {JSX.Element} The rendered directory page.
 */
export default function FederationDirectoryPage() {
  const t = useTranslations("FederationDirectory");
  const [data, setData] = useState<FederationDirectoryData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>("");

  useEffect(() => {
    let isMounted = true;
    getFederationDirectory()
      .then(res => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          setError(err?.message || "Failed to load directory");
          setLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const peers = (data?.peers || []).filter(peer => peer.domain.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <Globe className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-serif font-bold tracking-tight">{t("title")}</h1>
          </div>
          <p className="text-muted-foreground mt-2 max-w-2xl">{t("description")}</p>
        </div>

        {/* Local Instance Hub Card */}
        {data?.local_instance && (
          <Card className="mb-8 border-primary/30 bg-primary/5">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <Badge variant="outline" className="gap-1 border-primary text-primary">
                  <Server className="h-3.5 w-3.5" />
                  {t("thisInstance")}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {data.local_instance.software_name} v{data.local_instance.software_version}
                </span>
              </div>
              <CardTitle className="text-xl mt-2">{data.local_instance.domain}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Library className="h-4 w-4" />
                <span>{t("publicHoldings", { count: data.local_instance.public_items_count })}</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Federation Disabled Notice */}
        {data?.federation_enabled === false && (
          <div
            data-testid="federation-disabled-banner"
            className="mb-8 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-800 dark:text-amber-200 flex items-center gap-3"
          >
            <ShieldCheck className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
            <div>
              <p className="font-semibold">{t("disabledTitle") || "Federation disabled on this instance"}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("disabledBanner") ||
                  "Server-to-server federation is currently disabled. You can still explore the local library collection."}
              </p>
            </div>
          </div>
        )}

        {/* Search Input */}
        <div className="relative mb-6 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={t("searchPlaceholder")}
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="h-9 w-full rounded-md border border-input bg-transparent pl-9 pr-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>

        {/* Peer Libraries List */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-40 rounded-xl bg-card border border-border animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <Card className="border-destructive/30 bg-destructive/5 text-destructive p-6">
            <p className="text-sm font-medium">{error}</p>
          </Card>
        ) : peers.length === 0 ? (
          <Card className="p-8 text-center text-muted-foreground">
            <Library className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p>{t("noLibrariesFound")}</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {peers.map(peer => (
              <Card key={peer.id} className="hover:border-primary/50 transition-colors">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary" className="gap-1">
                      <ShieldCheck className="h-3 w-3 text-green-600 dark:text-green-400" />
                      {peer.trust_level}
                    </Badge>
                    {peer.last_seen_at && (
                      <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(peer.last_seen_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  <CardTitle className="text-base font-semibold mt-2 truncate">{peer.domain}</CardTitle>
                  <CardDescription className="text-xs">
                    {peer.software_name ? `${peer.software_name} ${peer.software_version || ""}` : t("unknownSoftware")}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <a
                    href={`https://${peer.domain}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    <span>{t("visitLibrary")}</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
