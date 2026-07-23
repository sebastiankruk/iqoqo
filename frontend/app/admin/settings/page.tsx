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

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useProfile } from "@/lib/api/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";
import {
  Loader2,
  Settings,
  Users,
  User,
  Shield,
  BadgeCheck,
  Key,
  Building2,
  DollarSign,
  Database,
  Search,
  X,
  Image as ImageIcon,
} from "lucide-react";
import { PermissionName } from "@/lib/permissions";
import { InstanceSettings } from "@/components/admin/instance-settings";
import { UserManagement } from "@/components/admin/user-management";
import { MyEscalations } from "@/components/escalation/my-escalations";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { FrbrEditor } from "@/components/admin/frbr-editor";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { searchFrbrEntities, type FrbrSearchResult } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import type React from "react";
import Link from "next/link";

interface NavItemProps {
  label: string;
  icon: LucideIcon;
  isActive: boolean;
  onClick: () => void;
  href?: string;
}

/**
 * Navigation item for settings sidebar.
 * @param props - Navigation item properties
 * @param props.label - Display label
 * @param props.icon - Lucide icon component
 * @param props.isActive - Whether this item is currently active
 * @param props.onClick - Click handler
 * @param props.href - Optional href for external navigation
 * @returns Navigation item JSX element
 */
function NavItem({ label, icon: Icon, isActive, onClick, href }: NavItemProps): React.JSX.Element {
  const className = cn(
    "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
    isActive ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
  );

  const content = (
    <>
      <Icon className="h-4 w-4" />
      {label}
    </>
  );

  if (href) {
    return (
      <Link href={href} onClick={onClick} className={className}>
        {content}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className}>
      {content}
    </button>
  );
}

/**
 * Inner settings content component that uses useSearchParams.
 * Must be wrapped in Suspense boundary.
 * @returns Settings page JSX element
 */
