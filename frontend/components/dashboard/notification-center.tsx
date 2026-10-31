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

import React, { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Bell, Check, X, Loader2, UserPlus, UserCheck, BookOpen, AlertCircle, ArrowUpRight } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";
import {
  useNotifications,
  useMarkNotificationsRead,
  useMarkAllNotificationsRead,
  notificationQueryKeys,
  NotificationItem,
} from "@/lib/api/notifications";

interface NotificationCenterProps {
  enabled?: boolean;
}

/**
 * In-app Notification Center dropdown displaying alerts for follows, loans, and escalations.
 *
 * @param props - Component props containing enabled flag.
 * @returns {JSX.Element} The NotificationCenter component.
 */
export function NotificationCenter({ enabled = true }: NotificationCenterProps) {
  const t = useTranslations("Notifications");
  const queryClient = useQueryClient();
  const { data, isLoading } = useNotifications(false, enabled);
  const markReadMutation = useMarkNotificationsRead();
  const markAllReadMutation = useMarkAllNotificationsRead();
  const [respondingId, setRespondingId] = useState<string | number | null>(null);

  const notifications = data?.notifications || [];
  const unreadCount = data?.unread_count || 0;

  const handleNotificationClick = (notif: NotificationItem) => {
    if (!notif.read_at) {
      markReadMutation.mutate([notif.id]);
    }
  };

  const getNotificationTargetUrl = (notif: NotificationItem): string | null => {
    if (notif.target_iri) return notif.target_iri;
    if (typeof notif.payload?.target_iri === "string") return notif.payload.target_iri;
    if (notif.type === "friend_request" || notif.type === "follow_request") return "/profile?tab=incoming#friends";
    if (notif.type === "friend_accepted") return "/profile?tab=accepted#friends";
    return null;
  };

  const handleRespondFriendship = async (
    e: React.MouseEvent,
    notif: NotificationItem,
    friendshipId: string | number,
    action: "accept" | "reject"
  ) => {
    e.preventDefault();
    e.stopPropagation();
    setRespondingId(friendshipId);
    try {
      await apiClient.post(`/profile/friends/${encodeURIComponent(String(friendshipId))}/respond`, { action });
      toast.success(action === "accept" ? t("friendAccepted") : t("friendRejected"));
      markReadMutation.mutate([notif.id]);
      await queryClient.invalidateQueries({ queryKey: notificationQueryKeys.all });
      await queryClient.invalidateQueries({ queryKey: ["profile"] });
    } catch (err) {
      const msg = err instanceof Error ? err.message : t("actionFailed");
      toast.error(msg);
    } finally {
      setRespondingId(null);
    }
  };

  const renderIcon = (type: string) => {
    switch (type) {
      case "friend_request":
        return <UserPlus className="h-4 w-4 text-sky-500" />;
      case "friend_accepted":
        return <UserCheck className="h-4 w-4 text-emerald-500" />;
      case "follow_request":
        return <UserPlus className="h-4 w-4 text-sky-500" />;
      case "loan_request":
      case "loan_approved":
      case "loan_rejected":
        return <BookOpen className="h-4 w-4 text-emerald-500" />;
      case "escalation_resolved":
        return <AlertCircle className="h-4 w-4 text-amber-500" />;
      default:
        return <Bell className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="relative flex h-9 w-9 items-center justify-center rounded-full hover:bg-white/10 dark:hover:bg-white/5 transition-colors outline-none"
          aria-label={t("ariaLabel")}
          data-testid="notification-bell"
        >
          <Bell className="h-4 w-4 text-foreground/80 dark:text-foreground" />
          {unreadCount > 0 && (
            <span
              data-testid="notification-badge"
              className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white shadow-sm"
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-80 sm:w-96 p-2 dark:bg-[#0a0c10] dark:border-white/10 shadow-xl rounded-xl"
      >
        <div className="flex items-center justify-between px-3 py-2 border-b dark:border-white/10">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">{t("title")}</span>
            {unreadCount > 0 && (
              <span className="text-xs text-muted-foreground">{t("unreadCount", { count: String(unreadCount) })}</span>
            )}
          </div>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground hover:text-foreground px-2"
              onClick={() => markAllReadMutation.mutate()}
              disabled={markAllReadMutation.isPending}
            >
              <Check className="h-3 w-3 mr-1" />
              {t("markAllRead")}
            </Button>
          )}
        </div>

        <div className="max-h-[360px] overflow-y-auto divide-y dark:divide-white/5 my-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : notifications.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground" data-testid="notification-empty">
              {t("empty")}
            </div>
          ) : (
            notifications.map(notif => {
              const targetUrl = getNotificationTargetUrl(notif);
              const fid = notif.payload?.friendship_id as string | number | undefined;
              const isFriendOrFollow = notif.type === "friend_request" || notif.type === "follow_request";
              const showActions =
                isFriendOrFollow && Boolean(fid) && !notif.read_at && notif.payload?.status !== "accepted";

              const content = (
                <div
                  className={`flex flex-col p-2.5 rounded-lg text-sm transition-colors cursor-pointer ${
                    notif.read_at
                      ? "opacity-60 hover:opacity-100 hover:bg-muted/50"
                      : "bg-muted/40 font-medium hover:bg-muted/70"
                  }`}
                  data-testid={`notification-item-${notif.id}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 shrink-0">{renderIcon(notif.type)}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs leading-snug break-words">{String(notif.payload?.message || notif.type)}</p>
                      <span className="text-[10px] text-muted-foreground mt-1 block">
                        {new Date(notif.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                    {targetUrl && <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />}
                  </div>

                  {showActions && fid && (
                    <div className="flex items-center gap-1.5 mt-2 pt-1.5 border-t border-border/40">
                      <Button
                        size="sm"
                        variant="default"
                        className="h-7 px-2.5 text-xs gap-1"
                        disabled={respondingId === fid}
                        onClick={e => handleRespondFriendship(e, notif, fid, "accept")}
                        data-testid={`notification-accept-${notif.id}`}
                      >
                        <Check className="h-3 w-3" />
                        {t("accept")}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 px-2.5 text-xs gap-1 text-destructive hover:bg-destructive/10"
                        disabled={respondingId === fid}
                        onClick={e => handleRespondFriendship(e, notif, fid, "reject")}
                        data-testid={`notification-reject-${notif.id}`}
                      >
                        <X className="h-3 w-3" />
                        {t("reject")}
                      </Button>
                    </div>
                  )}
                </div>
              );

              return (
                <div key={notif.id} className="py-1">
                  {targetUrl ? (
                    <Link
                      href={targetUrl}
                      className="block"
                      onClick={() => handleNotificationClick(notif)}
                      data-testid={`notification-link-${notif.id}`}
                    >
                      {content}
                    </Link>
                  ) : (
                    <div onClick={() => handleNotificationClick(notif)}>{content}</div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
