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
import { useTranslations } from "next-intl";
import { Plus, Trash2, Copy, Check, AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";
import { useProfile } from "@/lib/api/hooks";

export interface PersonalAccessToken {
  id: number;
  name: string;
  token_prefix: string;
  scopes: string[];
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string | null;
  is_active: boolean;
}

interface TokensListResponse {
  items: PersonalAccessToken[];
  total: number;
  limit: number;
  offset: number;
}

interface CreateTokenResponse {
  token: string;
  data: PersonalAccessToken;
}

const AVAILABLE_SCOPES = [
  { id: "read:catalog", label: "read:catalog", description: "Read catalog items, works, and manifestations" },
  { id: "write:catalog", label: "write:catalog", description: "Create, update, and manage catalog items" },
  { id: "admin", label: "admin", description: "Administrative settings, user management, and diagnostics" },
  { id: "*", label: "* (Full Access)", description: "Unrestricted access matching all account permissions" },
];

/**
 * Personal Access Tokens (PATs) management card.
 *
 * @returns {JSX.Element} The component
 */
export function PatManagement() {
  const t = useTranslations("Profile");
  const { data: profile } = useProfile();
  const isAdmin = Boolean(profile?.roles?.includes("admin"));
  const availableScopes = AVAILABLE_SCOPES.filter(
    s => (s.id !== "admin" && s.id !== "*") || isAdmin
  );

  const [tokens, setTokens] = useState<PersonalAccessToken[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Dialog state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [tokenName, setTokenName] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["read:catalog"]);
  const [expirationDays, setExpirationDays] = useState<string>("30");
  const [isCreating, setIsCreating] = useState(false);

  // Newly generated token state (displayed only once)
  const [newlyCreatedToken, setNewlyCreatedToken] = useState<string | null>(null);
  const [copiedToken, setCopiedToken] = useState(false);

  // Revocation state
  const [revokingId, setRevokingId] = useState<number | null>(null);

  const fetchTokens = useCallback(async () => {
    try {
      const res = await apiClient.get<TokensListResponse>("/auth/tokens?limit=50&offset=0");
      if (res && res.data) {
        setTokens(res.data.items || []);
        setTotal(res.data.total || 0);
      }
    } catch (err: unknown) {
      console.error("Failed to load personal access tokens", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const res = await apiClient.get<TokensListResponse>("/auth/tokens?limit=50&offset=0");
        if (!active || !res || !res.data) return;
        setTokens(res.data.items || []);
        setTotal(res.data.total || 0);
      } catch (err: unknown) {
        if (!active) return;
        console.error("Failed to load personal access tokens", err);
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };
    load();
    return () => {
      active = false;
    };
  }, []);

  const handleScopeToggle = (scopeId: string) => {
    setSelectedScopes(prev => (prev.includes(scopeId) ? prev.filter(s => s !== scopeId) : [...prev, scopeId]));
  };

  const handleCreateToken = async () => {
    if (!tokenName.trim()) {
      toast.error("Token name is required");
      return;
    }

    if (selectedScopes.length === 0) {
      toast.error("Please select at least one scope");
      return;
    }

    setIsCreating(true);
    try {
      const res = await apiClient.post<CreateTokenResponse>("/auth/tokens", {
        name: tokenName.trim(),
        scopes: selectedScopes,
        expires_in_days: expirationDays === "0" ? null : parseInt(expirationDays, 10),
      });

      setNewlyCreatedToken(res.data.token);
      setTokenName("");
      setSelectedScopes(["read:catalog"]);
      setExpirationDays("30");
      setIsCreateOpen(false);
      toast.success("Personal access token generated");
      await fetchTokens();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create personal access token";
      toast.error(msg);
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevokeToken = async (tokenId: number) => {
    setRevokingId(tokenId);
    try {
      await apiClient.delete(`/auth/tokens/${tokenId}`);
      toast.success("Token revoked");
      await fetchTokens();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to revoke token";
      toast.error(msg);
    } finally {
      setRevokingId(null);
    }
  };

  const copyTokenToClipboard = () => {
    if (!newlyCreatedToken) return;
    navigator.clipboard.writeText(newlyCreatedToken);
    setCopiedToken(true);
    toast.success("Token copied to clipboard");
    setTimeout(() => setCopiedToken(false), 2000);
  };

  return (
    <div className="p-4 border rounded-lg bg-card space-y-4" data-testid="pat-management-card">
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold">{t("personalAccessTokens")}</h2>
            <Badge variant="outline" className="font-mono text-xs">
              {total}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {t("personalAccessTokensDesc")}
          </p>
        </div>

        <Button
          variant="default"
          size="sm"
          onClick={() => {
            setNewlyCreatedToken(null);
            setIsCreateOpen(true);
          }}
          data-testid="generate-pat-button"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          {t("generateNewToken")}
        </Button>
      </div>

      {/* ── Newly Created Token Display Banner ── */}
      {newlyCreatedToken && (
        <div
          className="p-4 rounded-lg border border-amber-500/50 bg-amber-500/10 space-y-2"
          data-testid="new-pat-banner"
        >
          <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-medium text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {t("tokenCreatedDesc")}
          </div>
          <div className="flex items-center gap-2">
            <code className="text-xs bg-background/80 px-3 py-2 rounded border border-border flex-1 font-mono break-all select-all">
              {newlyCreatedToken}
            </code>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={copyTokenToClipboard}
              className="h-9 px-3"
              data-testid="copy-pat-button"
            >
              {copiedToken ? <Check className="w-4 h-4 text-green-600 mr-1" /> : <Copy className="w-4 h-4 mr-1" />}
              {copiedToken ? "Copied" : "Copy"}
            </Button>
          </div>
        </div>
      )}

      {/* ── Tokens Table / List ── */}
      {isLoading ? (
        <div className="flex justify-center items-center py-6 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading tokens...
        </div>
      ) : tokens.length === 0 ? (
        <div className="text-center py-6 border border-dashed rounded-md text-sm text-muted-foreground">
          {t("noTokens")}
        </div>
      ) : (
        <div className="divide-y border rounded-md">
          {tokens.map(token => (
            <div
              key={token.id}
              className="p-3 flex flex-col sm:flex-row justify-between sm:items-center gap-2 hover:bg-muted/30 transition-colors"
              data-testid={`pat-item-${token.id}`}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{token.name}</span>
                  <code className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded font-mono">
                    {token.token_prefix}...
                  </code>
                  {token.is_active ? (
                    <Badge variant="outline" className="text-xs text-green-600 border-green-600/30">
                      {t("active")}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-xs text-muted-foreground">
                      {token.revoked_at ? t("revoked") : "Expired"}
                    </Badge>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                  <span>{t("scopes")}:</span>
                  {token.scopes.map(s => (
                    <span key={s} className="bg-muted/80 px-1.5 py-0.5 rounded text-[11px] font-mono">
                      {s}
                    </span>
                  ))}
                  <span>•</span>
                  <span>Created: {token.created_at ? new Date(token.created_at).toLocaleDateString() : "—"}</span>
                  {token.last_used_at && (
                    <>
                      <span>•</span>
                      <span>{t("lastUsed")}: {new Date(token.last_used_at).toLocaleDateString()}</span>
                    </>
                  )}
                  {token.expires_at && (
                    <>
                      <span>•</span>
                      <span>{t("expires")}: {new Date(token.expires_at).toLocaleDateString()}</span>
                    </>
                  )}
                </div>
              </div>

              {token.is_active && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRevokeToken(token.id)}
                  disabled={revokingId === token.id}
                  className="text-destructive hover:bg-destructive/10 self-end sm:self-center h-8 px-2"
                  data-testid={`revoke-pat-${token.id}`}
                >
                  {revokingId === token.id ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5 mr-1" />
                  )}
                  {t("revoke")}
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Generate Token Dialog ── */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="generate-pat-dialog">
          <DialogHeader>
            <DialogTitle>{t("generateNewToken")}</DialogTitle>
            <DialogDescription>
              {t("personalAccessTokensDesc")}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label htmlFor="pat-name-input" className="text-sm font-medium">
                {t("tokenName")} <span className="text-destructive">*</span>
              </label>
              <input
                id="pat-name-input"
                type="text"
                placeholder={t("tokenNamePlaceholder")}
                value={tokenName}
                onChange={e => setTokenName(e.target.value)}
                maxLength={100}
                className="w-full h-9 px-3 py-2 text-sm rounded-md border border-input bg-background"
                data-testid="pat-name-input"
                autoFocus
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">{t("scopes")}</label>
              <div className="space-y-2 border rounded-md p-3">
                {availableScopes.map(scope => (
                  <label key={scope.id} className="flex items-start gap-2.5 cursor-pointer text-xs">
                    <input
                      type="checkbox"
                      checked={selectedScopes.includes(scope.id)}
                      onChange={() => handleScopeToggle(scope.id)}
                      className="mt-0.5 rounded border-input"
                      data-testid={`scope-checkbox-${scope.id}`}
                    />
                    <div>
                      <div className="font-mono font-medium text-foreground">{scope.label}</div>
                      <div className="text-muted-foreground">{scope.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="pat-expiration-select" className="text-sm font-medium">
                {t("expiration")}
              </label>
              <select
                id="pat-expiration-select"
                value={expirationDays}
                onChange={e => setExpirationDays(e.target.value)}
                className="w-full h-9 px-3 py-2 text-sm rounded-md border border-input bg-background"
                data-testid="pat-expiration-select"
              >
                <option value="30">{t("days30")}</option>
                <option value="60">{t("days60")}</option>
                <option value="90">{t("days90")}</option>
                <option value="0">{t("noExpiration")}</option>
              </select>
            </div>
          </div>

          <DialogFooter className="sm:justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)} disabled={isCreating}>
              {t("cancel")}
            </Button>
            <Button
              type="button"
              onClick={handleCreateToken}
              disabled={isCreating || !tokenName.trim()}
              data-testid="confirm-generate-pat-button"
            >
              {isCreating && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              {t("generateToken")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