function SettingsContent(): React.JSX.Element {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { data: profile, isLoading } = useProfile();
  const queryClient = useQueryClient();
  const [internalTab, setInternalTab] = useState<string | null>(null);

  // Redirect to login if user is unauthenticated
  useEffect(() => {
    if (!isLoading && !profile) {
      router.push("/login");
    }
  }, [profile, isLoading, router]);
  const [displayName, setDisplayName] = useState<string>("");
  const [publicUsername, setPublicUsername] = useState<string>("");
  const [bio, setBio] = useState<string>("");
  const [avatarUrl, setAvatarUrl] = useState<string>("");
  const [visibility, setVisibility] = useState<string>("private");
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const activeTab = internalTab || searchParams.get("tab") || "profile";

  // Initialize local state when profile loads
  useEffect(() => {
    if (profile) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDisplayName(profile.display_name || "");
      setPublicUsername(profile.public_username || "");
      setBio(profile.bio || "");
      setAvatarUrl(profile.avatar_url || "");
      setVisibility(profile.visibility || "private");
    }
  }, [profile, activeTab]);

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      await apiClient.put("/profile/", {
        display_name: displayName.trim(),
        public_username: publicUsername.trim() || null,
        bio: bio.trim(),
        avatar_url: avatarUrl.trim(),
        visibility: visibility,
      });
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

  const handleTabChange = (tab: string) => {
    setInternalTab(tab);
  };

  if (isLoading || !profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
      </div>
    );
  }

  const permissions = profile.permissions ?? [];
  const hasPermission = (perm: PermissionName): boolean => permissions.includes(perm);

  const canViewSettings =
    hasPermission(PermissionName.CONFIG_EXTERNAL_APIS) ||
    hasPermission(PermissionName.CONFIG_FEDERATION) ||
    hasPermission(PermissionName.CONFIG_AFFILIATE) ||
    hasPermission(PermissionName.CONFIG_INTERNAL);
  const canViewUsers = hasPermission(PermissionName.READ_USERS);
  const canViewRoles = hasPermission(PermissionName.READ_ROLES);
  const canEditUsers = hasPermission(PermissionName.WRITE_USERS);
  const canViewMetadata = hasPermission(PermissionName.READ_METADATA);
  const canEditCover = hasPermission(PermissionName.EDIT_COVER);

  const hasCustodianAccess = canViewMetadata || canEditCover;

  return (
    <div className="min-h-screen bg-background dark:bg-[#040608] flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col md:flex-row gap-12">
        {/* Left Sidebar Navigation */}
        <aside className="w-full md:w-64 shrink-0 flex flex-col gap-8">
          <div>
            <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Personal</h2>
            <nav className="flex flex-col gap-1">
              <NavItem
                label="Profile"
                icon={User}
                isActive={activeTab === "profile"}
                onClick={() => handleTabChange("profile")}
              />
            </nav>
          </div>

          {hasCustodianAccess && (
            <div>
              <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Custodians</h2>
              <nav className="flex flex-col gap-1">
                {canViewMetadata && (
                  <NavItem
                    label="Metadata"
                    icon={Database}
                    isActive={activeTab === "metadata"}
                    onClick={() => handleTabChange("metadata")}
                  />
                )}
                {canEditCover && (
                  <NavItem
                    label="Cover Art"
                    icon={ImageIcon}
                    isActive={activeTab === "cover-art"}
                    onClick={() => handleTabChange("cover-art")}
                    href="/admin/content?tab=cover-art"
                  />
                )}
              </nav>
            </div>
          )}

          {canViewSettings && (
            <div>
              <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Administration</h2>
              <nav className="flex flex-col gap-1">
                <NavItem
                  label="Settings"
                  icon={Settings}
                  isActive={activeTab === "instance"}
                  onClick={() => handleTabChange("instance")}
                />
                {hasPermission(PermissionName.CONFIG_FEDERATION) && (
                  <NavItem
                    label="Federation"
                    icon={Building2}
                    isActive={activeTab === "federation"}
                    onClick={() => handleTabChange("federation")}
                  />
                )}
                {hasPermission(PermissionName.CONFIG_AFFILIATE) && (
                  <NavItem
                    label="Monetization"
                    icon={DollarSign}
                    isActive={activeTab === "monetization"}
                    onClick={() => handleTabChange("monetization")}
                  />
                )}
                {hasPermission(PermissionName.CONFIG_EXTERNAL_APIS) && (
                  <NavItem
                    label="API Integrations"
                    icon={Key}
                    isActive={activeTab === "apikeys"}
                    onClick={() => handleTabChange("apikeys")}
                  />
                )}
                {canViewUsers && (
                  <NavItem
                    label="Users"
                    icon={Users}
                    isActive={activeTab === "users"}
                    onClick={() => handleTabChange("users")}
                  />
                )}
                {canViewRoles && (
                  <NavItem
                    label="Roles"
                    icon={BadgeCheck}
                    isActive={activeTab === "roles"}
                    onClick={() => handleTabChange("roles")}
                    href="/admin/groups"
                  />
                )}
                {hasPermission(PermissionName.CONFIG_INTERNAL) && (
                  <NavItem
                    label="Security"
                    icon={Shield}
                    isActive={activeTab === "security"}
                    onClick={() => handleTabChange("security")}
                  />
                )}
              </nav>
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <div className="flex-1 min-w-0 pb-20">
          {activeTab === "profile" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Profile Settings</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage your personal account settings and preferences.
                </p>
              </div>
              <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden">
                <div className="p-6 flex flex-col gap-8">
                  {/* Display Name */}
                  <div>
                    <h3 className="text-lg font-medium">Display Name</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      This is your public display name on this instance.
                    </p>
                    <input
                      className="mt-4 flex h-9 w-full max-w-md rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      value={displayName}
                      onChange={e => setDisplayName(e.target.value)}
                      placeholder="Enter your display name"
                    />
                  </div>

                  {/* Avatar URL */}
                  <div>
                    <h3 className="text-lg font-medium">Avatar URL</h3>
                    <p className="text-sm text-muted-foreground mt-1">Link to an image for your profile picture.</p>
                    <input
                      className="mt-4 flex h-9 w-full max-w-md rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      value={avatarUrl}
                      onChange={e => setAvatarUrl(e.target.value)}
                      placeholder="https://example.com/avatar.jpg"
                    />
                  </div>

                  {/* Public Username */}
                  <div>
                    <h3 className="text-lg font-medium">Public Username</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Setting a public username allows you to share your collection at <code>/u/[username]</code>.
                    </p>
                    <div className="mt-4 flex items-center gap-2 max-w-md">
                      <span className="text-sm text-muted-foreground">
                        {typeof window !== "undefined" ? window.location.host : "iqoqo.app"}/u/
                      </span>
                      <input
                        className={cn(
                          "flex h-9 flex-1 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                          usernameError && "border-red-500 focus-visible:ring-red-500"
                        )}
                        value={publicUsername}
                        onChange={e => {
                          setPublicUsername(e.target.value);
                          if (usernameError) setUsernameError(null);
                        }}
                        placeholder="testuser1"
                      />
                    </div>
                    {usernameError && <p className="mt-2 text-xs font-medium text-red-500">{usernameError}</p>}
                  </div>

                  {/* Bio */}
                  <div>
                    <h3 className="text-lg font-medium">Bio</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      A short description about you or your collection.
                    </p>
                    <textarea
                      className="mt-4 flex min-h-[100px] w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      value={bio}
                      onChange={e => setBio(e.target.value)}
                      placeholder="Tell the world about your library..."
                    />
                  </div>

                  {/* Visibility */}
                  <div>
                    <h3 className="text-lg font-medium">Profile Visibility</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Control who can see your profile and collection.
                    </p>
                    <div className="mt-4 flex flex-col gap-2">
                      <label className="flex items-center gap-3 cursor-pointer group">
                        <input
                          type="radio"
                          name="visibility"
                          value="private"
                          checked={visibility === "private"}
                          onChange={e => setVisibility(e.target.value)}
                          className="h-4 w-4 text-primary border-input bg-background focus:ring-primary"
                        />
                        <div>
                          <p className="text-sm font-medium group-hover:text-foreground transition-colors">Private</p>
                          <p className="text-xs text-muted-foreground">Only you can see your collection.</p>
                        </div>
                      </label>
                      <label className="flex items-center gap-3 cursor-pointer group">
                        <input
                          type="radio"
                          name="visibility"
                          value="public"
                          checked={visibility === "public"}
                          onChange={e => setVisibility(e.target.value)}
                          className="h-4 w-4 text-primary border-input bg-background focus:ring-primary"
                        />
                        <div>
                          <p className="text-sm font-medium group-hover:text-foreground transition-colors">Public</p>
                          <p className="text-xs text-muted-foreground">
                            Anyone with the link can view your collection.
                          </p>
                        </div>
                      </label>
                    </div>
                  </div>
                </div>

                <div className="bg-muted/40 dark:bg-white/[0.02] border-t border-border dark:border-white/10 px-6 py-3 flex justify-end">
                  <button
                    className="h-9 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md text-sm font-medium disabled:opacity-50 flex items-center gap-2"
                    onClick={handleSaveProfile}
                    disabled={
                      isSaving ||
                      (displayName === (profile.display_name || "") &&
                        publicUsername === (profile.public_username || "") &&
                        bio === (profile.bio || "") &&
                        avatarUrl === (profile.avatar_url || "") &&
                        visibility === (profile.visibility || "private"))
                    }
                  >
                    {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                    {isSaving ? "Saving..." : "Save Changes"}
                  </button>
                </div>
              </div>

              <MyEscalations />
            </div>
          )}

          {activeTab === "instance" && canViewSettings && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Instance Settings</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Configure instance-wide settings for this deployment.
                </p>
              </div>
              <InstanceSettings category="internal" />
            </div>
          )}

          {activeTab === "federation" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Federation</h1>
                <p className="text-sm text-muted-foreground mt-1">Manage federated instances and partnerships.</p>
              </div>
              <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden">
                <div className="p-6">
                  <p className="text-sm text-muted-foreground">Coming soon</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "monetization" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Monetization</h1>
                <p className="text-sm text-muted-foreground mt-1">Configure affiliate programs and revenue sharing.</p>
              </div>
              <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden">
                <div className="p-6">
                  <p className="text-sm text-muted-foreground">Coming soon</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "apikeys" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">API Integrations</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage external API keys for third-party integrations.
                </p>
              </div>
              <InstanceSettings category="external_apis" showApiKeys />
            </div>
          )}

          {activeTab === "users" && canViewUsers && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">User Management</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  View and manage roles for users registered on this instance.
                </p>
              </div>
              <UserManagement canEdit={canEditUsers} />
            </div>
          )}

          {activeTab === "security" && hasPermission(PermissionName.CONFIG_INTERNAL) && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Security</h1>
                <p className="text-sm text-muted-foreground mt-1">Configure internal security settings.</p>
              </div>
              <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden">
                <div className="p-6">
                  <p className="text-sm text-muted-foreground">Coming soon</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "metadata" && canViewMetadata && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">FRBR Metadata Editor</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage Works, Expressions, and Manifestations through the FRBR hierarchy.
                </p>
              </div>
              <FrbrEditorWrapper />
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}

