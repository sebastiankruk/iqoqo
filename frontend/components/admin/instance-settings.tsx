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
import { getInstanceSettings, updateInstanceSettings } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { Loader2, Eye, EyeOff, Save } from "lucide-react";

interface InstanceSettingsProps {
  category?: "external_apis" | "federation" | "affiliate" | "internal";
  showApiKeys?: boolean;
}

interface InstanceSettingsData {
  [key: string]: string | boolean | null;
}

const SETTING_GROUPS = {
  external_apis: [
    { key: "GOOGLE_BOOKS_API_KEY", label: "Google Books API Key", type: "api" as const, placeholder: "Enter API key" },
    { key: "DISCOGS_USER_TOKEN", label: "Discogs User Token", type: "api" as const, placeholder: "Enter token" },
    { key: "TMDB_API_KEY", label: "TMDB API Key", type: "api" as const, placeholder: "Enter API key" },
    { key: "BGG_API_TOKEN", label: "BGG API Token", type: "api" as const, placeholder: "Enter token" },
    { key: "OPENAI_API_KEY", label: "OpenAI API Key", type: "api" as const, placeholder: "Enter API key" },
    { key: "GEMINI_API_KEY", label: "Google Gemini API Key", type: "api" as const, placeholder: "Enter API key" },
    { key: "UPC_DATABASE_ORG_KEY", label: "UPC Database API Key", type: "api" as const, placeholder: "Enter API key" },
    { key: "ALLEGRO_CLIENT_ID", label: "Allegro Client ID", type: "api" as const, placeholder: "Enter client ID" },
    {
      key: "ALLEGRO_CLIENT_SECRET",
      label: "Allegro Client Secret",
      type: "api" as const,
      placeholder: "Enter client secret",
    },
    {
      key: "LOCAL_SD_URL",
      label: "Local Stable Diffusion URL",
      type: "text" as const,
      placeholder: "http://localhost:7860",
    },
  ],
  federation: [
    { key: "FEDERATION_BASE_URL", label: "Instance URL", type: "text" as const, placeholder: "https://..." },
    { key: "FEDERATION_ENABLED", label: "Enable Federation", type: "boolean" as const },
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
  ],
};

/**
 * Card wrapper for settings sections.
 *
 * @param props - Card wrapper properties
 * @param props.title - Card title
 * @param props.description - Card description
 * @param props.onSave - Save button handler
 * @param props.children - Card body content
 * @returns Card wrapper component
 */
function CardWrapper({
  title,
  description,
  onSave,
  children,
}: {
  title: string;
  description: string;
  onSave: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col">
      <div className="p-6 flex-1">
        <h3 className="text-lg font-medium tracking-tight">{title}</h3>
        <p className="text-sm text-muted-foreground mt-1">{description}</p>
        <div className="mt-5">{children}</div>
      </div>
      <div className="bg-muted/40 dark:bg-white/[0.02] border-t border-border dark:border-white/10 px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground"></p>
        <Button size="sm" onClick={onSave}>
          <Save className="h-4 w-4 mr-2" />
          Save
        </Button>
      </div>
    </div>
  );
}

/**
 * Instance settings component for managing global configuration.
 *
 * @param props - Component props
 * @param props.category - Settings category (external_apis, federation, affiliate, internal)
 * @param props.showApiKeys - Whether to show API keys interface
 * @returns The instance settings component
 */
export function InstanceSettings({ category = "external_apis", showApiKeys = false }: InstanceSettingsProps) {
  const [settings, setSettings] = useState<InstanceSettingsData>({});
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [saving, setSaving] = useState(false);
  const [revealedKeys, setRevealedKeys] = useState<Set<string>>(new Set());
  const [saved, setSaved] = useState(false);

  const settingsList = SETTING_GROUPS[category] || [];

  useEffect(() => {
    if (showApiKeys && category !== "external_apis") {
      setLoading(false);
      return;
    }
    getInstanceSettings(category)
      .then(data => setSettings(data as InstanceSettingsData))
      .finally(() => setLoading(false));
  }, [category, showApiKeys]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const toSave: Record<string, unknown> = {};
      for (const s of settingsList) {
        const val = settings[s.key];
        if (s.type === "boolean") {
          toSave[s.key] = val === true || val === "true";
        } else {
          toSave[s.key] = val ?? "";
        }
      }
      await updateInstanceSettings(toSave, category);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error("Failed to save settings", e);
    } finally {
      setSaving(false);
    }
  };

  const toggleReveal = (key: string) => {
    setRevealedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const isApiValue = (key: string, value: unknown): boolean => {
    return (
      SETTING_GROUPS.external_apis.some(s => s.key === key && s.type === "api") &&
      typeof value === "string" &&
      value.startsWith("***")
    );
  };

  if (loading) {
    return <Loader2 className="animate-spin h-6 w-6 text-muted-foreground my-10 mx-auto" />;
  }

  if (showApiKeys && category === "external_apis") {
    const apiSettings = SETTING_GROUPS.external_apis;
    return (
      <div className="flex flex-col gap-8">
        {apiSettings.map(s => {
          const value = (settings[s.key] as string) || "";
          const isMasked = isApiValue(s.key, value);
          const isRevealed = revealedKeys.has(s.key);

          return (
            <CardWrapper
              key={s.key}
              title={s.label}
              description={`Configure your ${s.label.toLowerCase()}`}
              onSave={handleSave}
            >
              <div className="relative">
                <input
                  type={isRevealed && !isMasked ? "text" : "password"}
                  className="flex h-9 w-full max-w-md rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring pr-10"
                  value={value}
                  onChange={e => setSettings({ ...settings, [s.key]: e.target.value })}
                  placeholder={s.placeholder}
                />
                {isMasked && (
                  <button
                    type="button"
                    onClick={() => toggleReveal(s.key)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {isRevealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                )}
              </div>
            </CardWrapper>
          );
        })}
        {saved && <p className="text-sm text-green-500">Settings saved successfully</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {settingsList.map(s => {
        if (s.type === "boolean") {
          return (
            <CardWrapper key={s.key} title={s.label} description={""} onSave={handleSave}>
              <select
                className="flex h-9 w-full max-w-[200px] rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={String(settings[s.key] ?? "false")}
                onChange={e => setSettings({ ...settings, [s.key]: e.target.value })}
              >
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </CardWrapper>
          );
        }

        return (
          <CardWrapper key={s.key} title={s.label} description={""} onSave={handleSave}>
            <input
              type={s.type === "api" ? "password" : "text"}
              className="flex h-9 w-full max-w-md rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={(settings[s.key] as string) || ""}
              onChange={e => setSettings({ ...settings, [s.key]: e.target.value })}
              placeholder={s.placeholder}
            />
          </CardWrapper>
        );
      })}
      {saved && <p className="text-sm text-green-500">Settings saved successfully</p>}
    </div>
  );
}
