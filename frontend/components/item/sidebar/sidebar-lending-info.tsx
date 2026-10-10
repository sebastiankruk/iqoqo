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

/** Props for SidebarLendingInfo component */
export interface SidebarLendingInfoProps {
  item: Item;
  handleRequestLoan?: () => void;
  handleLentSubmit?: () => void;
}

/**
 * Lending info display region of ItemSidebar, showing borrower or owner name when lent or borrowed.
 *
 * @param props - Props object
 * @returns {JSX.Element | null} Rendered lending info or null if not lent/borrowed
 */
export function SidebarLendingInfo({ item }: SidebarLendingInfoProps) {
  if (item.collection_status !== "lent" && !item.is_borrowed) {
    return null;
  }

  return (
    <div className="flex flex-col items-center gap-1">
      {item.collection_status === "lent" && !item.is_borrowed && item.lent_to_name && (
        <p className="text-center text-[10px] font-bold uppercase tracking-wider text-orange-600">
          Lent to: <span className="text-foreground">{item.lent_to_name}</span>
        </p>
      )}
      {item.is_borrowed && item.owner_name && (
        <p className="text-center text-[10px] font-bold uppercase tracking-wider text-blue-600">
          Borrowed from: <span className="text-foreground">{item.owner_name}</span>
        </p>
      )}
    </div>
  );
}