/**
 * Unified settings hub page - serves as Profile for regular users and Admin panel for administrators.
 *
 * @returns The settings hub page component
 */
export default function SettingsHubPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
        </div>
      }
    >
      <SettingsContent />
    </Suspense>
  );
}

/**
 * Wrapper for the FRBR Editor that handles manifestation search and selection.
 *
 * @returns The wrapped FRBR Editor component
 */
function FrbrEditorWrapper() {
  const [selectedManifestationId, setSelectedManifestationId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<FrbrSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setSearching(true);
    setSearchError(null);
    setSearchResults([]);

    try {
      const results = await searchFrbrEntities(searchQuery.trim(), "manifestation", 20);
      setSearchResults(results);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleSelectManifestation = (id: number) => {
    setSelectedManifestationId(id);
  };

  const handleClearSelection = () => {
    setSelectedManifestationId(null);
  };

  if (!selectedManifestationId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Find Manifestation</CardTitle>
          <CardDescription>
            Search by ISBN-13, UPC, or EAN to locate the manifestation you want to edit.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <input
              placeholder="Enter ISBN-13, UPC, or EAN"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex h-10 w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <Button onClick={handleSearch} disabled={searching}>
              {searching ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Search className="h-4 w-4 mr-2" />}
              Search
            </Button>
          </div>

          {searchError && <p className="text-destructive mt-4">{searchError}</p>}

          {searchResults.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium mb-3">Search Results</h3>
              <div className="border rounded-lg divide-y">
                {searchResults.map(result => (
                  <div
                    key={result.id}
                    className="flex items-center justify-between p-4 hover:bg-muted/50 cursor-pointer"
                    onClick={() => handleSelectManifestation(result.id)}
                  >
                    <div>
                      <p className="font-medium">{result.title}</p>
                      <p className="text-sm text-muted-foreground">
                        ID: {result.id}
                        {result.isbn13 && ` | ISBN: ${result.isbn13}`}
                        {result.upc && ` | UPC: ${result.upc}`}
                      </p>
                    </div>
                    <Button variant="outline" size="sm">
                      Edit
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {searchResults.length === 0 && !searching && !searchError && searchQuery && (
            <p className="text-muted-foreground mt-4">No results found. Try a different search term.</p>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Editing Manifestation #{selectedManifestationId}</CardTitle>
          <CardDescription>Navigate through the FRBR hierarchy using the tabs below.</CardDescription>
        </div>
        <Button variant="ghost" size="sm" onClick={handleClearSelection}>
          <X className="h-4 w-4 mr-2" />
          Clear
        </Button>
      </CardHeader>
      <CardContent>
        <FrbrEditor manifestationId={selectedManifestationId} />
      </CardContent>
    </Card>
  );
}
