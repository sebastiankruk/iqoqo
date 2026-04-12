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

import { useState, useEffect, type ReactNode } from "react";
import { getInstanceSettings, updateInstanceSettings } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface InstanceSettingsData {
  instance_name?: string;
  amazon_affiliate_id?: string;
  enable_federation?: string | boolean;
  [key: string]: unknown;
}

interface CardWrapperProps {
  /** Card title */
  title: string;
  /** Card description */
  description: string;
  /** Footer helper text */
  footerText: string;
  /** Save button handler */
  onSave: () => void;
  /** Card body content */
  children: ReactNode;
}

/**
 * Card wrapper for settings sections.
 * @param props - Card wrapper properties
 * @param props.title - Card title
 * @param props.description - Card description
 * @param props.footerText - Footer helper text
 * @param props.onSave - Save button handler
 * @param props.children - Card body content
 * @returns Card wrapper component
 */
function CardWrapper({ title, description, footerText, onSave, children }: CardWrapperProps) {
  return (
    <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col">
      <div className="p-6 flex-1">
        <h3 className="text-lg font-medium tracking-tight">{title}</h3>
        <p className="text-sm text-muted-foreground mt-1">{description}</p>
        <div className="mt-5">{children}</div>
      </div>
      <div className="bg-muted/40 dark:bg-white/[0.02] border-t border-border dark:border-white/10 px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">{footerText}</p>
        <Button size="sm" onClick={onSave}>
          Save
        </Button>
      </div>
    </div>
  );
}

/**
 * Instance settings component for managing global configuration.
 *
 * @returns {JSX.Element} The instance settings component
 */
export function InstanceSettings() {
  const [settings, setSettings] = useState<InstanceSettingsData>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getInstanceSettings()
      .then(setSettings)
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    try {
      await updateInstanceSettings(settings);
    } catch (e) {
      console.error("Failed to save settings", e);
    }
  };

  if (loading) {
    return <Loader2 className="animate-spin h-6 w-6 text-muted-foreground my-10 mx-auto" />;
  }

  return (
    <div className="flex flex-col gap-8">
      <CardWrapper
        title="Instance Name"
        description="Used to identify your library on the web and within federated networks."
        footerText="Maximum 32 characters."
        onSave={handleSave}
      >
        <input
          type="text"
          className="flex h-9 w-full max-w-md rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          value={settings.instance_name ?? ""}
          onChange={e => setSettings({ ...settings, instance_name: e.target.value })}
          placeholder="e.g., My Personal Library"
        />
      </CardWrapper>

      <CardWrapper
        title="Amazon Affiliate ID"
        description="Monetize external store links by automatically appending your affiliate tracking ID."
        footerText="Leave blank to disable Amazon integrations."
        onSave={handleSave}
      >
        <input
          type="text"
          className="flex h-9 w-full max-w-md rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          value={settings.amazon_affiliate_id ?? ""}
          onChange={e => setSettings({ ...settings, amazon_affiliate_id: e.target.value })}
          placeholder="e.g., iqoqo-20"
        />
      </CardWrapper>

      <CardWrapper
        title="Federation"
        description="Allow other iqoqo instances to query your public catalog via ActivityPub and Linked Open Data."
        footerText="This requires your server to be publicly accessible."
        onSave={handleSave}
      >
        <select
          className="flex h-9 w-full max-w-[200px] rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          value={String(settings.enable_federation ?? "false")}
          onChange={e => setSettings({ ...settings, enable_federation: e.target.value })}
        >
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </select>
      </CardWrapper>
    </div>
  );
}
