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

/** Props for SidebarFrbrInfo component */
export interface SidebarFrbrInfoProps {
  item?: Item;
  expression?: Item["expression"] | null;
}

/**
 * FRBR quick-info panel of ItemSidebar, displaying expression format and language.
 *
 * @param props - Props object
 * @returns {JSX.Element} Rendered FRBR info panel
 */
export function SidebarFrbrInfo({ item, expression: expressionProp }: SidebarFrbrInfoProps) {
  const expression = expressionProp !== undefined ? expressionProp : item?.expression;

  return (
    <div className="w-full rounded-lg border border-border bg-muted/50 p-4">
      <div className="flex flex-col gap-3">
        {expression && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Format</span>
            <span className="text-xs font-semibold capitalize text-foreground">{expression.content_type}</span>
          </div>
        )}
        {expression?.language && (
          <>
            <div className="h-px bg-border" />
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Language</span>
              <span className="text-xs font-semibold uppercase text-foreground">{expression.language}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
