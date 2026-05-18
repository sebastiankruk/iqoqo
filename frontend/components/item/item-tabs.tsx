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
import { FileText, Globe, History, Images } from "lucide-react";
import type { Item } from "@/types/frbr";
import { useAppConfig, useWorkParts } from "@/lib/api/hooks";
import Link from "next/link";
import { ExtendedMetadata } from "./extended-metadata";
import { ItemProvenanceTimeline } from "./item-timeline";
import { MultiScanGallery } from "./multi-scan-gallery";

const TABS = [
  { id: "details", label: "Details", icon: FileText },
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
  const { data: partsResponse } = useWorkParts(item.work?.id ?? 0);
  const parts = partsResponse?.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* Rich metadata including audio tracklists */}
      <ExtendedMetadata meta={meta} owner_name={item.owner_name} owner_count={item.owner_count} />

      {/* FRBR hierarchy info */}
      <div className="border-t pt-6">
        <h4 className="mb-3 font-serif text-sm font-bold text-foreground">FRBR Hierarchy</h4>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
          {item.work && (
            <div className="flex flex-col gap-0.5">
              <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Work ID</dt>
              <dd className="text-sm font-mono text-foreground">#{item.work.id}</dd>
            </div>
          )}
          {item.expression && (
            <div className="flex flex-col gap-0.5">
              <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Expression ID</dt>
              <dd className="text-sm font-mono text-foreground">#{item.expression.id}</dd>
            </div>
          )}
          <div className="flex flex-col gap-0.5">
            <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Manifestation ID</dt>
            <dd className="text-sm font-mono text-foreground">
              <Link href={`/manifestation/${item.manifestation_id}`} className="hover:underline">
                #{item.manifestation_id}
              </Link>
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Item ID</dt>
            <dd className="text-sm font-mono text-foreground">#{item.id}</dd>
          </div>
        </dl>
      </div>

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
              return (
                <div
                  key={part.part_work_id}
                  className={`flex items-center justify-between p-3 text-sm transition-colors hover:bg-muted/5 ${
                    isCurrent ? "bg-primary/5 font-semibold" : ""
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                        isCurrent ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {part.sequence}
                    </span>
                    <span className={isCurrent ? "text-primary" : "text-foreground"}>{part.title}</span>
                  </div>
                  {isCurrent && (
                    <span className="text-xs font-semibold uppercase tracking-wider text-primary px-2 py-0.5 rounded-full bg-primary/10">
                      Current Item
                    </span>
                  )}
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

  const visibleTabs = TABS.filter(tab => tab.id !== "federation" || config?.federation_enabled);

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
        {active === "gallery" && <MultiScanGallery manifestationId={item.manifestation_id} />}
        {active === "history" && <ItemProvenanceTimeline itemId={item.id} />}
        {active === "federation" && <FederationTab />}
      </div>
    </div>
  );
}
