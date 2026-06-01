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
import { getFederationConsent, updateFederationConsent } from "@/lib/api/federation";
import { Loader2 } from "lucide-react";
import type { FederationConsent } from "@/types/federation";

/**
 * User-facing federation consent toggle settings.
 * @returns {JSX.Element} The component
 */
export function FederationConsentSettings() {
  const [consent, setConsent] = useState<FederationConsent | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getFederationConsent()
      .then(data => setConsent(data))
      .finally(() => setLoading(false));
  }, []);

  const handleToggle = async (field: "federated_profile" | "federated_collection", value: boolean) => {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await updateFederationConsent({ [field]: value });
      setConsent(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error("Failed to update consent", e);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <Loader2 className="animate-spin h-6 w-6 text-muted-foreground my-10 mx-auto" />;
  }

  return (
    <div className="space-y-6">
      <div className="border border-border rounded-xl p-6 space-y-4">
        <h3 className="text-lg font-medium">Federation Privacy</h3>
        <p className="text-sm text-muted-foreground">
          Control how your profile and collection are visible to other iqoqo instances through federation.
        </p>

        <div className="space-y-4 mt-4">
          <label className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Make profile discoverable</p>
              <p className="text-xs text-muted-foreground">Allow other instances to find your profile via federation</p>
            </div>
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300"
              checked={consent?.federated_profile ?? false}
              onChange={e => handleToggle("federated_profile", e.target.checked)}
              disabled={saving}
            />
          </label>

          <label className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Share collection updates</p>
              <p className="text-xs text-muted-foreground">Broadcast collection changes to federated followers</p>
            </div>
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300"
              checked={consent?.federated_collection ?? false}
              onChange={e => handleToggle("federated_collection", e.target.checked)}
              disabled={saving}
            />
          </label>
        </div>

        {saved && <p className="text-sm text-green-500">Settings saved</p>}
      </div>
    </div>
  );
}
