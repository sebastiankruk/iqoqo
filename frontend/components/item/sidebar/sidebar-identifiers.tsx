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
  localBarcode?: string | null;
}

/**
 * Identifiers region of ItemSidebar, displaying ISBN and exemplar local barcode.
 *
 * @param props - Props object
 * @returns {JSX.Element | null} Rendered identifiers or null if absent
 */
export function SidebarIdentifiers({ isbn, item, localBarcode }: SidebarIdentifiersProps) {
  const isbnValue = isbn !== undefined ? isbn : item?.isbn;
  const barcodeValue = localBarcode !== undefined ? localBarcode : item?.local_barcode;

  if (!isbnValue && !barcodeValue) {
    return null;
  }

  return (
    <div className="space-y-0.5 text-center text-xs text-muted-foreground">
      {isbnValue && <p>ISBN: {isbnValue}</p>}
      {barcodeValue && <p data-testid="sidebar-local-barcode">Barcode: {barcodeValue}</p>}
    </div>
  );
}
