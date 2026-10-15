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
import * as React from "react";
import type { Item } from "@/types/frbr";

/** Props for SidebarIdentifiers component */
export interface SidebarIdentifiersProps {
  isbn?: string | null;
  item?: Item;
}

/**
 * Identifiers region of ItemSidebar, displaying ISBN.
 *
 * @param props - Props object
 * @returns {JSX.Element | null} Rendered ISBN or null if absent
 */
export function SidebarIdentifiers({ isbn, item }: SidebarIdentifiersProps) {
  const value = isbn !== undefined ? isbn : item?.isbn;

  if (!value) {
    return null;
  }

  return <p className="text-center text-xs text-muted-foreground">ISBN: {value}</p>;
}
