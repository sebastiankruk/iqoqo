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

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { apiFetch, apiClient } from "@/lib/api/client";
import { downloadCollectionExport, ExportFormat, EXPORT_FORMAT_OPTIONS } from "@/lib/api/export";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Avatar } from "@/components/ui/avatar";
import { useAppConfig } from "@/lib/api/hooks";
import { useQueryClient } from "@tanstack/react-query";
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
  public_username: string | null;
  bio: string | null;
  avatar_url: string | null;
  visibility: "public" | "private";
  created_at: string;
  consents: ConsentRecord;
}

/**
 * Profile page component.
 * Consolidates username, bio, avatar URL, profile visibility, RDF export, and GDPR consents.
 *
 * @returns {JSX.Element} The page component
 */
export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const { data: config } = useAppConfig();
  const queryClient = useQueryClient();

  // Editable profile form state
  const [displayName, setDisplayName] = useState("");
  const [publicUsername, setPublicUsername] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [visibility, setVisibility] = useState<"public" | "private">("private");
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("json-ld");
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    // Note the trailing slash to match Flask's route: /profile/
    apiFetch<UserProfile>("/profile/")
      .then(data => {
        setProfile(data);
        setDisplayName(data.display_name || "");
        setPublicUsername(data.public_username || "");
        setBio(data.bio || "");
        setAvatarUrl(data.avatar_url || "");
        setVisibility(data.visibility || "private");
      })
      .catch(err => console.error("Failed to load profile", err));
  }, []);

  /**
   * Handles saving the user's profile.
   * @returns {Promise<void>} A promise that resolves when the profile is saved.
   */
  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      await apiClient.put("/profile/", {
        display_name: displayName.trim(),
        public_username: publicUsername.trim() || null,
        bio: bio.trim(),
        avatar_url: avatarUrl.trim(),
        visibility,
      });
      setProfile(prev =>
        prev
          ? {
              ...prev,
              display_name: displayName.trim(),
              public_username: publicUsername.trim() || null,
              bio: bio.trim(),
              avatar_url: avatarUrl.trim(),
              visibility,
            }
          : null
      );
      // Invalidate so the navbar and other consumers refresh immediately
      await queryClient.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Profile updated successfully");
      setUsernameError(null);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Failed to update profile";
      toast.error(errorMsg);
      if (errorMsg.toLowerCase().includes("username")) {
        setUsernameError(errorMsg);
      }
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownloadExport = useCallback(async () => {
    try {
      setIsExporting(true);
      await downloadCollectionExport(selectedFormat);
    } catch {
      // Toast notification is managed inside downloadCollectionExport
    } finally {
      setIsExporting(false);
    }
  }, [selectedFormat]);

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

  const isProfileDirty =
    displayName !== (profile.display_name || "") ||
    publicUsername !== (profile.public_username || "") ||
    bio !== (profile.bio || "") ||
    avatarUrl !== (profile.avatar_url || "") ||
    visibility !== (profile.visibility || "private");

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-2xl mx-auto p-6 space-y-8">
        {/* ── Header ── */}
        <div className="flex items-center space-x-4">
          <Avatar
            src={avatarUrl || profile.avatar_url}
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

        {/* ── Profile Settings Card ── */}
        <div className="border border-border rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden">
          <div className="p-6 flex flex-col gap-6">
            <div>
              <h2 className="text-xl font-semibold">Profile Settings</h2>
              <p className="text-sm text-muted-foreground mt-1">Manage your public identity and account preferences.</p>
            </div>

            {/* Display Name */}
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="display-name">
                Display Name
              </label>
              <input
                id="display-name"
                type="text"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                placeholder="Enter your display name"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            {/* Public Username */}
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="public-username">
                Public Username
              </label>
              <p className="text-xs text-muted-foreground mb-2">
                Setting a public username allows sharing your collection at <code>/u/[username]</code>.
              </p>
              <div className="flex items-center gap-2 max-w-md">
                <span className="text-sm text-muted-foreground">
                  {typeof window !== "undefined" ? window.location.host : "iqoqo.app"}/u/
                </span>
                <input
                  id="public-username"
                  type="text"
                  value={publicUsername}
                  onChange={e => {
                    setPublicUsername(e.target.value);
                    if (usernameError) setUsernameError(null);
                  }}
                  placeholder="your-username"
                  className={`flex h-9 flex-1 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring${usernameError ? " border-red-500 focus-visible:ring-red-500" : ""}`}
                />
              </div>
              {usernameError && <p className="mt-2 text-xs font-medium text-red-500">{usernameError}</p>}
            </div>

            {/* Avatar URL */}
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="avatar-url">
                Avatar URL
              </label>
              <input
                id="avatar-url"
                type="text"
                value={avatarUrl}
                onChange={e => setAvatarUrl(e.target.value)}
                placeholder="https://example.com/avatar.jpg"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            {/* Bio */}
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="bio">
                Bio
              </label>
              <textarea
                id="bio"
                value={bio}
                onChange={e => setBio(e.target.value)}
                placeholder="Tell the world about your library..."
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            {/* Visibility */}
            <div>
              <p className="text-sm font-medium mb-2">Profile Visibility</p>
              <div className="flex flex-col gap-2">
                <label className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="radio"
                    name="visibility"
                    value="private"
                    checked={visibility === "private"}
                    onChange={() => setVisibility("private")}
                    className="h-4 w-4 text-primary border-input bg-background focus:ring-primary"
                  />
                  <div>
                    <p className="text-sm font-medium">Private</p>
                    <p className="text-xs text-muted-foreground">Only you can see your collection.</p>
                  </div>
                </label>
                <label className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="radio"
                    name="visibility"
                    value="public"
                    checked={visibility === "public"}
                    onChange={() => setVisibility("public")}
                    className="h-4 w-4 text-primary border-input bg-background focus:ring-primary"
                  />
                  <div>
                    <p className="text-sm font-medium">Public</p>
                    <p className="text-xs text-muted-foreground">Anyone with the link can view your collection.</p>
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* Single primary CTA per card */}
          <div className="bg-muted/40 dark:bg-white/[0.02] border-t border-border px-6 py-3 flex justify-end">
            <Button onClick={handleSaveProfile} disabled={isSaving || !isProfileDirty}>
              {isSaving ? "Saving..." : "Save Profile"}
            </Button>
          </div>
        </div>

        {/* ── Privacy & Consents Card ── */}
        <div className="p-4 border rounded-lg bg-card space-y-4" data-testid="privacy-consents-card">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Privacy &amp; Consents (GDPR)</h2>
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

        {/* ── Export Collection Card ── */}
        <div className="p-4 border rounded-lg bg-card space-y-4" data-testid="export-collection-card">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold">Export Collection</h2>
            <p className="text-sm text-muted-foreground">
              Download your full library as Linked Open Data or hierarchical JSON for complete data sovereignty and
              portability.
            </p>
          </div>

          <div className="space-y-3">
            <div className="space-y-1.5">
              <label htmlFor="export-format-select" className="block text-sm font-medium text-foreground">
                Export Format
              </label>
              <select
                id="export-format-select"
                aria-label="Export Format"
                value={selectedFormat}
                onChange={e => setSelectedFormat(e.target.value as ExportFormat)}
                className="w-full max-w-sm h-10 px-3 py-2 text-sm rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                disabled={isExporting}
              >
                {EXPORT_FORMAT_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground" data-testid="export-format-description">
                {EXPORT_FORMAT_OPTIONS.find(opt => opt.value === selectedFormat)?.description}
              </p>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <Button onClick={handleDownloadExport} disabled={isExporting} aria-label="Export Collection Button">
                <Download className="w-4 h-4 mr-2" />
                {isExporting ? "Exporting..." : "Download Export"}
              </Button>
            </div>
          </div>
        </div>

        {/* ── My Help Requests ── */}
        <div id="help-requests">
          <MyEscalations />
        </div>

        {/* ── Account Actions ── */}
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
