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
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MEDIA_FORMATS, MEDIA_HIERARCHY } from "@/types/taxonomy";
import { transformMetaToFields, type ManifestationFormData, type MetaField } from "./types";
import { MetaFieldsEditor } from "./meta-fields-editor";
import { ContributorRowsEditor } from "./contributor-rows-editor";
import type { FrbrTree, FrbrContribution } from "@/lib/api/admin";

/**
 * Props for the ManifestationEditor component.
 */
interface ManifestationEditorProps {
  tree: FrbrTree;
  onSubmit: (data: ManifestationFormData) => Promise<void>;
  onAddChild?: () => void;
  onEscalate?: () => void;
  onDelete?: () => void;
}

/** Manifestation-level roles (Publication Event). */
const MANIFESTATION_ROLES = ["publisher", "studio", "distributor"];

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
 * Form for editing Manifestation (F3) entities.
 * Supports media hierarchy selection, ISBN-13/UPC/EAN identifiers,
 * publisher, publication date, and dynamic metadata.
 *
 * @param props - Component properties
 * @param props.tree - The FRBR tree data
 * @param props.onSubmit - Submission handler
 * @param props.onAddChild - Optional callback for adding a child item
 * @param props.onEscalate - Optional callback for escalating
 * @param props.onDelete - Optional callback for deleting
 * @returns Manifestation editor JSX element
 */
export function ManifestationEditor({ tree, onSubmit, onAddChild, onEscalate, onDelete }: ManifestationEditorProps) {
  const initialType = (tree.manifestation.meta?.type as string) || "book";
  const [type, setType] = useState(initialType);
  const initialMetaFields = transformMetaToFields(tree.manifestation.meta).filter(
    f => f.key !== "type" && f.key !== "mechanics"
  );
  const [metaFields, setMetaFields] = useState<MetaField[]>(initialMetaFields);
  const [contributions, setContributions] = useState<FrbrContribution[]>(
    () => tree.manifestation?.contributions ?? []
  );

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: ManifestationFormData = {
      type,
      isbn13: formData.get("isbn13") as string | undefined,
      upc: formData.get("upc") as string | undefined,
      ean: formData.get("ean") as string | undefined,
      publisher: formData.get("publisher") as string | undefined,
      publication_date: formData.get("publication_date") as string | undefined,
      metaFields,
      contributions,
    };
    await onSubmit(data);
  };

  const textFormats: string[] = MEDIA_HIERARCHY.text.formats.map(f => f.id);
  const legacyBookLike = ["Book", "Comic Book", "Manga", "Magazine", "Journal", "Newspaper", "Zine"];
  const isBookLike = textFormats.includes(type) || legacyBookLike.includes(type);

  const isValidFormat = (MEDIA_FORMATS as readonly string[]).includes(type);

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="text-sm font-medium">Type</label>
          <Select value={type} onValueChange={(val: string) => setType(val)}>
            <SelectTrigger className="w-full bg-background">
              <SelectValue placeholder="Select type..." />
            </SelectTrigger>
            <SelectContent>
              {!isValidFormat && <SelectItem value={type}>{type} (Legacy)</SelectItem>}
              {Object.entries(MEDIA_HIERARCHY).map(([catId, cat]) => (
                <SelectGroup key={catId}>
                  <SelectLabel>{cat.label}</SelectLabel>
                  {cat.formats.map(f => (
                    <SelectItem key={f.id} value={f.id}>
                      {f.label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              ))}
            </SelectContent>
          </Select>
        </div>

        {isBookLike && (
          <div>
            <label className="text-sm font-medium">ISBN-13</label>
            <InputField name="isbn13" defaultValue={tree.manifestation.isbn13 ?? ""} />
          </div>
        )}
        <div>
          <label className="text-sm font-medium">UPC</label>
          <InputField name="upc" defaultValue={tree.manifestation.upc ?? ""} />
        </div>
        <div>
          <label className="text-sm font-medium">EAN</label>
          <InputField name="ean" defaultValue={tree.manifestation.ean ?? ""} />
        </div>
        <div>
          <label className="text-sm font-medium">Publisher</label>
          <InputField name="publisher" defaultValue={tree.manifestation.publisher ?? ""} />
        </div>
        <div className="col-span-2">
          <label className="text-sm font-medium">Publication Date</label>
          <InputField
            name="publication_date"
            defaultValue={tree.manifestation.publication_date ?? ""}
            placeholder="YYYY-MM-DD"
          />
        </div>
      </div>
      <MetaFieldsEditor fields={metaFields} onChange={setMetaFields} />
      <ContributorRowsEditor roles={MANIFESTATION_ROLES} contributions={contributions} onChange={setContributions} />
      <div className="flex items-center gap-2">
        <Button type="submit">
          <Save className="w-4 h-4 mr-2" />
          Save Manifestation
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
