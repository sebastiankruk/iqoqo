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
import { Button } from "@/components/ui/button";
import { Save, Plus, MoreVertical, ArrowUpRight, Trash2 } from "lucide-react";
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

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: WorkFormData = {
      title: formData.get("title") as string,
      metaFields,
      contributions,
    };
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="text-sm font-medium">Title</label>
        <InputField name="title" defaultValue={tree.work?.title ?? ""} required />
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
