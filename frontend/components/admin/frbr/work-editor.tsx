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

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Save, Plus, MoreVertical, ArrowUpRight, Trash2, Layers, X, Search } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { transformMetaToFields, type WorkFormData, type MetaField } from "./types";
import { MetaFieldsEditor } from "./meta-fields-editor";
import { ContributorRowsEditor } from "./contributor-rows-editor";
import type { FrbrTree, FrbrContribution } from "@/lib/api/admin";
import { useDebounce } from "@/lib/hooks/use-debounce";
import { apiClient } from "@/lib/api/client";

interface WorkSearchResult {
  id: number;
  title: string;
}

/**
 * Props for the WorkEditor component.
 */
interface WorkEditorProps {
  tree: FrbrTree;
  onSubmit: (data: WorkFormData) => Promise<void>;
  onAddChild?: () => void;
  onEscalate?: () => void;
  onDelete?: () => void;
}

/** Work-level roles (Composition Event). */
const WORK_ROLES = ["author", "composer", "lyricist", "director", "writer"];

/**
 * A standard styled input field for admin forms.
 *
 * @param props - Component properties
 * @param props.name - Input name
 * @param props.defaultValue - Initial value
 * @param props.placeholder - Placeholder text
 * @param props.required - Whether the field is required
 * @param props.className - Additional CSS classes
 * @returns Input JSX element
 */
