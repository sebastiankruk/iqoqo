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
import { getInstanceSettings, updateInstanceSettings, revealSettingValue } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { Loader2, Eye, EyeOff, Save, KeyRound, ExternalLink, CheckCircle2, AlertCircle } from "lucide-react";

interface InstanceSettingsProps {
  category?: "external_apis" | "federation" | "affiliate" | "internal";
  showApiKeys?: boolean;
}

interface SettingValue {
  value: string | boolean | null;
  source: "db" | "env" | "missing";
}

interface InstanceSettingsData {
  [key: string]: SettingValue | string | boolean | null;
}

interface SettingItem {
  key: string;
  label: string;
  type: "api" | "text" | "boolean";
  placeholder: string;
  description?: string;
}

interface SettingGroup {
  id: string;
  title: string;
  description: string;
  items: SettingItem[];
}

const API_SERVICE_GROUPS: SettingGroup[] = [
  {
    id: "allegro",
    title: "Allegro Integration",
    description:
      "Configure Allegro API client credentials and authorize account access for Polish book & media catalog lookups.",
    items: [
      { key: "ALLEGRO_CLIENT_ID", label: "Allegro Client ID", type: "api", placeholder: "Enter Allegro Client ID" },
      {
        key: "ALLEGRO_CLIENT_SECRET",
        label: "Allegro Client Secret",
        type: "api",
        placeholder: "Enter Allegro Client Secret",
      },
    ],
  },
  {
    id: "twitch_igdb",
    title: "Twitch / IGDB Video Games API",
    description:
      "Configure Twitch Developer Application credentials to enable Internet Game Database (IGDB) artwork and game metadata lookup.",
    items: [
      { key: "TWITCH_CLIENT_ID", label: "Twitch / IGDB Client ID", type: "api", placeholder: "Enter Twitch Client ID" },
      {
        key: "TWITCH_CLIENT_SECRET",
        label: "Twitch / IGDB Client Secret",
        type: "api",
        placeholder: "Enter Twitch Client Secret",
      },
    ],
  },
  {
    id: "google",
    title: "Google Services",
    description: "Configure Google Books API for ISBN metadata and Google Gemini API for AI features.",
    items: [
      {
        key: "GOOGLE_BOOKS_API_KEY",
        label: "Google Books API Key",
        type: "api",
        placeholder: "Enter Google Books API key",
      },
      {
        key: "GEMINI_API_KEY",
        label: "Google Gemini API Key",
        type: "api",
        placeholder: "Enter Google Gemini API key",
      },
    ],
  },
  {
    id: "media_databases",
    title: "Media & Catalog Databases",
    description: "External APIs for music, movies, board games, and barcode lookups.",
    items: [
      { key: "DISCOGS_USER_TOKEN", label: "Discogs User Token", type: "api", placeholder: "Enter Discogs token" },
      { key: "TMDB_API_KEY", label: "TMDB API Key", type: "api", placeholder: "Enter TMDB API key" },
      { key: "BGG_API_TOKEN", label: "BoardGameGeek Token", type: "api", placeholder: "Enter BGG token" },
      {
        key: "UPC_DATABASE_ORG_KEY",
        label: "UPC Database API Key",
        type: "api",
        placeholder: "Enter UPC Database key",
      },
    ],
  },
  {
    id: "ai_image",
    title: "AI & Cover Generation",
    description: "Configure LLM providers and local image generation services.",
    items: [
      { key: "OPENAI_API_KEY", label: "OpenAI API Key", type: "api", placeholder: "Enter OpenAI API key" },
      { key: "LOCAL_SD_URL", label: "Local Stable Diffusion URL", type: "text", placeholder: "http://localhost:7860" },
    ],
  },
];

