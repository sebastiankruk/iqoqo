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

import { useState } from "react";
import { FileText, Globe, History, Images, BookOpen, MessageSquare } from "lucide-react";
import type { Item } from "@/types/frbr";
import { useAppConfig, useWorkParts, useProfile } from "@/lib/api/hooks";
import { PermissionName } from "@/lib/permissions";
import Link from "next/link";
import Image from "next/image";
import { ExtendedMetadata } from "./extended-metadata";
import { ItemProvenanceTimeline } from "./item-timeline";
import { MultiScanGallery } from "./multi-scan-gallery";
import { FRBRFeedback } from "../social/frbr-feedback";

const TABS = [
  { id: "details", label: "Details", icon: FileText },
  { id: "reviews", label: "Reviews", icon: MessageSquare },
  { id: "gallery", label: "Gallery", icon: Images },
  { id: "history", label: "History", icon: History },
  { id: "federation", label: "Federation", icon: Globe },
] as const;

type TabId = (typeof TABS)[number]["id"];

/* ── Details tab ─────────────────────────────────────────────────────────── */

/**
 * Details tab component.
 *
 * @param {{ item: Item }} props - The component props.
 * @param {Item} props.item - The item to display.
 * @returns {JSX.Element}
 */
function DetailsTab({ item }: { item: Item }) {
  const meta = (item.manifestation_meta as Record<string, unknown>) ?? {};
  const { data: partsResponse } = useWorkParts(item.work?.container_work_id ?? item.work?.id ?? 0);
  const parts = partsResponse?.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* Rich metadata including audio tracklists */}
      <ExtendedMetadata meta={meta} owner_name={item.owner_name} owner_count={item.owner_count} />

      {/* Series parts info */}
      {item.work && parts.length > 0 && (
        <div className="border-t pt-6">
          <h4 className="mb-3 font-serif text-sm font-bold text-foreground">Series / Complex Work Parts</h4>
          <p className="text-xs text-muted-foreground mb-3">
            This title is part of a complex work / series. Here are all the elements in this series:
          </p>
          <div className="border rounded-xl divide-y bg-muted/10 overflow-hidden">
            {parts.map(part => {
              const isCurrent = part.part_work_id === item.work?.id;
              const isLinkable = !!(part.item_id || part.manifestation_id);
              const linkUrl = part.item_id ? `/item/${part.item_id}` : `/manifestation/${part.manifestation_id}`;

              const content = (
                <div className="flex items-center gap-3">
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      isCurrent ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {part.sequence}
                  </span>
                  {part.cover_url ? (
                    <div className="relative h-12 w-8 shrink-0 overflow-hidden rounded-md border border-border/80 bg-secondary shadow-sm">
                      <Image
                        src={part.cover_url}
                        alt={`Cover of ${part.title}`}
                        fill
                        sizes="32px"
                        className="object-cover"
                        unoptimized
                      />
                    </div>
                  ) : (
                    <div className="flex h-12 w-8 shrink-0 items-center justify-center rounded-md border border-border/80 bg-muted text-muted-foreground/30 shadow-sm">
                      <BookOpen className="h-4 w-4" />
                    </div>
                  )}
                  <span
                    className={
                      isCurrent ? "text-primary font-semibold" : "text-foreground hover:text-primary transition-colors"
                    }
                  >
                    {part.title}
                  </span>
                </div>
              );

              return (
                <div
                  key={part.part_work_id}
                  className={`flex items-center justify-between p-3 text-sm transition-all duration-200 ${
                    isCurrent ? "bg-primary/5 font-semibold" : "hover:bg-muted/40"
                  }`}
                >
                  {isLinkable ? (
                    <Link href={linkUrl} className="flex-1">
                      {content}
                    </Link>
                  ) : (
                    <div className="flex-1">{content}</div>
                  )}
                  <div className="flex items-center gap-2">
                    {part.item_id && (
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-green-600 dark:text-green-400 px-2 py-0.5 rounded-full bg-green-500/10">
                        In Collection
                      </span>
                    )}
                    {isCurrent && (
                      <span className="text-xs font-semibold uppercase tracking-wider text-primary px-2 py-0.5 rounded-full bg-primary/10">
                        Current Item
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Federation tab ──────────────────────────────────────────────────────── */

/**
 * Federation tab component.
 *
 * @returns {JSX.Element} The component
 */
function FederationTab() {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        <Globe className="h-7 w-7 text-muted-foreground" />
      </div>
      <h3 className="mt-4 font-serif text-lg font-bold text-foreground">Federation Coming Soon</h3>
      <p className="mt-1 max-w-xs text-sm text-muted-foreground">
        Connect with other iqoqo libraries to discover who else has this title in their collection.
      </p>
    </div>
  );
}

/**
 * Renders the reviews tab content for an item, showing all levels of reviews (Work, Expression, Manifestation, Item).
 *
 * @param props - Component props.
 * @param props.item - The item to display reviews for.
 * @returns The rendered reviews tab.
 */
function ReviewsTab({ item }: { item: Item }) {
  const subtabs = [
    { id: "work", label: "Conceptual Work", targetId: item.work?.id, description: "Story / artistic creation" },
    {
      id: "expression",
      label: "Expression",
      targetId: item.expression?.id,
      description: "Realization (Language/Format)",
    },
    {
      id: "manifestation",
      label: "Edition",
      targetId: item.manifestation_id,
      description: "Printed publication (ISBN)",
    },
    { id: "item", label: "Personal Copy", targetId: item.id, description: "Your copy rating & notes" },
  ] as const;

  // Default to the first subtab that has a valid targetId (items may lack work/expression)
  const firstAvailableLevel = (subtabs.find(s => !!s.targetId)?.id ?? "manifestation") as
    | "work"
    | "expression"
    | "manifestation"
    | "item";
  const [activeLevel, setActiveLevel] = useState<"work" | "expression" | "manifestation" | "item">(firstAvailableLevel);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2 border-b pb-4">
        {subtabs.map(({ id, label, targetId, description }) => {
          if (!targetId) return null;
          const isSelected = activeLevel === id;
          return (
            <button
              key={id}
              onClick={() => setActiveLevel(id)}
              className={`flex flex-col items-start gap-0.5 rounded-xl border px-4 py-2.5 text-left transition-all cursor-pointer ${
                isSelected
                  ? "border-primary bg-primary/5 text-primary shadow-sm"
                  : "border-border/60 hover:bg-muted/30 text-muted-foreground hover:text-foreground"
              }`}
            >
              <span className="text-xs font-bold leading-none">{label}</span>
              <span className="text-[10px] text-muted-foreground/80 leading-none mt-1">{description}</span>
            </button>
          );
        })}
      </div>

      <div>
        {activeLevel === "work" && item.work && (
          <FRBRFeedback level="work" targetId={item.work.id} title="Conceptual Work" />
        )}
        {activeLevel === "expression" && item.expression && (
          <FRBRFeedback level="expression" targetId={item.expression.id} title="Expression" />
        )}
        {activeLevel === "manifestation" && (
          <FRBRFeedback level="manifestation" targetId={item.manifestation_id} title="Manifestation Edition" />
        )}
        {activeLevel === "item" && <FRBRFeedback level="item" targetId={item.id} title="Personal Copy" />}
      </div>
    </div>
  );
}

/* ── Tabs component ──────────────────────────────────────────────────────── */

/**
 * Tabbed detail panel for an item page.
 *
 * @param {{ item: Item }} props - The component props.
 * @param {Item} props.item - The item to display.
 * @returns {JSX.Element}
 */
export function ItemTabs({ item }: { item: Item }) {
  const [active, setActive] = useState<TabId>("details");
  const { data: config } = useAppConfig();
  const { data: profile } = useProfile();

  const permissions = profile?.permissions ?? [];
  const isOwner = !!item.is_owner || (!!profile && item.owner_id === profile.id);
  const isBorrower = !!item.is_borrowed || (!!profile && item.lent_to_user_id === profile.id);
  const isAdmin = !!profile?.roles?.includes("admin");
  const hasUpdatePermission = permissions.includes(PermissionName.UPDATE_ITEM);

  const canViewHistory = isOwner || isBorrower || isAdmin || hasUpdatePermission;

  const visibleTabs = TABS.filter(tab => {
    if (tab.id === "federation") return !!config?.federation_enabled;
    if (tab.id === "history") return canViewHistory && item.id > 0;
    return true;
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Tab bar */}
      <div className="flex gap-1 rounded-xl bg-secondary p-1">
        {visibleTabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActive(id)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition-all ${
              active === id ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {active === "details" && <DetailsTab item={item} />}
        {active === "reviews" && <ReviewsTab item={item} />}
        {active === "gallery" && <MultiScanGallery manifestationId={item.manifestation_id} />}
        {active === "history" && <ItemProvenanceTimeline itemId={item.id} />}
        {active === "federation" && <FederationTab />}
      </div>
    </div>
  );
}
