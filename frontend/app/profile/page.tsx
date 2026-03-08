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
import Image from "next/image";


interface ConsentRecord {
  consent_type: string;
  is_granted: boolean;
  policy_version: string;
  timestamp: string;
  telemetry: boolean;
  federation: boolean;
}

interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  visibility: "public" | "private";
  created_at: string;
  consents: ConsentRecord;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editNameValue, setEditNameValue] = useState("");

  useEffect(() => {
    fetch("/api/profile", { headers: { "Content-Type": "application/json" } })
    .then(res => res.json())
    .then(data => {
      setProfile(data);
      setEditNameValue(data.display_name || "");
    })
    .catch(err => console.error(err));
  }, []);

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  };

  const handleUpdateName = async () => {
    const res = await fetch("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: editNameValue })
    });
    if (res.ok) {
      setProfile(prev => prev ? { ...prev, display_name: editNameValue } : null);
      setIsEditingName(false);
      toast.success("Profile updated");
    } else {
      toast.error("Failed to update profile");
    }
  };

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm("Are you absolutely sure? This will permanently delete your account, your library collection, and all your data. This cannot be undone.");
    if (!confirmed) return;

    const res = await fetch("/api/profile", { method: "DELETE" });
    if (res.ok) {
      toast.success("Account deleted permanently.");
      handleLogout();
    } else {
      toast.error("Failed to delete account");
    }
  };

  const toggleConsent = async (type: string, currentStatus: boolean) => {
    await fetch("/api/profile/consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consent_type: type, is_granted: !currentStatus })
    });
    setProfile(prev => {
      if (!prev) return null;
      return {
        ...prev,
        consents: {
          ...prev.consents,
          [type]: !currentStatus
        }
      };
    });
    toast.success("Privacy preferences updated");
  };

  if (!profile) return <div className="p-8 text-center text-muted-foreground">Loading...</div>;

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <div className="flex items-center space-x-4">
        {profile.avatar_url ? (
          <Image src={profile.avatar_url} alt="Avatar" className="w-16 h-16 rounded-full border" />
        ) : (
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-xl font-bold">
            {profile.email[0].toUpperCase()}
          </div>
        )}
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
                  onChange={(e) => setEditNameValue(e.target.value)}
                  className="border rounded px-2 py-1 flex-1 text-sm bg-background"
                />
                <Button size="sm" onClick={handleUpdateName}>Save</Button>
                <Button size="sm" variant="ghost" onClick={() => setIsEditingName(false)}>Cancel</Button>
              </div>
            ) : (
              <div className="flex items-center justify-between mt-1">
                <span>{profile.display_name || "N/A"}</span>
                <Button size="sm" variant="outline" onClick={() => setIsEditingName(true)}>Edit</Button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="p-4 border rounded-lg bg-card space-y-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Privacy & Consents (GDPR)</h2>
          <Link href="/legal/privacy" target="_blank" className="text-sm text-muted-foreground underline hover:text-primary">
            Read Policy
          </Link>
        </div>
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

      <div className="flex justify-between items-center pt-4">
        <Button variant="outline" onClick={handleLogout}>Log Out</Button>

        <div className="text-right">
          <Button variant="destructive" onClick={handleDeleteAccount}>
            Delete Account
          </Button>
        </div>
      </div>
    </div>
  );
}
