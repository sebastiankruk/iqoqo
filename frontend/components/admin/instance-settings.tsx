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
import { Loader2 } from "lucide-react";

/**
 * Instance settings data
 */
interface InstanceSettingsData {
  instance_name?: string;
  amazon_affiliate_id?: string;
  enable_federation?: string | boolean;
  [key: string]: unknown;
}

/**
 * Component for managing global instance settings.
 *
 * @returns {JSX.Element} The component
 */
export function InstanceSettings() {
  const [settings, setSettings] = useState<InstanceSettingsData>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getInstanceSettings()
      .then(setSettings)
      .finally(() => setLoading(false));
  }, []);

  /**
   * Handles saving the settings.
   */
  const handleSave = async () => {
    setSaving(true);
    try {
      await updateInstanceSettings(settings);
    } catch (e) {
      console.error("Failed to save settings", e);
    } finally {
      setSaving(false);
    }
  };

  if (loading)
    return (
      <div className="p-4 flex justify-center">
        <Loader2 className="animate-spin" />
      </div>
    );

  return (
    <div className="flex flex-col gap-5 max-w-lg">
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium">Instance Name</label>
        <input
          type="text"
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          value={settings.instance_name ?? ""}
          onChange={e => setSettings({ ...settings, instance_name: e.target.value })}
          placeholder="e.g., My Personal Library"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium">Amazon Affiliate ID</label>
        <input
          type="text"
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          value={settings.amazon_affiliate_id ?? ""}
          onChange={e => setSettings({ ...settings, amazon_affiliate_id: e.target.value })}
          placeholder="e.g., iqoqo-20"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium">Enable Federation (Share metadata globally)</label>
        <select
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={String(settings.enable_federation ?? "false")}
          onChange={e => setSettings({ ...settings, enable_federation: e.target.value })}
        >
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </select>
      </div>

      <Button onClick={handleSave} disabled={saving} className="w-fit mt-2">
        {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Save Configuration
      </Button>
    </div>
  );
}
