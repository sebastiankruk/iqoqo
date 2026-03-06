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
import { FileText, BookCopy, Globe } from "lucide-react";
import type { Item } from "@/types/frbr";

const TABS = [
  { id: "details", label: "Details", icon: FileText },
  { id: "my-copy", label: "My Copy", icon: BookCopy },
  { id: "federation", label: "Federation", icon: Globe },
] as const;

type TabId = (typeof TABS)[number]["id"];

/* ── Details tab ─────────────────────────────────────────────────────────── */

function DetailsTab({ item }: { item: Item }) {
  const meta = item.manifestation_meta ?? {};
  const description =
    (meta["description"] as string | undefined) ??
    (meta["Description"] as string | undefined);

  const fields = [
    { label: "Publisher", value: meta["Publisher"] as string | undefined },
    { label: "ISBN-13", value: item.isbn },
    { label: "Language", value: item.expression?.language },
    { label: "Format", value: item.expression?.content_type },
    { label: "Year", value: meta["Year"] as string | undefined },
  ].filter((f) => f.value);

  return (
    <div className="flex flex-col gap-6">
      {description && (
        <div>
          <h4 className="mb-2 font-serif text-sm font-bold text-foreground">
            Synopsis
          </h4>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        </div>
      )}

      {fields.length > 0 && (
        <div>
          <h4 className="mb-3 font-serif text-sm font-bold text-foreground">
            Publication Details
          </h4>
          <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
            {fields.map(({ label, value }) => (
              <div key={label} className="flex flex-col gap-0.5">
                <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  {label}
                </dt>
                <dd className="text-sm font-medium text-foreground">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* FRBR hierarchy info */}
      <div>
        <h4 className="mb-3 font-serif text-sm font-bold text-foreground">
          FRBR Hierarchy
        </h4>
        <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
          {item.work && (
            <div className="flex flex-col gap-0.5">
              <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Work ID
              </dt>
              <dd className="text-sm font-medium text-foreground">
                #{item.work.id}
              </dd>
            </div>
          )}
          {item.expression && (
            <div className="flex flex-col gap-0.5">
              <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Expression ID
              </dt>
              <dd className="text-sm font-medium text-foreground">
                #{item.expression.id}
              </dd>
            </div>
          )}
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Manifestation ID
            </dt>
            <dd className="text-sm font-medium text-foreground">
              #{item.manifestation_id}
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Item ID
            </dt>
            <dd className="text-sm font-medium text-foreground">#{item.id}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

/* ── My Copy tab ─────────────────────────────────────────────────────────── */

function MyCopyTab({ item }: { item: Item }) {
  const fields = [
    { label: "Status", value: item.status },
    { label: "Owner", value: item.owner_id },
  ].filter((f) => f.value);

  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-lg border border-border bg-muted/40 p-4">
        <h4 className="mb-3 font-serif text-sm font-bold text-foreground">
          Copy Information
        </h4>
        <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
          {fields.map(({ label, value }) => (
            <div key={label} className="flex flex-col gap-0.5">
              <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {label}
              </dt>
              <dd className="text-sm font-medium capitalize text-foreground">
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

/* ── Federation tab ──────────────────────────────────────────────────────── */

function FederationTab() {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        <Globe className="h-7 w-7 text-muted-foreground" />
      </div>
      <h3 className="mt-4 font-serif text-lg font-bold text-foreground">
        Federation Coming Soon
      </h3>
      <p className="mt-1 max-w-xs text-sm text-muted-foreground">
        Connect with other iqoqo libraries to discover who else has this title
        in their collection.
      </p>
    </div>
  );
}

/* ── Tabs component ──────────────────────────────────────────────────────── */

/** Tabbed detail panel for an item page. */
export function ItemTabs({ item }: { item: Item }) {
  const [active, setActive] = useState<TabId>("details");

  return (
    <div className="flex flex-col gap-6">
      {/* Tab bar */}
      <div className="flex gap-1 rounded-xl bg-secondary p-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActive(id)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition-all ${
              active === id
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
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
        {active === "my-copy" && <MyCopyTab item={item} />}
        {active === "federation" && <FederationTab />}
      </div>
    </div>
  );
}
