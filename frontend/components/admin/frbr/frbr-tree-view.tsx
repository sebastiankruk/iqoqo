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

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronDown, MoreVertical, Plus, ArrowUpRight, Trash2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useState } from "react";
import type { FrbrTree } from "@/lib/api/admin";

/**
 * The FRBR entity level type for tree nodes.
 */
export type FrbrLevel = "work" | "expression" | "manifestation" | "item";

/**
 * Props for the FRBRTreeView component.
 */
interface FRBRTreeViewProps {
  tree: FrbrTree;
  selectedLevel: FrbrLevel;
  selectedId?: number;
  onSelect: (level: FrbrLevel, id: number) => void;
  onAddChild?: (parentLevel: FrbrLevel) => void;
  onEscalate?: (level: FrbrLevel, id: number) => void;
  onDelete?: (level: FrbrLevel, id: number) => void;
}

/**
 * Badge label for each FRBR entity level.
 */
const LEVEL_BADGES: Record<FrbrLevel, string> = {
  work: "F1",
  expression: "F2",
  manifestation: "F3",
  item: "F5",
};

/**
 * Hierarchical tree navigator for FRBR entities.
 * Renders Work → Expression → Manifestation → Items with selection indicators,
 * format/count badges, and inline action menus.
 *
 * @param props - Component properties
 * @param props.tree - The FRBR tree data
 * @param props.selectedLevel - Currently selected entity level
 * @param props.selectedId - Currently selected entity ID
 * @param props.onSelect - Callback when a node is selected
 * @param props.onAddChild - Optional callback for adding a child entity
 * @param props.onEscalate - Optional callback for escalating
 * @param props.onDelete - Optional callback for deleting
 * @returns JSX element
 */
export function FRBRTreeView({
  tree,
  selectedLevel,
  selectedId,
  onSelect,
  onAddChild,
  onEscalate,
  onDelete,
}: FRBRTreeViewProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["work", "expression", "manifestation", "items"])
  );

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  /**
   * Renders an inline action menu for a tree node.
   *
   * @param level - The entity level
   * @param id - The entity ID
   * @returns JSX element
   */
  function renderActions(level: FrbrLevel, id: number) {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={e => e.stopPropagation()}>
            <MoreVertical className="w-3 h-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {onAddChild && level !== "item" && (
            <DropdownMenuItem onClick={() => onAddChild(level)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Child
            </DropdownMenuItem>
          )}
          {onEscalate && (
            <DropdownMenuItem onClick={() => onEscalate(level, id)}>
              <ArrowUpRight className="w-4 h-4 mr-2" />
              Escalate
            </DropdownMenuItem>
          )}
          {onDelete && (
            <DropdownMenuItem onClick={() => onDelete(level, id)} className="text-destructive">
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  return (
    <div className="border rounded-lg divide-y text-sm" data-testid="frbr-tree-view">
      {/* Work */}
      <div>
        <button
          type="button"
          className="w-full flex items-center gap-2 p-2 hover:bg-muted/50 text-left"
          onClick={() => toggleSection("work")}
        >
          {expandedSections.has("work") ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
          <Badge variant="outline" className="text-xs">
            F1
          </Badge>
          <span className="font-medium truncate flex-1">
            {tree.work?.title ?? "No Work"}
          </span>
        </button>
        {expandedSections.has("work") && tree.work && (
          <div
            className={`flex items-center gap-2 pl-8 pr-2 py-1.5 cursor-pointer hover:bg-muted/30 ${
              selectedLevel === "work" && selectedId === tree.work.id ? "bg-primary/10" : ""
            }`}
            onClick={() => tree.work && onSelect("work", tree.work.id)}
            data-testid="tree-node-work"
          >
            <span className="truncate flex-1">{tree.work.title}</span>
            {renderActions("work", tree.work.id)}
          </div>
        )}
      </div>

      {/* Expression */}
      <div>
        <button
          type="button"
          className="w-full flex items-center gap-2 p-2 hover:bg-muted/50 text-left"
          onClick={() => toggleSection("expression")}
        >
          {expandedSections.has("expression") ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
          <Badge variant="outline" className="text-xs">
            F2
          </Badge>
          <span className="font-medium truncate flex-1">
            {tree.expression
              ? `${tree.expression.content_type}${tree.expression.language ? ` (${tree.expression.language})` : ""}`
              : "No Expression"}
          </span>
        </button>
        {expandedSections.has("expression") && tree.expression && (
          <div
            className={`flex items-center gap-2 pl-8 pr-2 py-1.5 cursor-pointer hover:bg-muted/30 ${
              selectedLevel === "expression" && selectedId === tree.expression.id ? "bg-primary/10" : ""
            }`}
            onClick={() => tree.expression && onSelect("expression", tree.expression.id)}
            data-testid="tree-node-expression"
          >
            <span className="truncate flex-1">
              {tree.expression.content_type} — {tree.expression.language || "unknown"}
            </span>
            {renderActions("expression", tree.expression.id)}
          </div>
        )}
      </div>

      {/* Manifestation */}
      <div>
        <button
          type="button"
          className="w-full flex items-center gap-2 p-2 hover:bg-muted/50 text-left"
          onClick={() => toggleSection("manifestation")}
        >
          {expandedSections.has("manifestation") ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
          <Badge variant="outline" className="text-xs">
            F3
          </Badge>
          <span className="font-medium truncate flex-1">
            #{tree.manifestation.id}
            {(tree.manifestation.meta?.type as string) ? ` — ${tree.manifestation.meta.type}` : ""}
          </span>
        </button>
        {expandedSections.has("manifestation") && (
          <div
            className={`flex items-center gap-2 pl-8 pr-2 py-1.5 cursor-pointer hover:bg-muted/30 ${
              selectedLevel === "manifestation" && selectedId === tree.manifestation.id ? "bg-primary/10" : ""
            }`}
            onClick={() => onSelect("manifestation", tree.manifestation.id)}
            data-testid="tree-node-manifestation"
          >
            <span className="truncate flex-1">
              #{tree.manifestation.id}
              {tree.manifestation.isbn13 ? ` — ISBN ${tree.manifestation.isbn13}` : ""}
            </span>
            {renderActions("manifestation", tree.manifestation.id)}
          </div>
        )}
      </div>

      {/* Items */}
      <div>
        <button
          type="button"
          className="w-full flex items-center gap-2 p-2 hover:bg-muted/50 text-left"
          onClick={() => toggleSection("items")}
        >
          {expandedSections.has("items") ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
          <Badge variant="outline" className="text-xs">
            F5
          </Badge>
          <span className="font-medium truncate flex-1">Items</span>
          <Badge variant="secondary" className="text-xs">
            {tree.items.length}
          </Badge>
        </button>
        {expandedSections.has("items") &&
          tree.items.map(item => (
            <div
              key={item.id}
              className={`flex items-center gap-2 pl-8 pr-2 py-1.5 cursor-pointer hover:bg-muted/30 ${
                selectedLevel === "item" && selectedId === item.id ? "bg-primary/10" : ""
              }`}
              onClick={() => onSelect("item", item.id)}
              data-testid={`tree-node-item-${item.id}`}
            >
              <span className="truncate flex-1">
                #{item.id} — {item.status}
                {item.condition ? ` (${item.condition})` : ""}
              </span>
              {renderActions("item", item.id)}
            </div>
          ))}
      </div>
    </div>
  );
}
