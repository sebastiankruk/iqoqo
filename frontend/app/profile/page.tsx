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

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { apiFetch, apiClient } from "@/lib/api/client"; // Use your configured client
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Avatar } from "@/components/ui/avatar";
import { useAppConfig } from "@/lib/api/hooks";
import { MyEscalations } from "@/components/escalation/my-escalations";

/**
 * User consent record
 */
interface ConsentRecord {
  consent_type: string;
  is_granted: boolean;
  policy_version: string;
  timestamp: string;
  telemetry: boolean;
  federation: boolean;
}

/**
 * User profile details
 */
interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  visibility: "public" | "private";
  created_at: string;
  consents: ConsentRecord;
}

/**
 * Profile page component.
 *
 * @returns {JSX.Element} The page component
 */
export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editNameValue, setEditNameValue] = useState("");
  const { data: config } = useAppConfig();

  useEffect(() => {
    // Note the trailing slash to match Flask's route: /profile/
    apiFetch<UserProfile>("/profile/")
      .then(data => {
        setProfile(data);
        setEditNameValue(data.display_name || "");
      })
      .catch(err => console.error("Failed to load profile", err));
  }, []);

  /**
   * Handles the user logout.
   *
   * @returns {Promise<void>} A promise that resolves when the logout process is complete.
   */
  const handleLogout = async () => {
    try {
      // Call the Next.js logout route to clear the session cookie
      await fetch("/api/auth/logout", { method: "POST" });
      window.location.href = "/";
    } catch {
      toast.error("Failed to logout");
    }
  };

  /**
   * Handles the update of the user's display name.
   * @returns {Promise<void>} A promise that resolves when the name update is complete.
   */

  const handleUpdateName = async () => {
    try {
      await apiClient.put("/profile/", { display_name: editNameValue });
      setProfile(prev => (prev ? { ...prev, display_name: editNameValue } : null));
      setIsEditingName(false);
      toast.success("Profile updated");
    } catch {
      toast.error("Failed to update profile");
    }
  };

  /**
   * Handles the deletion of the user's account.
   * @returns {Promise<void>} A promise that resolves when the account deletion is complete.
   */

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm(
      "Are you absolutely sure? This will permanently delete your account, your library collection, and all your data. This cannot be undone."
    );
    if (!confirmed) return;

    try {
      await apiClient.delete("/profile/");
      toast.success("Account deleted permanently.");
      handleLogout();
    } catch {
      toast.error("Failed to delete account");
    }
  };

  /**
   * Toggles the consent for a given type.
   * @param {string} type - The type of consent to toggle.
   * @param {boolean} currentStatus - The current status of the consent.
   */

  const toggleConsent = async (type: string, currentStatus: boolean) => {
    try {
      await apiClient.post("/profile/consent", {
        consent_type: type,
        is_granted: !currentStatus,
      });
      setProfile(prev => {
        if (!prev) return null;
        return {
          ...prev,
          consents: {
            ...prev.consents,
            [type]: !currentStatus,
          },
        };
      });
      toast.success("Privacy preferences updated");
    } catch {
      toast.error("Failed to update preferences");
    }
  };

  if (!profile) return <div className="p-8 text-center text-muted-foreground">Loading...</div>;

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-2xl mx-auto p-6 space-y-8">
        <div className="flex items-center space-x-4">
          <Avatar
            src={profile.avatar_url}
            alt="Avatar"
            size={64}
            className="border"
            fallback={profile.email[0].toUpperCase()}
          />
          <div>
            <h1 className="text-3xl font-bold">My Profile</h1>
            <p className="text-muted-foreground">{profile.email}</p>
          </div>
        </div>

        <div className="p-4 border rounded-lg bg-card">
          <h2 className="text-xl font-semibold mb-4">Account Details</h2>
          <div className="space-y-4">
            <div>
              <span className="block text-sm font-medium text-muted-foreground">Display Name</span>
              {isEditingName ? (
                <div className="flex items-center space-x-2 mt-1">
                  <input
                    type="text"
                    value={editNameValue}
                    onChange={e => setEditNameValue(e.target.value)}
                    className="border rounded px-2 py-1 flex-1 text-sm bg-background"
                  />
                  <Button size="sm" onClick={handleUpdateName}>
                    Save
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setIsEditingName(false)}>
                    Cancel
                  </Button>
                </div>
              ) : (
                <div className="flex items-center justify-between mt-1">
                  <span>{profile.display_name || "N/A"}</span>
                  <Button size="sm" variant="outline" onClick={() => setIsEditingName(true)}>
                    Edit
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="p-4 border rounded-lg bg-card space-y-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Privacy & Consents (GDPR)</h2>
            <Link
              href="/legal/privacy"
              target="_blank"
              className="text-sm text-muted-foreground underline hover:text-primary"
            >
              Read Policy
            </Link>
          </div>
          {config?.federation_enabled && (
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <p className="font-medium">Allow Federal Discovery (ActivityPub)</p>
                <p className="text-xs text-muted-foreground">Shares your public collection with the broader network.</p>
              </div>
              <Button
                variant={profile.consents?.federation ? "default" : "outline"}
                onClick={() => toggleConsent("federation", profile.consents?.federation)}
              >
                {profile.consents?.federation ? "Opted In" : "Opted Out"}
              </Button>
            </div>
          )}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="font-medium">Allow Anonymous Telemetry for AI</p>
              <p className="text-xs text-muted-foreground">Metadata shared to generate covers or recommendations.</p>
            </div>
            <Button
              variant={profile.consents?.telemetry ? "default" : "outline"}
              onClick={() => toggleConsent("telemetry", profile.consents?.telemetry)}
            >
              {profile.consents?.telemetry ? "Opted In" : "Opted Out"}
            </Button>
          </div>
        </div>

        <div id="help-requests">
          <MyEscalations />
        </div>

        <div className="flex justify-between items-center pt-4">
          <Button variant="outline" onClick={handleLogout}>
            Log Out
          </Button>

          <div className="text-right">
            <Button variant="destructive" onClick={handleDeleteAccount}>
              Delete Account
            </Button>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