function InputField({
  name,
  defaultValue,
  placeholder,
  required,
  className = "",
}: {
  name: string;
  defaultValue?: string;
  placeholder?: string;
  required?: boolean;
  className?: string;
}) {
  return (
    <input
      name={name}
      defaultValue={defaultValue}
      placeholder={placeholder}
      required={required}
      className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${className}`}
    />
  );
}

/**
 * Form for editing Work (F1) entities.
 * Integrates title editing, dynamic metadata, board game mechanics,
 * series parts management, and action toolbars.
 *
 * @param props - Component properties
 * @param props.tree - The FRBR tree data
 * @param props.onSubmit - Submission handler
 * @param props.onAddChild - Optional callback for adding a child expression
 * @param props.onEscalate - Optional callback for escalating
 * @param props.onDelete - Optional callback for deleting
 * @returns Work editor JSX element
 */
export function WorkEditor({ tree, onSubmit, onAddChild, onEscalate, onDelete }: WorkEditorProps) {
  const [metaFields, setMetaFields] = useState<MetaField[]>(() =>
    transformMetaToFields(tree.work?.meta).filter(f => f.key !== "mechanics")
  );
  const [contributions, setContributions] = useState<FrbrContribution[]>(() => tree.work?.contributions ?? []);
  const [seriesMemberships, setSeriesMemberships] = useState<
    Array<{
      series_work_id: number;
      sequence: number;
      title?: string;
    }>
  >(() =>
    (tree.work?.series_memberships ?? []).map(sm => ({
      series_work_id: sm.series_work_id,
      sequence: sm.sequence,
      title: sm.title,
    }))
  );

  // Series search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<WorkSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [newSeriesSeq, setNewSeriesSeq] = useState("1");
  const [showResults, setShowResults] = useState(false);

  const debouncedSearch = useDebounce(searchQuery, 300);

  // Search works when query changes
  useEffect(() => {
    if (!debouncedSearch || debouncedSearch.length < 2) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    const controller = new AbortController();
    setIsSearching(true);

    apiClient
      .get<{ success: boolean; data: WorkSearchResult[] }>(
        `/v1/admin/works/search?q=${encodeURIComponent(debouncedSearch)}&limit=10`,
        { signal: controller.signal }
      )
      .then(res => {
        setSearchResults(res.data.data || []);
      })
      .catch(error => {
        if (error?.name !== "CanceledError" && error?.name !== "AbortError") {
          console.error("Search failed:", error);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsSearching(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [debouncedSearch]);

  const handleSelectSeries = (work: WorkSearchResult) => {
    if (seriesMemberships.some(sm => sm.series_work_id === work.id)) return;
    setSeriesMemberships(prev => [
      ...prev,
      {
        series_work_id: work.id,
        sequence: parseInt(newSeriesSeq, 10) || 0,
        title: work.title,
      },
    ]);
    setSearchQuery("");
    setSearchResults([]);
    setShowResults(false);
    setNewSeriesSeq("1");
  };

  const handleRemoveSeries = (sId: number) => {
    setSeriesMemberships(prev => prev.filter(sm => sm.series_work_id !== sId));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: WorkFormData = {
      title: formData.get("title") as string,
      metaFields,
      contributions,
      series_memberships: seriesMemberships,
    };
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="text-sm font-medium">Title</label>
        <InputField name="title" defaultValue={tree.work?.title ?? ""} required />
      </div>

      {/* Multi-series containers */}
      <div className="border rounded-lg p-3 space-y-3 bg-muted/20">
        <div className="flex items-center justify-between">
          <label className="text-sm font-semibold flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-primary" />
            Series Memberships
          </label>
          <span className="text-xs text-muted-foreground">Multi-Series Support</span>
        </div>

        {seriesMemberships.length > 0 ? (
          <div className="space-y-2">
            {seriesMemberships.map(sm => (
              <div
                key={sm.series_work_id}
                className="flex items-center gap-2 bg-background p-2 rounded-md border text-xs"
              >
                <span className="font-medium text-foreground">{sm.title || `Series Work #${sm.series_work_id}`}</span>
                <span className="text-muted-foreground">Seq: #{sm.sequence}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveSeries(sm.series_work_id)}
                  className="ml-auto text-muted-foreground hover:text-destructive p-1"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No series memberships attached.</p>
        )}

        <div className="space-y-2 pt-1">
          <div className="relative">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search for a series Work by title or ID..."
                  value={searchQuery}
                  onChange={e => {
                    setSearchQuery(e.target.value);
                    setShowResults(true);
                  }}
                  onFocus={() => setShowResults(true)}
                  className="flex h-8 w-full rounded-md border border-input bg-background pl-7 pr-2 text-xs"
                />
              </div>
              <input
                type="number"
                placeholder="Seq #"
                value={newSeriesSeq}
                onChange={e => setNewSeriesSeq(e.target.value)}
                className="flex h-8 w-16 rounded-md border border-input bg-background px-2 text-xs"
              />
            </div>

            {showResults && (searchQuery.length >= 2 || searchResults.length > 0) && (
              <div className="absolute top-full left-0 right-0 mt-1 max-h-48 overflow-y-auto bg-background border border-input rounded-md shadow-lg z-50">
                {isSearching ? (
                  <div className="p-2 text-xs text-muted-foreground text-center">Searching...</div>
                ) : searchResults.length > 0 ? (
                  searchResults.map(result => (
                    <button
                      key={result.id}
                      type="button"
                      onClick={() => handleSelectSeries(result)}
                      className="w-full text-left px-3 py-2 text-xs hover:bg-muted/50 border-b border-border/50 last:border-b-0"
                    >
                      <span className="font-medium">#{result.id}</span>
                      <span className="ml-2 text-muted-foreground">{result.title}</span>
                    </button>
                  ))
                ) : searchQuery.length >= 2 ? (
                  <div className="p-2 text-xs text-muted-foreground text-center">No works found</div>
                ) : null}
              </div>
            )}
          </div>
        </div>
      </div>

      <MetaFieldsEditor fields={metaFields} onChange={setMetaFields} />
      <ContributorRowsEditor roles={WORK_ROLES} contributions={contributions} onChange={setContributions} />
      <div className="flex items-center gap-2">
        <Button type="submit">
          <Save className="w-4 h-4 mr-2" />
          Save Work
        </Button>
        <Button type="button" variant="outline" onClick={onAddChild} disabled={!onAddChild}>
          <Plus className="w-4 h-4 mr-2" />
          Add Child
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" type="button">
              <MoreVertical className="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onEscalate} disabled={!onEscalate}>
              <ArrowUpRight className="w-4 h-4 mr-2" />
              Escalate
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onDelete} disabled={!onDelete} className="text-destructive">
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </form>
  );
}
