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

import { useState, useEffect } from "react";
import type React from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle2, AlertCircle, Server } from "lucide-react";
import { getInstanceUrl, setInstanceUrl, setInstanceName } from "@/lib/capacitor/storage";

export interface ServerSelectorProps {
  initialUrl?: string;
  onConnected?: (instanceUrl: string, instanceName?: string) => void;
  showCancel?: boolean;
  onCancel?: () => void;
}

/**
 * Home Assistant (HASS)-style dynamic server selector for mobile devices.
 * Probes the target iqoqo instance via GET /api/health before saving.
 */
export function ServerSelector({ initialUrl, onConnected, showCancel = false, onCancel }: ServerSelectorProps) {
  const t = useTranslations("Mobile");
  const router = useRouter();

  const [urlInput, setUrlInput] = useState(initialUrl || "");
  const [isVerifying, setIsVerifying] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [verifiedInfo, setVerifiedInfo] = useState<{ name: string; version?: string } | null>(null);

  useEffect(() => {
    if (!initialUrl) {
      getInstanceUrl().then(saved => {
        if (saved) setUrlInput(saved);
      });
    }
  }, [initialUrl]);

  /**
   * Normalize entered server URL.
   */
  const normalizeUrl = (raw: string): string => {
    let trimmed = raw.trim();
    if (!trimmed) return "";
    if (!/^https?:\/\//i.test(trimmed)) {
      trimmed = `https://${trimmed}`;
    }
    return trimmed.replace(/\/+$/, "");
  };

  /**
   * Verify server health and configuration.
   */
  const handleVerify = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setErrorMessage(null);
    setVerifiedInfo(null);

    const normalized = normalizeUrl(urlInput);
    if (!normalized) {
      setErrorMessage(t("invalidUrl"));
      return;
    }

    try {
      new URL(normalized);
    } catch {
      setErrorMessage(t("invalidUrl"));
      return;
    }

    setIsVerifying(true);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);

      const healthRes = await fetch(`${normalized}/api/health`, {
        method: "GET",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      }).catch(err => {
        throw err;
      });

      clearTimeout(timeoutId);

      if (!healthRes.ok) {
        throw new Error(`HTTP ${healthRes.status}`);
      }

      let detectedName = "iqoqo Library";
      let detectedVersion: string | undefined;

      try {
        const configRes = await fetch(`${normalized}/api/config`, {
          method: "GET",
          headers: { Accept: "application/json" },
        });
        if (configRes.ok) {
          const configJson = await configRes.json();
          const configData = configJson?.data || configJson;
          if (configData?.instance_name) {
            detectedName = configData.instance_name;
          }
          if (configData?.version) {
            detectedVersion = configData.version;
          }
        }
      } catch {
        // Non-critical, fallback to default name
      }

      await setInstanceUrl(normalized);
      await setInstanceName(detectedName);

      setVerifiedInfo({ name: detectedName, version: detectedVersion });

      if (onConnected) {
        onConnected(normalized, detectedName);
      } else {
        router.push("/login");
      }
    } catch {
      setErrorMessage(t("connectionFailed"));
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto shadow-lg border-border">
      <CardHeader className="text-center space-y-2 pb-4">
        <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-1">
          <Server className="w-6 h-6" />
        </div>
        <CardTitle className="text-xl font-bold">{t("serverSelectorTitle")}</CardTitle>
        <CardDescription className="text-sm">{t("serverSelectorDescription")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleVerify} className="space-y-4">
          <div className="space-y-1.5">
            <label
              htmlFor="server-url-input"
              className="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
            >
              {t("serverUrlLabel")}
            </label>
            <input
              id="server-url-input"
              type="text"
              inputMode="url"
              autoCapitalize="none"
              autoCorrect="off"
              placeholder={t("serverUrlPlaceholder")}
              value={urlInput}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUrlInput(e.target.value)}
              disabled={isVerifying}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          {errorMessage && (
            <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {verifiedInfo && (
            <div className="flex items-center gap-2 p-3 text-sm text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-md">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <div className="flex-1">
                <p className="font-medium">{t("connectionSuccess", { name: verifiedInfo.name })}</p>
                {verifiedInfo.version && (
                  <p className="text-xs text-muted-foreground">{t("version", { version: verifiedInfo.version })}</p>
                )}
              </div>
            </div>
          )}

          <div className="pt-2 flex flex-col gap-2">
            <Button type="submit" className="w-full" disabled={isVerifying || !urlInput.trim()}>
              {isVerifying ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t("verifying")}
                </>
              ) : (
                t("verifyConnection")
              )}
            </Button>

            {showCancel && onCancel && (
              <Button type="button" variant="ghost" className="w-full" onClick={onCancel} disabled={isVerifying}>
                {t("cancel")}
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