const SETTING_GROUPS = {
  external_apis: API_SERVICE_GROUPS.flatMap(g => g.items),
  federation: [
    { key: "FEDERATION_BASE_URL", label: "Instance URL", type: "text" as const, placeholder: "https://..." },
    { key: "FEDERATION_ENABLED", label: "Enable Federation", type: "boolean" as const, placeholder: "" },
  ],
  affiliate: [
    { key: "AFFILIATE_AMAZON", label: "Amazon Affiliate ID", type: "text" as const, placeholder: "e.g., iqoqo-20" },
  ],
  internal: [
    {
      key: "IQOQO_KNOWN_JUNK_PHASHES",
      label: "Known Junk Image Hashes",
      type: "text" as const,
      placeholder: "Comma-separated pHash values",
    },
    {
      key: "MAINTENANCE_MODE",
      label: "Maintenance Mode",
      type: "boolean" as const,
      placeholder: "",
    },
  ],
};

function CardWrapper({
  title,
  description,
  onSave,
  saving = false,
  children,
  extraFooterContent,
}: {
  title: string;
  description: string;
  onSave: () => void;
  saving?: boolean;
  children: React.ReactNode;
  extraFooterContent?: React.ReactNode;
}) {
  return (
    <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col">
      <div className="p-6 flex-1">
        <h3 className="text-lg font-medium tracking-tight flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-muted-foreground" />
          {title}
        </h3>
        <p className="text-sm text-muted-foreground mt-1">{description}</p>
        <div className="mt-5 space-y-4">{children}</div>
      </div>
      <div className="bg-muted/40 dark:bg-white/[0.02] border-t border-border dark:border-white/10 px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>{extraFooterContent}</div>
        <Button size="sm" onClick={onSave} disabled={saving}>
          {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
          Save Changes
        </Button>
      </div>
    </div>
  );
}

export function InstanceSettings({ category = "external_apis", showApiKeys = false }: InstanceSettingsProps) {
  const [settings, setSettings] = useState<InstanceSettingsData>({});
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [revealedKeys, setRevealedKeys] = useState<Set<string>>(new Set());
  const [revealedValues, setRevealedValues] = useState<Record<string, string>>({});
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [allegroAuthStatus, setAllegroAuthStatus] = useState<string>("");
  const [allegroAuthUrl, setAllegroAuthUrl] = useState<string | null>(null);
  const [isAuthorizingAllegro, setIsAuthorizingAllegro] = useState(false);

  useEffect(() => {
    if (showApiKeys && category !== "external_apis") {
      setLoading(false);
      return;
    }
    getInstanceSettings(category)
      .then(data => setSettings(data as InstanceSettingsData))
      .finally(() => setLoading(false));
  }, [category, showApiKeys]);

  const handleSaveKeys = async (keysToSave: SettingItem[], groupId: string) => {
    setSavingKey(groupId);
    setSavedMessage(null);
    try {
      const toSave: Record<string, unknown> = {};
      for (const s of keysToSave) {
        const setting = settings[s.key];
        let val: string | boolean = "";
        if (setting && typeof setting === "object" && "value" in setting) {
          val = String(setting.value || "");
        } else if (typeof setting === "boolean") {
          val = setting;
        } else if (typeof setting === "string") {
          val = setting;
        }

        if (revealedKeys.has(s.key) && revealedValues[s.key] !== undefined) {
          val = revealedValues[s.key];
        }

        if (s.type === "boolean") {
          toSave[s.key] = val === true || val === "true";
        } else {
          toSave[s.key] = val ?? "";
        }
      }
      await updateInstanceSettings(toSave, category);
      setSavedMessage(`Saved settings for ${groupId}`);
      setTimeout(() => setSavedMessage(null), 3000);
    } catch (e) {
      console.error("Failed to save settings", e);
    } finally {
      setSavingKey(null);
    }
  };

  const toggleReveal = async (key: string) => {
    if (revealedKeys.has(key)) {
      setRevealedKeys(prev => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
      return;
    }

    try {
      const data = await revealSettingValue(key);
      setRevealedValues(prev => ({ ...prev, [key]: data.value }));
      setRevealedKeys(prev => {
        const next = new Set(prev);
        next.add(key);
        return next;
      });
    } catch (e) {
      console.error("Failed to reveal setting", e);
    }
  };

  const getSettingValue = (key: string): { value: string; source: string } => {
    const setting = settings[key];
    if (setting && typeof setting === "object" && "value" in setting) {
      return { value: String(setting.value || ""), source: setting.source || "missing" };
    }
    return { value: String(setting || ""), source: "missing" };
  };

  const startAllegroAuth = async () => {
    setAllegroAuthStatus("Initiating device flow...");
    setAllegroAuthUrl(null);
    setIsAuthorizingAllegro(true);
    try {
      const idSetting = settings["ALLEGRO_CLIENT_ID"];
      const secretSetting = settings["ALLEGRO_CLIENT_SECRET"];

      let idVal =
        idSetting !== undefined && (typeof idSetting === "string" ? idSetting : (idSetting as any)?.value) !== undefined
          ? typeof idSetting === "string"
            ? idSetting
            : (idSetting as any).value
          : getSettingValue("ALLEGRO_CLIENT_ID").value;

      let secretVal =
        secretSetting !== undefined &&
        (typeof secretSetting === "string" ? secretSetting : (secretSetting as any)?.value) !== undefined
          ? typeof secretSetting === "string"
            ? secretSetting
            : (secretSetting as any).value
          : getSettingValue("ALLEGRO_CLIENT_SECRET").value;

      if (revealedKeys.has("ALLEGRO_CLIENT_ID") && revealedValues["ALLEGRO_CLIENT_ID"]) {
        idVal = revealedValues["ALLEGRO_CLIENT_ID"];
      }
      if (revealedKeys.has("ALLEGRO_CLIENT_SECRET") && revealedValues["ALLEGRO_CLIENT_SECRET"]) {
        secretVal = revealedValues["ALLEGRO_CLIENT_SECRET"];
      }

      const res = await fetch("/api/auth/allegro/device-flow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: idVal, client_secret: secretVal }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to start device flow");
      }
      const data = await res.json();

      const verificationUrl = data.verification_uri_complete || data.verification_uri;
      const userCode = data.user_code;
      setAllegroAuthUrl(verificationUrl);
      setAllegroAuthStatus(`Authorize code: ${userCode || ""}. Waiting for confirmation...`);

      if (verificationUrl) {
        window.open(verificationUrl, "_blank");
      }

      const interval = data.interval ? parseInt(data.interval) * 1000 : 5000;
      let expires = data.expires_in ? parseInt(data.expires_in) : 600;

      const poll = async () => {
        if (expires <= 0) {
          setAllegroAuthStatus("Authorization expired. Please try again.");
          setIsAuthorizingAllegro(false);
          return;
        }
        const pollRes = await fetch("/api/auth/allegro/device-token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ client_id: idVal, client_secret: secretVal, device_code: data.device_code }),
        });

        if (pollRes.status === 200) {
          setAllegroAuthStatus("Allegro authorized successfully!");
          setIsAuthorizingAllegro(false);
        } else if (pollRes.status === 202) {
          expires -= interval / 1000;
          setTimeout(poll, interval);
        } else {
          setAllegroAuthStatus("Authorization failed or denied.");
          setIsAuthorizingAllegro(false);
        }
      };

      setTimeout(poll, interval);
    } catch (e) {
      setAllegroAuthStatus("Error: " + (e instanceof Error ? e.message : String(e)));
      setIsAuthorizingAllegro(false);
    }
  };

  if (loading) {
    return <Loader2 className="animate-spin h-6 w-6 text-muted-foreground my-10 mx-auto" />;
  }

  const getSourceBadge = (source: string) => {
    if (source === "db")
      return { label: "DB", className: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" };
    if (source === "env")
      return { label: "ENV", className: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" };
    return { label: "—", className: "bg-muted text-muted-foreground" };
  };

  const renderInputField = (s: SettingItem) => {
    const { value, source } = getSettingValue(s.key);
    const isMasked = s.type === "api" && value.startsWith("***");
    const isRevealed = revealedKeys.has(s.key);
    const badge = getSourceBadge(source);

    return (
      <div key={s.key} className="flex flex-col gap-1.5">
        <label className="text-xs font-semibold text-muted-foreground tracking-wide uppercase">{s.label}</label>
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              autoComplete="off"
              className="flex h-9 w-full max-w-md rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring pr-10"
              value={isRevealed ? revealedValues[s.key] || value : value}
              onChange={e => {
                const newVal = e.target.value;
                if (isRevealed) {
                  setRevealedValues({ ...revealedValues, [s.key]: newVal });
                }
                setSettings({ ...settings, [s.key]: newVal });
              }}
              placeholder={s.placeholder}
            />
            {(isMasked || source !== "missing") && (
              <button
                type="button"
                onClick={() => toggleReveal(s.key)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1"
                title={isRevealed ? "Hide value" : "Reveal stored value"}
              >
                {isRevealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            )}
          </div>
          <span className={`text-xs px-2 py-1 rounded font-mono ${badge.className}`}>{badge.label}</span>
        </div>
      </div>
    );
  };

  if (showApiKeys && category === "external_apis") {
    return (
      <div className="flex flex-col gap-8">
        {savedMessage && (
          <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-600 dark:text-green-400 text-sm flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            {savedMessage}
          </div>
        )}

        {API_SERVICE_GROUPS.map(group => {
          const isAllegro = group.id === "allegro";

          return (
            <CardWrapper
              key={group.id}
              title={group.title}
              description={group.description}
              saving={savingKey === group.id}
              onSave={() => handleSaveKeys(group.items, group.id)}
              extraFooterContent={
                isAllegro ? (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={startAllegroAuth}
                    disabled={isAuthorizingAllegro}
                  >
                    {isAuthorizingAllegro ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <ExternalLink className="h-4 w-4 mr-2" />
                    )}
                    Authorize Allegro Account
                  </Button>
                ) : null
              }
            >
              <div className="flex flex-col gap-4">
                {group.items.map(s => renderInputField(s))}
                {isAllegro && (allegroAuthStatus || allegroAuthUrl) && (
                  <div className="mt-2 p-3 rounded-lg border border-border dark:border-white/10 bg-muted/30 text-sm flex flex-col gap-2">
                    {allegroAuthStatus && (
                      <div className="flex items-center gap-2 font-medium">
                        {allegroAuthStatus.includes("Error") || allegroAuthStatus.includes("failed") ? (
                          <AlertCircle className="h-4 w-4 text-destructive" />
                        ) : allegroAuthStatus.includes("successfully") ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        )}
                        <span>{allegroAuthStatus}</span>
                      </div>
                    )}
                    {allegroAuthUrl && (
                      <p className="text-xs text-muted-foreground">
                        If browser window did not open automatically,{" "}
                        <a
                          href={allegroAuthUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary underline font-medium inline-flex items-center gap-1"
                        >
                          click here to authorize on Allegro <ExternalLink className="h-3 w-3 inline" />
                        </a>
                      </p>
                    )}
                  </div>
                )}
              </div>
            </CardWrapper>
          );
        })}
      </div>
    );
  }

  const defaultList = SETTING_GROUPS[category] || [];
  return (
    <div className="flex flex-col gap-8">
      {savedMessage && (
        <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-600 dark:text-green-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          {savedMessage}
        </div>
      )}

      {defaultList.map(s => {
        const { value, source } = getSettingValue(s.key);
        const badge = getSourceBadge(source);

        return (
          <CardWrapper
            key={s.key}
            title={s.label}
            description=""
            saving={savingKey === s.key}
            onSave={() => handleSaveKeys([s], s.key)}
          >
            <div className="flex items-center gap-3">
              {s.type === "boolean" ? (
                <select
                  className="flex h-9 w-full max-w-[200px] rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={String(value).toLowerCase() === "true" ? "true" : "false"}
                  onChange={e => setSettings({ ...settings, [s.key]: e.target.value })}
                >
                  <option value="true">Enabled</option>
                  <option value="false">Disabled</option>
                </select>
              ) : (
                <input
                  type="text"
                  className="flex h-9 w-full max-w-md rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={value}
                  onChange={e => setSettings({ ...settings, [s.key]: e.target.value })}
                  placeholder={s.placeholder}
                />
              )}
              <span className={`text-xs px-2 py-1 rounded font-mono ${badge.className}`}>{badge.label}</span>
            </div>
          </CardWrapper>
        );
      })}
    </div>
  );
}
