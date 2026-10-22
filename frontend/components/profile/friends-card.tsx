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

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { UserPlus, Check, X, UserX, Globe, Users, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";

export interface FriendEntry {
  friendship_id: number;
  user_id: string;
  username: string;
  display_name?: string | null;
  avatar_url?: string | null;
  status: string;
  created_at?: string | null;
  is_federated: boolean;
  actor_uri?: string | null;
}

export interface FriendsResponse {
  accepted: FriendEntry[];
  incoming: FriendEntry[];
  outgoing: FriendEntry[];
}

/**
 * Renders the Friends management card with tabs for accepted, incoming, and outgoing requests.
 *
 * @returns {JSX.Element} The component
 */
export function FriendsCard() {
  const t = useTranslations("Profile");
  const [data, setData] = useState<FriendsResponse>({ accepted: [], incoming: [], outgoing: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [targetIdentifier, setTargetIdentifier] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<"accepted" | "incoming" | "outgoing">(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab");
      if (tabParam === "incoming" || tabParam === "outgoing" || tabParam === "accepted") {
        return tabParam;
      }
    }
    return "accepted";
  });

  const loadFriends = useCallback(async () => {
    try {
      const res = await apiClient.get<{ success: boolean; data: FriendsResponse }>("/profile/friends");
      setData(res.data.data);
    } catch (err) {
      console.error("Failed to load friends", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    const fetchFriends = async () => {
      try {
        const res = await apiClient.get<{ success: boolean; data: FriendsResponse }>("/profile/friends");
        if (!ignore) {
          setData(res.data.data);
        }
      } catch (err) {
        console.error("Failed to load friends", err);
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };
    void fetchFriends();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    const handleUrlSync = () => {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab");
      if (tabParam === "incoming" || tabParam === "outgoing" || tabParam === "accepted") {
        setActiveTab(tabParam);
      }
    };

    window.addEventListener("popstate", handleUrlSync);
    return () => {
      window.removeEventListener("popstate", handleUrlSync);
    };
  }, []);

  const handleSendRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetIdentifier.trim()) return;

    setIsSubmitting(true);
    try {
      await apiClient.post("/profile/friends/request", { identifier: targetIdentifier.trim() });
      toast.success(t("requestSent") || "Friend request sent!");
      setTargetIdentifier("");
      await loadFriends();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to send friend request";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRespond = async (friendshipId: number, action: "accept" | "reject") => {
    try {
      await apiClient.post(`/profile/friends/${friendshipId}/respond`, { action });
      toast.success(
        action === "accept"
          ? t("friendAccepted") || "Friend request accepted"
          : t("friendRejected") || "Friend request rejected"
      );
      await loadFriends();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to respond to request";
      toast.error(msg);
    }
  };

  const handleRemove = async (friendshipId: number) => {
    try {
      await apiClient.delete(`/profile/friends/${friendshipId}`);
      toast.success(t("friendRemoved") || "Friendship removed");
      await loadFriends();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to remove friend";
      toast.error(msg);
    }
  };

  return (
    <div id="friends" data-testid="friends-card" className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-2">
        <Users className="h-5 w-5 text-primary" />
        <h2 className="text-lg font-semibold">{t("friendsManagement") || "Friends & Social Library"}</h2>
      </div>
      <p className="text-xs text-muted-foreground mb-6">
        {t("friendsManagementDesc") || "Manage connected friends across your local instance and the Fediverse."}
      </p>

      {/* Add Friend Form */}
      <form onSubmit={handleSendRequest} className="mb-6 flex gap-2">
        <input
          type="text"
          value={targetIdentifier}
          onChange={e => setTargetIdentifier(e.target.value)}
          placeholder={t("addFriendPlaceholder") || "Username, email, or @user@domain handle..."}
          className="flex h-9 flex-1 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <Button type="submit" size="sm" disabled={isSubmitting || !targetIdentifier.trim()} className="gap-1.5">
          {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
          {t("sendRequest") || "Send Request"}
        </Button>
      </form>

      {/* Sub-tabs */}
      <div className="flex border-b border-border mb-4 text-xs font-medium">
        <button
          type="button"
          onClick={() => setActiveTab("accepted")}
          className={`pb-2 px-3 border-b-2 transition-colors ${
            activeTab === "accepted"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("friendsTab") || "Friends"} ({data.accepted.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("incoming")}
          className={`pb-2 px-3 border-b-2 transition-colors ${
            activeTab === "incoming"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("incomingRequests") || "Incoming"} ({data.incoming.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("outgoing")}
          className={`pb-2 px-3 border-b-2 transition-colors ${
            activeTab === "outgoing"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {t("outgoingRequests") || "Outgoing"} ({data.outgoing.length})
        </button>
      </div>

      {isLoading ? (
        <div className="py-6 text-center text-sm text-muted-foreground flex justify-center items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading...
        </div>
      ) : activeTab === "accepted" ? (
        data.accepted.length === 0 ? (
          <p className="py-6 text-center text-xs text-muted-foreground">
            {t("noFriends") || "No friends connected yet."}
          </p>
        ) : (
          <ul className="space-y-3">
            {data.accepted.map(friend => (
              <li
                key={friend.friendship_id}
                className="flex items-center justify-between p-3 rounded-lg bg-muted/40 border border-border/40"
              >
                <div className="flex items-center gap-2.5">
                  <div className="h-8 w-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold text-xs">
                    {(friend.display_name || friend.username || "U")[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm font-medium leading-none">{friend.display_name || friend.username}</p>
                      {friend.is_federated && (
                        <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] bg-secondary text-secondary-foreground">
                          <Globe className="h-2.5 w-2.5" /> Fediverse
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">@{friend.username}</p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemove(friend.friendship_id)}
                  className="h-8 text-xs text-muted-foreground hover:text-destructive gap-1"
                >
                  <UserX className="h-3.5 w-3.5" />
                  {t("remove") || "Remove"}
                </Button>
              </li>
            ))}
          </ul>
        )
      ) : activeTab === "incoming" ? (
        data.incoming.length === 0 ? (
          <p className="py-6 text-center text-xs text-muted-foreground">
            {t("noRequests") || "No pending incoming requests."}
          </p>
        ) : (
          <ul className="space-y-3">
            {data.incoming.map(req => (
              <li
                key={req.friendship_id}
                className="flex items-center justify-between p-3 rounded-lg bg-muted/40 border border-border/40"
              >
                <div className="flex items-center gap-2.5">
                  <div className="h-8 w-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold text-xs">
                    {(req.display_name || req.username || "U")[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm font-medium leading-none">{req.display_name || req.username}</p>
                      {req.is_federated && (
                        <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] bg-secondary text-secondary-foreground">
                          <Globe className="h-2.5 w-2.5" /> Fediverse
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">@{req.username}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <Button
                    size="sm"
                    onClick={() => handleRespond(req.friendship_id, "accept")}
                    className="h-8 text-xs gap-1"
                  >
                    <Check className="h-3.5 w-3.5" />
                    {t("accept") || "Accept"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRespond(req.friendship_id, "reject")}
                    className="h-8 text-xs text-destructive hover:text-destructive gap-1"
                  >
                    <X className="h-3.5 w-3.5" />
                    {t("reject") || "Reject"}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )
      ) : data.outgoing.length === 0 ? (
        <p className="py-6 text-center text-xs text-muted-foreground">{t("noRequests") || "No outgoing requests."}</p>
      ) : (
        <ul className="space-y-3">
          {data.outgoing.map(req => (
            <li
              key={req.friendship_id}
              className="flex items-center justify-between p-3 rounded-lg bg-muted/40 border border-border/40"
            >
              <div>
                <p className="text-sm font-medium leading-none">{req.display_name || req.username}</p>
                <p className="text-xs text-muted-foreground mt-0.5">@{req.username}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground italic">{t("pending") || "Pending"}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemove(req.friendship_id)}
                  className="h-8 text-xs text-muted-foreground hover:text-destructive gap-1"
                >
                  <X className="h-3.5 w-3.5" />
                  {t("cancel") || "Cancel"}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
