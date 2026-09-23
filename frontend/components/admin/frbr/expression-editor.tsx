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
import { Save, Plus, MoreVertical, ArrowUpRight, Trash2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EXPRESSION_KINDS } from "@/types/frbr";
import { formatKeyForDisplay, transformMetaToFields, type ExpressionFormData, type MetaField } from "./types";
import { MetaFieldsEditor } from "./meta-fields-editor";
import { ContributorRowsEditor } from "./contributor-rows-editor";
import type { FrbrTree, FrbrContribution } from "@/lib/api/admin";

/**
 * Props for the ExpressionEditor component.
 */
interface ExpressionEditorProps {
  tree: FrbrTree;
  onSubmit: (data: ExpressionFormData) => Promise<void>;
  onAddChild?: () => void;
  onEscalate?: () => void;
  onDelete?: () => void;
}

/** Expression-level roles (Performance Event). */
const EXPRESSION_ROLES = ["performer", "narrator", "conductor", "actor"];

/**
 * Form for editing Expression (F2) entities.
 * Supports content type selection, language, expression kind,
 * dynamic metadata, and action toolbars.
 *
 * @param props - Component properties
 * @param props.tree - The FRBR tree data
 * @param props.onSubmit - Submission handler
 * @param props.onAddChild - Optional callback for adding a child manifestation
 * @param props.onEscalate - Optional callback for escalating
 * @param props.onDelete - Optional callback for deleting
 * @returns Expression editor JSX element
 */
export function ExpressionEditor({ tree, onSubmit, onAddChild, onEscalate, onDelete }: ExpressionEditorProps) {
  const initialType = tree.expression?.content_type ?? "text";
  const [type, setType] = useState(initialType);
  const initialKind = tree.expression?.kind ?? "";
  const [kind, setKind] = useState(initialKind);
  const [metaFields, setMetaFields] = useState<MetaField[]>(() => transformMetaToFields(tree.expression?.meta));
  const [contributions, setContributions] = useState<FrbrContribution[]>(
    () => tree.expression?.contributions ?? []
  );

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setType(tree.expression?.content_type ?? "text");
    setKind(tree.expression?.kind ?? "");
    setMetaFields(transformMetaToFields(tree.expression?.meta));
    setContributions(tree.expression?.contributions ?? []);
  }, [tree.expression?.content_type, tree.expression?.kind, tree.expression?.meta, tree.expression?.contributions]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: ExpressionFormData = {
      content_type: type,
      language: formData.get("language") as string | undefined,
      kind,
      metaFields,
      contributions,
    };
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">Content Type</label>
          <select
            name="content_type"
            value={type}
            onChange={e => setType(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <option value="text">Text (Book/Comic/Manga/Magazine)</option>
            <option value="image">Image (Artwork)</option>
            <option value="audio">Audio (Music/Audiobook/Podcast)</option>
            <option value="video">Video (Movie/TV Show/Anime)</option>
            <option value="software">Software (Video Game)</option>
            <option value="object">Object (Board Game/Model/Merch)</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Kind</label>
          <select
            name="kind"
            value={kind}
            onChange={e => setKind(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <option value="">Studio / Default</option>
            {EXPRESSION_KINDS.map(k => (
              <option key={k} value={k}>
                {formatKeyForDisplay(k)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Language</label>
          <input
            name="language"
            defaultValue={tree.expression?.language ?? ""}
            placeholder="e.g., en, pl"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>
      </div>
      <MetaFieldsEditor fields={metaFields} onChange={setMetaFields} />
      <ContributorRowsEditor roles={EXPRESSION_ROLES} contributions={contributions} onChange={setContributions} />
      <div className="flex items-center gap-2">
        <Button type="submit">
          <Save className="w-4 h-4 mr-2" />
          Save Expression
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
