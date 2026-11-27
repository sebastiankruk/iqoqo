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

import { useState, useEffect, useCallback } from "react";
import type React from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, AlertCircle, Server, Trash2, Pencil, Check, X } from "lucide-react";
import {
  getInstanceUrl,
  getSavedServers,
  getActiveServerId,
  saveServerProfile,
  switchActiveServer,
  updateServerProfile,
  removeServerProfile,
  getAuthToken,
  type ServerProfile,
} from "@/lib/capacitor/storage";

export interface ServerSelectorProps {
  initialUrl?: string;
  onConnected?: (instanceUrl: string, instanceName?: string) => void;
  showCancel?: boolean;
  onCancel?: () => void;
}

/**
 * Home Assistant (HASS)-style dynamic multi-server selector for mobile devices.
 * Probes target iqoqo instances via GET /api/health before saving and isolates
 * auth tokens and offline caches per saved server profile.
 */
export function ServerSelector({ initialUrl, onConnected, showCancel = false, onCancel }: ServerSelectorProps) {
  const t = useTranslations("Mobile");
  const router = useRouter();
  const queryClient = useQueryClient();

  const [urlInput, setUrlInput] = useState(initialUrl || "");
  const [nameInput, setNameInput] = useState("");
  const [servers, setServers] = useState<ServerProfile[]>([]);
  const [activeServerId, setActiveServerId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [verifiedInfo, setVerifiedInfo] = useState<{ name: string; version?: string } | null>(null);

  const loadServers = useCallback(async () => {
    const [list, activeId, savedUrl] = await Promise.all([
      getSavedServers(),
      getActiveServerId(),
      initialUrl ? Promise.resolve(initialUrl) : getInstanceUrl(),
    ]);
    setServers(list);
    setActiveServerId(activeId);
    if (!initialUrl && savedUrl) {
      setUrlInput(prev => prev || savedUrl);
    }
  }, [initialUrl]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getSavedServers(),
      getActiveServerId(),
      initialUrl ? Promise.resolve(initialUrl) : getInstanceUrl(),
    ]).then(([list, activeId, savedUrl]) => {
      if (cancelled) return;
      setServers(list);
      setActiveServerId(activeId);
      if (!initialUrl && savedUrl) {
        setUrlInput(prev => prev || savedUrl);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [initialUrl]);

  /** Normalize entered server URL. */
  const normalizeUrl = (raw: string): string => {
    let trimmed = raw.trim();
    if (!trimmed) return "";
    if (!/^https?:\/\//i.test(trimmed)) {
      trimmed = `https://${trimmed}`;
    }
    return trimmed.replace(/\/+$/, "");
  };

  /** Switch to an already-saved server profile without wiping other servers' tokens/caches. */
  const handleSwitchServer = async (profile: ServerProfile) => {
    setErrorMessage(null);
    const activated = await switchActiveServer(profile.id);
    if (!activated) return;

    setActiveServerId(activated.id);
    queryClient.clear();
    queryClient.invalidateQueries({ queryKey: ["auth", "providers"] });

    if (onConnected) {
      onConnected(activated.url, activated.name);
      return;
    }

    const token = await getAuthToken(activated.id);
    router.push(token ? "/collection" : "/login");
  };

  /** Persist inline server rename. */
  const handleSaveRename = async (serverId: string) => {
    if (!editingName.trim()) {
      setEditingId(null);
      return;
    }
    await updateServerProfile(serverId, { name: editingName.trim() });
    setEditingId(null);
    await loadServers();
  };

  /** Remove a saved server profile along with its isolated token and offline cache. */
  const handleRemoveServer = async (serverId: string) => {
    await removeServerProfile(serverId);
    queryClient.clear();
    await loadServers();
  };

  /** Verify new server health and save/activate its profile. */
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
        clearTimeout(timeoutId);
        throw err;
      });

      clearTimeout(timeoutId);

      if (!healthRes.ok) {
        throw new Error(`HTTP ${healthRes.status}`);
      }

      let detectedName = nameInput.trim() || "iqoqo Library";
      let detectedVersion: string | undefined;

      try {
        const configRes = await fetch(`${normalized}/api/config`, {
          method: "GET",
          headers: { Accept: "application/json" },
        });
        if (configRes.ok) {
          const configJson = await configRes.json();
          const configData = configJson?.data || configJson;
          if (!nameInput.trim() && configData?.instance_name) {
            detectedName = configData.instance_name;
          }
          if (configData?.version) {
            detectedVersion = configData.version;
          }
        }
      } catch {
        // Non-critical, fallback to default name
      }

      const saved = await saveServerProfile({ url: normalized, name: detectedName }, true);
      queryClient.clear();
      queryClient.invalidateQueries({ queryKey: ["auth", "providers"] });

      setActiveServerId(saved.id);
      await loadServers();
      setVerifiedInfo({ name: detectedName, version: detectedVersion });
      setNameInput("");

      if (onConnected) {
        onConnected(normalized, detectedName);
      } else {
        const existingToken = await getAuthToken(saved.id);
        router.push(existingToken ? "/collection" : "/login");
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
      <CardContent className="space-y-5">
        {servers.length > 0 && (
          <div className="space-y-2" data-testid="saved-servers-list">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("savedServers")}</p>
            <div className="space-y-2">
              {servers.map(srv => {
                const isActive = srv.id === activeServerId;
                const isEditing = editingId === srv.id;
                return (
                  <div
                    key={srv.id}
                    data-testid={`saved-server-${srv.id}`}
                    className={`flex items-center justify-between gap-2 rounded-lg border p-2.5 text-sm ${
                      isActive ? "border-primary/50 bg-primary/5" : "border-border bg-background"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      {isEditing ? (
                        <div className="flex items-center gap-1">
                          <input
                            type="text"
                            value={editingName}
                            onChange={e => setEditingName(e.target.value)}
                            aria-label={t("serverNameLabel")}
                            className="h-7 w-full rounded border border-input bg-background px-2 text-xs"
                          />
                          <Button
                            type="button"
                            size="icon"
                            variant="ghost"
                            className="h-7 w-7 shrink-0"
                            onClick={() => handleSaveRename(srv.id)}
                            aria-label={t("saveName")}
                          >
                            <Check className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            type="button"
                            size="icon"
                            variant="ghost"
                            className="h-7 w-7 shrink-0"
                            onClick={() => setEditingId(null)}
                            aria-label={t("cancel")}
                          >
                            <X className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center gap-1.5">
                            <span className="font-medium truncate">{srv.name}</span>
                            {isActive && (
                              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                                {t("activeServer")}
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground font-mono truncate">{srv.url}</p>
                        </>
                      )}
                    </div>
                    {!isEditing && (
                      <div className="flex items-center gap-1 shrink-0">
                        {!isActive && (
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs"
                            onClick={() => handleSwitchServer(srv)}
                          >
                            {t("switchToServer")}
                          </Button>
                        )}
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7"
                          onClick={() => {
                            setEditingId(srv.id);
                            setEditingName(srv.name);
                          }}
                          aria-label={t("renameServer")}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 text-destructive hover:text-destructive"
                          onClick={() => handleRemoveServer(srv.id)}
                          aria-label={t("removeServer")}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <form onSubmit={handleVerify} className="space-y-4">
          <div className="space-y-1.5">
            <label
              htmlFor="server-name-input"
              className="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
            >
              {t("serverNameLabel")}
            </label>
            <input
              id="server-name-input"
              type="text"
              placeholder={t("serverNamePlaceholder")}
              value={nameInput}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNameInput(e.target.value)}
              disabled={isVerifying}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

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

/**
 * Modal wrapper for ServerSelector to switch servers on mobile screens.
 */
export function ServerSelectorModal({
  isOpen,
  onClose,
  onConnected,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConnected?: (instanceUrl: string) => void;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md max-h-[90vh] overflow-y-auto">
        <ServerSelector
          showCancel
          onCancel={onClose}
          onConnected={url => {
            onConnected?.(url);
            onClose();
          }}
        />
      </div>
    </div>
  );
}
