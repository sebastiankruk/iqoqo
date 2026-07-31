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

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getFrbrTree,
  updateFrbrEntity,
  searchFrbrEntities,
  type FrbrTree,
  type FrbrItem,
  type FrbrSearchResult,
} from "@/lib/api/admin";
import { toast } from "sonner";
import { Loader2, Plus, Save, RotateCcw, X, ChevronDown, ChevronRight, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { useWorkParts } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";
import { useProfile } from "@/lib/api/hooks";
import { PermissionName } from "@/lib/permissions";
import { useCreateEscalation } from "@/lib/api/escalations";
import { EXPRESSION_KINDS } from "@/types/frbr";
import { MEDIA_HIERARCHY } from "@/types/taxonomy";
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select";

interface MetaField {
  key: string;
  value: string;
}

/**
 * Converts a snake_case or camelCase key to Title Case for display.
 *
 * @param key - The key to convert
 * @returns Title cased version of the key
 */
function formatKeyForDisplay(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, c => c.toUpperCase());
}

interface FrbrEditorProps {
  manifestationId: number;
  onClose?: () => void;
}

interface WorkFormData {
  title: string;
  type?: string;
  metaFields: MetaField[];
}

interface ExpressionFormData {
  content_type?: string;
  language?: string;
  kind?: string;
  metaFields: MetaField[];
}

interface ManifestationFormData {
  type?: string;
  isbn13?: string;
  upc?: string;
  ean?: string;
  publisher?: string;
  publication_date?: string;
  metaFields: MetaField[];
}

interface ItemFormData {
  status?: string;
  condition?: string;
  metaFields: MetaField[];
}

/**
 * Transforms a metadata object into an array of key-value pairs for form editing.
 *
 * @param meta - The source metadata object
 * @returns Array of meta field pairs
 */
function transformMetaToFields(meta: Record<string, unknown> | null | undefined): MetaField[] {
  if (!meta || typeof meta !== "object") return [];
  return Object.entries(meta).map(([key, value]) => ({
    key,
    value: String(value ?? ""),
  }));
}

/**
 * Transforms an array of key-value pairs back into a metadata object.
 *
 * @param fields - The array of meta field pairs
 * @returns The metadata record
 */
function transformFieldsToMeta(fields: MetaField[]): Record<string, unknown> {
  return fields.reduce(
    (acc, field) => {
      if (field.key.trim()) {
        acc[field.key.trim()] = field.value;
      }
      return acc;
    },
    {} as Record<string, unknown>
  );
}

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
      className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    />
  );
}

/**
 * Props for the EditableKeyField component.
 */
interface EditableKeyFieldProps {
  value: string;
  onChange: (newValue: string) => void;
}

/**
 * A field that displays a key as title case with an edit pencil icon.
 * Clicking the pencil switches to an input field for editing the key.
 * Pressing Enter or blurring saves the change; pressing Escape cancels.
 *
 * @param root0 - The props object
 * @param root0.value - The current key value
 * @param root0.onChange - Callback when the key is changed
 * @returns JSX element
 */
function EditableKeyField({ value, onChange }: EditableKeyFieldProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      onChange(editValue);
      setIsEditing(false);
    } else if (e.key === "Escape") {
      setEditValue(value);
      setIsEditing(false);
    }
  };

  if (isEditing) {
    return (
      <input
        value={editValue}
        onChange={e => setEditValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          onChange(editValue);
          setIsEditing(false);
        }}
        autoFocus
        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 w-1/3 font-mono"
      />
    );
  }

  return (
    <div className="flex items-center gap-2 w-1/3">
      <span className="text-sm font-medium truncate flex-1" title={value}>
        {formatKeyForDisplay(value) || "Key"}
      </span>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-6 w-6 text-blue-500 hover:text-blue-700"
        onClick={() => {
          setEditValue(value);
          setIsEditing(true);
        }}
      >
        <Pencil className="w-3 h-3" />
      </Button>
    </div>
  );
}

/**
 * Form for editing Work (F1) entities.
 *
 * @param props - Component properties
 * @param props.tree - The FRBR tree data
 * @param props.onSubmit - Submission handler
 * @returns Work editor JSX element
 */
function WorkEditor({ tree, onSubmit }: { tree: FrbrTree; onSubmit: (data: WorkFormData) => Promise<void> }) {
  const [metaFields, setMetaFields] = useState<MetaField[]>(() => transformMetaToFields(tree.work?.meta));

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: WorkFormData = {
      title: formData.get("title") as string,
      metaFields,
    };
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="text-sm font-medium">Title</label>
        <InputField name="title" defaultValue={tree.work?.title ?? ""} required />
      </div>
      <div className="space-y-2">
        <h4 className="font-medium text-sm text-muted-foreground">Dynamic Metadata</h4>
        {metaFields.map((field, index) => (
          <div key={index} className="flex gap-2 items-center">
            <EditableKeyField
              value={field.key}
              onChange={newKey => {
                const newFields = [...metaFields];
                newFields[index].key = newKey;
                setMetaFields(newFields);
              }}
            />
            <input
              placeholder="Value"
              value={field.value}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].value = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setMetaFields(metaFields.filter((_, i) => i !== index))}
            >
              <X className="w-4 h-4 text-destructive" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setMetaFields([...metaFields, { key: "", value: "" }])}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Field
        </Button>
      </div>
      <Button type="submit">
        <Save className="w-4 h-4 mr-2" />
        Save Work
      </Button>
    </form>
  );
}
interface WorkPartsManagerProps {
  workId: number;
}

/**
 * Component to manage the parts of a complex work (series).
 * Shows existing parts and provides a form to add/remove parts.
 *
 * @param props - Component properties
 * @param props.workId - The ID of the container work
 * @returns JSX element
 */
function WorkPartsManager({ workId }: WorkPartsManagerProps) {
  const { data: partsResponse, refetch: refetchParts, isLoading } = useWorkParts(workId);
  const parts = partsResponse?.data ?? [];

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<FrbrSearchResult[]>([]);
  const [selectedWork, setSelectedWork] = useState<FrbrSearchResult | null>(null);
  const defaultSequence = parts.length + 1;
  const [sequenceInput, setSequenceInput] = useState(defaultSequence);
  const [searching, setSearching] = useState(false);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSequenceInput(parts.length + 1);
  }, [parts.length]);

  const handleSearch = async (val: string) => {
    setSearchQuery(val);
    if (val.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const res = await searchFrbrEntities(val, "work", 10);
      setSearchResults(res.filter(w => w.id !== workId));
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setSearching(false);
    }
  };

  const handleAddPart = async () => {
    if (!selectedWork) return;
    setAdding(true);
    try {
      await apiClient.post(`/works/${workId}/parts`, {
        part_work_id: selectedWork.id,
        sequence: sequenceInput,
      });
      toast.success(`Added "${selectedWork.title}" as part of this series`);
      setSelectedWork(null);
      setSearchQuery("");
      setSearchResults([]);
      refetchParts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add part");
    } finally {
      setAdding(false);
    }
  };

  const handleRemovePart = async (partWorkId: number, title: string) => {
    try {
      await apiClient.delete(`/works/${workId}/parts/${partWorkId}`);
      toast.success(`Removed "${title}" from series`);
      refetchParts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove part");
    }
  };

  return (
    <div className="mt-8 border-t pt-6 space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Series / Complex Work Parts</h3>
        <p className="text-sm text-muted-foreground">
          Define this work as a complex work (series/anthology) and manage its children.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="animate-spin h-6 w-6 text-muted-foreground" />
        </div>
      ) : parts.length === 0 ? (
        <div className="text-center py-6 border border-dashed rounded-lg bg-muted/20">
          <p className="text-sm text-muted-foreground">This work is currently not defined as a series.</p>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden bg-card divide-y">
          {parts.map(part => (
            <div key={part.part_work_id} className="flex items-center justify-between p-3 sm:px-4 hover:bg-muted/30">
              <div className="flex items-center gap-3 min-w-0">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                  {part.sequence}
                </span>
                <span className="font-medium text-sm truncate">{part.title}</span>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:bg-destructive/10"
                onClick={() => handleRemovePart(part.part_work_id, part.title)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="bg-muted/10 border rounded-lg p-4 space-y-4">
        <h4 className="text-sm font-semibold">Add Part Work</h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="sm:col-span-2 relative">
            <label className="text-xs font-medium text-muted-foreground block mb-1">Search Work</label>
            {selectedWork ? (
              <div className="flex items-center justify-between h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                <span className="truncate font-medium">{selectedWork.title}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-muted-foreground hover:text-foreground"
                  onClick={() => setSelectedWork(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <>
                <input
                  placeholder="Type to search works..."
                  value={searchQuery}
                  onChange={e => handleSearch(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
                {searching && (
                  <div className="absolute right-3 top-8">
                    <Loader2 className="animate-spin h-4 w-4 text-muted-foreground" />
                  </div>
                )}
                {searchResults.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 border rounded-md bg-popover text-popover-foreground shadow-md max-h-60 overflow-auto divide-y">
                    {searchResults.map(work => (
                      <button
                        key={work.id}
                        type="button"
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                        onClick={() => {
                          setSelectedWork(work);
                          setSearchResults([]);
                        }}
                      >
                        {work.title}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1">Sequence Number</label>
            <input
              type="number"
              min="1"
              value={sequenceInput}
              onChange={e => setSequenceInput(parseInt(e.target.value, 10) || 1)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
        </div>
        <Button type="button" disabled={!selectedWork || adding} onClick={handleAddPart} className="w-full sm:w-auto">
          {adding ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
          Add to Series
        </Button>
      </div>
    </div>
  );
}

/**
 * Form for editing Expression (F2) entities.
 *
 * @param props - Component properties
 * @param props.tree - The FRBR tree data
 * @param props.onSubmit - Submission handler
 * @returns Expression editor JSX element
 */
function ExpressionEditor({
  tree,
  onSubmit,
}: {
  tree: FrbrTree;
  onSubmit: (data: ExpressionFormData) => Promise<void>;
}) {
  const initialType = tree.expression?.content_type ?? "";
  const [type, setType] = useState(initialType);
  const initialKind = tree.expression?.kind ?? "";
  const [kind, setKind] = useState(initialKind);
  const [metaFields, setMetaFields] = useState<MetaField[]>(() => transformMetaToFields(tree.expression?.meta));

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: ExpressionFormData = {
      content_type: type,
      language: formData.get("language") as string | undefined,
      kind,
      metaFields,
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
          <InputField name="language" defaultValue={tree.expression?.language ?? ""} placeholder="e.g., en, pl" />
        </div>
      </div>
      <div className="space-y-2">
        <h4 className="font-medium text-sm text-muted-foreground">Dynamic Metadata</h4>
        {metaFields.map((field, index) => (
          <div key={index} className="flex gap-2 items-center">
            <EditableKeyField
              value={field.key}
              onChange={newKey => {
                const newFields = [...metaFields];
                newFields[index].key = newKey;
                setMetaFields(newFields);
              }}
            />
            <input
              placeholder="Value"
              value={field.value}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].value = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setMetaFields(metaFields.filter((_, i) => i !== index))}
            >
              <X className="w-4 h-4 text-destructive" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setMetaFields([...metaFields, { key: "", value: "" }])}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Field
        </Button>
      </div>
      <Button type="submit">
        <Save className="w-4 h-4 mr-2" />
        Save Expression
      </Button>
    </form>
  );
}

/**
 * Form for editing Manifestation (F3) entities.
 *
 * @param props - Component properties
 * @param props.tree - The FRBR tree data
 * @param props.onSubmit - Submission handler
 * @returns Manifestation editor JSX element
 */
function ManifestationEditor({
  tree,
  onSubmit,
}: {
  tree: FrbrTree;
  onSubmit: (data: ManifestationFormData) => Promise<void>;
}) {
  const initialType = (tree.manifestation.meta?.type as string) || "book";
  const [type, setType] = useState(initialType);
  const initialMetaFields = transformMetaToFields(tree.manifestation.meta).filter(f => f.key !== "type");
  const [metaFields, setMetaFields] = useState<MetaField[]>(initialMetaFields);

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
    };
    await onSubmit(data);
  };

  const textFormats: string[] = MEDIA_HIERARCHY.text.formats.map(f => f.id);
  const legacyBookLike = ["Book", "Comic Book", "Manga", "Magazine", "Journal", "Newspaper", "Zine"];
  const isBookLike = textFormats.includes(type) || legacyBookLike.includes(type);

  const allFormats = Object.values(MEDIA_HIERARCHY).flatMap((cat: { formats: { id: string; label: string }[] }) => cat.formats);
  const isValidFormat = allFormats.some((f: { id: string }) => f.id === type);

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
      <div className="space-y-2">
        <h4 className="font-medium text-sm text-muted-foreground">Dynamic Metadata</h4>
        {metaFields.map((field, index) => (
          <div key={index} className="flex gap-2 items-center">
            <EditableKeyField
              value={field.key}
              onChange={newKey => {
                const newFields = [...metaFields];
                newFields[index].key = newKey;
                setMetaFields(newFields);
              }}
            />
            <input
              placeholder="Value"
              value={field.value}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].value = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setMetaFields(metaFields.filter((_, i) => i !== index))}
            >
              <X className="w-4 h-4 text-destructive" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setMetaFields([...metaFields, { key: "", value: "" }])}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Field
        </Button>
      </div>
      <Button type="submit">
        <Save className="w-4 h-4 mr-2" />
        Save Manifestation
      </Button>
    </form>
  );
}

/**
 * Form for editing Item (F5) entities.
 *
 * @param props - Component properties
 * @param props.item - The FRBR item data
 * @param props.onSubmit - Submission handler
 * @returns Item editor JSX element
 */
function ItemEditor({ item, onSubmit }: { item: FrbrItem; onSubmit: (data: ItemFormData) => Promise<void> }) {
  const [metaFields, setMetaFields] = useState<MetaField[]>(() => transformMetaToFields(item.meta));

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: ItemFormData = {
      status: formData.get("status") as string | undefined,
      condition: formData.get("condition") as string | undefined,
      metaFields,
    };
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">Status</label>
          <InputField name="status" defaultValue={item.status ?? ""} placeholder="available, lent, lost, wish_list" />
        </div>
        <div>
          <label className="text-sm font-medium">Condition</label>
          <InputField name="condition" defaultValue={item.condition ?? ""} placeholder="Like New, Good, Fair" />
        </div>
      </div>
      <div className="space-y-2">
        <h4 className="font-medium text-sm text-muted-foreground">Dynamic Metadata</h4>
        {metaFields.map((field, index) => (
          <div key={index} className="flex gap-2 items-center">
            <EditableKeyField
              value={field.key}
              onChange={newKey => {
                const newFields = [...metaFields];
                newFields[index].key = newKey;
                setMetaFields(newFields);
              }}
            />
            <input
              placeholder="Value"
              value={field.value}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].value = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setMetaFields(metaFields.filter((_, i) => i !== index))}
            >
              <X className="w-4 h-4 text-destructive" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setMetaFields([...metaFields, { key: "", value: "" }])}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Field
        </Button>
      </div>
      <Button type="submit">
        <Save className="w-4 h-4 mr-2" />
        Save Item
      </Button>
    </form>
  );
}

/**
 * Main FRBR Editor component that manages state for the entire hierarchy.
 *
 * @param props - Component properties
 * @param props.manifestationId - The manifestation ID to load
 * @param props.onClose - Optional callback when the editor is closed
 * @returns FRBR editor JSX element
 */
export function FrbrEditor({ manifestationId, onClose }: FrbrEditorProps) {
  const [tree, setTree] = useState<FrbrTree | null>(null);
  const [lastFetched, setLastFetched] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"work" | "expression" | "manifestation" | "items">("manifestation");
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());
  const { data: profile } = useProfile();
  const createEscalation = useCreateEscalation();
  const hasWriteMetadata = Boolean(profile?.permissions?.includes(PermissionName.WRITE_METADATA));
  const hasEscalateRequest = Boolean(profile?.permissions?.includes(PermissionName.ESCALATE_REQUEST));

  const [itemFilter, setItemFilter] = useState({ owner: "", status: "", condition: "" });

  const fetchTree = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFrbrTree(manifestationId);
      setTree(data);
      setLastFetched(Date.now());
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load FRBR tree";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [manifestationId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchTree();
  }, [fetchTree]);

  const handleWorkSubmit = async (data: WorkFormData) => {
    if (!tree?.work) return;
    try {
      const meta = transformFieldsToMeta(data.metaFields);
      await updateFrbrEntity("work", tree.work.id, { title: data.title, meta });
      toast.success("Work updated successfully");
      await fetchTree();
    } catch (err) {
      toast.error(`Failed to update work: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleExpressionSubmit = async (data: ExpressionFormData) => {
    if (!tree?.expression) return;
    try {
      const meta = transformFieldsToMeta(data.metaFields);
      await updateFrbrEntity("expression", tree.expression.id, {
        content_type: data.content_type,
        language: data.language,
        kind: data.kind,
        meta,
      });
      toast.success("Expression updated successfully");
      await fetchTree();
    } catch (err) {
      toast.error(`Failed to update expression: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleManifestationSubmit = async (data: ManifestationFormData) => {
    if (!tree?.manifestation) return;
    try {
      const originalType = tree.manifestation.meta?.type as string;
      const typeChanged = data.type && data.type !== originalType;

      if (!hasWriteMetadata) {
        if (typeChanged && hasEscalateRequest) {
          await createEscalation.mutateAsync({
            level: "manifestation",
            targetId: tree.manifestation.id,
            data: {
              request_type: "change_type",
              field_name: "type",
              current_value: originalType,
              suggested_value: data.type ?? "",
              note: "Type change suggested via editor",
            },
          });
          toast.success("Type change requested via User Requests.");
        } else {
          toast.error("You do not have permission to update metadata.");
        }
        return;
      }

      const meta = transformFieldsToMeta(data.metaFields);
      if (data.type) {
        meta.type = data.type;
      }

      await updateFrbrEntity("manifestation", tree.manifestation.id, {
        isbn13: data.isbn13,
        upc: data.upc,
        ean: data.ean,
        publisher: data.publisher,
        publication_date: data.publication_date,
        meta,
      });
      toast.success("Manifestation updated successfully");
      await fetchTree();
    } catch (err) {
      toast.error(`Failed to update manifestation: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleItemSubmit = async (data: ItemFormData, itemId: number) => {
    try {
      const meta = transformFieldsToMeta(data.metaFields);
      await updateFrbrEntity("item", itemId, {
        status: data.status,
        condition: data.condition,
        meta,
      });
      toast.success("Item updated successfully");
      await fetchTree();
    } catch (err) {
      toast.error(`Failed to update item: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const toggleItemExpanded = (itemId: number) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  const filteredItems =
    tree?.items.filter(item => {
      if (
        itemFilter.owner &&
        !(
          item.owner_name?.toLowerCase().includes(itemFilter.owner.toLowerCase()) ||
          item.owner_id.toLowerCase().includes(itemFilter.owner.toLowerCase())
        )
      ) {
        return false;
      }
      if (itemFilter.status && item.status.toLowerCase() !== itemFilter.status.toLowerCase()) {
        return false;
      }
      if (
        itemFilter.condition &&
        !(item.condition?.toLowerCase().includes(itemFilter.condition.toLowerCase()) ?? false)
      ) {
        return false;
      }
      return true;
    }) ?? [];

  if (loading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="animate-spin w-8 h-8" />
      </div>
    );
  }

  if (error || !tree) {
    return (
      <div className="text-center p-8">
        <p className="text-destructive">{error ?? "Failed to load FRBR hierarchy"}</p>
        <Button variant="outline" className="mt-4" onClick={fetchTree}>
          <RotateCcw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center bg-muted/50 p-2 rounded-lg mb-4">
        <Select
          value={activeTab}
          onValueChange={(value: "work" | "expression" | "manifestation" | "items") => setActiveTab(value)}
        >
          <SelectTrigger className="w-[200px] bg-background">
            <SelectValue placeholder="Select level" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="work">Work (F1)</SelectItem>
            <SelectItem value="expression">Expression (F2)</SelectItem>
            <SelectItem value="manifestation">Manifestation (F3)</SelectItem>
            <SelectItem value="items">Items (F5)</SelectItem>
          </SelectContent>
        </Select>
        {onClose && (
          <Button type="button" variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Button>
        )}
      </div>

      {activeTab === "work" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Work</CardTitle>
            <CardDescription>The creative foundation (F1 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            {tree.work ? (
              <>
                <WorkEditor key={`${tree.work.id}-${lastFetched}`} tree={tree} onSubmit={handleWorkSubmit} />
                <WorkPartsManager workId={tree.work.id} />
              </>
            ) : (
              <p className="text-muted-foreground">No Work associated with this manifestation.</p>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "expression" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Expression</CardTitle>
            <CardDescription>The intellectual artistic form (F2 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            {tree.expression ? (
              <ExpressionEditor key={`${tree.expression.id}-${lastFetched}`} tree={tree} onSubmit={handleExpressionSubmit} />
            ) : (
              <p className="text-muted-foreground">No Expression associated with this manifestation.</p>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "manifestation" && (
        <Card>
          <CardHeader>
            <CardTitle>
              Edit Manifestation{" "}
              <Link
                href={`/manifestation/${tree.manifestation.id}`}
                className="text-muted-foreground hover:underline hover:text-primary transition-colors"
                target="_blank"
              >
                #{tree.manifestation.id}
              </Link>
            </CardTitle>
            <CardDescription>The physical embodiment (F3 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            <ManifestationEditor key={`${tree.manifestation.id}-${lastFetched}`} tree={tree} onSubmit={handleManifestationSubmit} />
          </CardContent>
        </Card>
      )}

      {activeTab === "items" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Items</CardTitle>
            <CardDescription>Individual copies (F5 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            {tree.items.length === 0 ? (
              <p className="text-muted-foreground">No items associated with this manifestation.</p>
            ) : (
              <div className="space-y-4">
                <div className="flex gap-4 items-end">
                  <div className="flex-1">
                    <label className="text-xs text-muted-foreground mb-1 block">Owner</label>
                    <input
                      placeholder="Filter by owner name or email"
                      value={itemFilter.owner}
                      onChange={e => setItemFilter(prev => ({ ...prev, owner: e.target.value }))}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    />
                  </div>
                  <div className="w-40">
                    <label className="text-xs text-muted-foreground mb-1 block">Status</label>
                    <select
                      value={itemFilter.status}
                      onChange={e => setItemFilter(prev => ({ ...prev, status: e.target.value }))}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    >
                      <option value="">All</option>
                      <option value="available">available</option>
                      <option value="lent">lent</option>
                      <option value="lost">lost</option>
                      <option value="wish_list">wish_list</option>
                    </select>
                  </div>
                  <div className="w-40">
                    <label className="text-xs text-muted-foreground mb-1 block">Condition</label>
                    <input
                      placeholder="Filter by condition"
                      value={itemFilter.condition}
                      onChange={e => setItemFilter(prev => ({ ...prev, condition: e.target.value }))}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    />
                  </div>
                </div>
                <div className="border rounded-lg divide-y">
                  {filteredItems.map(item => (
                    <div key={item.id}>
                      <button
                        type="button"
                        className="w-full flex items-center justify-between p-4 hover:bg-muted/50 text-left"
                        onClick={() => toggleItemExpanded(item.id)}
                      >
                        <div className="flex items-center gap-3">
                          {expandedItems.has(item.id) ? (
                            <ChevronDown className="w-4 h-4 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-muted-foreground" />
                          )}
                          <div>
                            <span className="font-medium">
                              <Link
                                href={`/item/${item.id}`}
                                className="hover:underline hover:text-primary transition-colors"
                                target="_blank"
                                onClick={e => e.stopPropagation()}
                              >
                                Item #{item.id}
                              </Link>
                            </span>
                            <span className="text-sm text-muted-foreground ml-2">
                              {item.status} {item.condition && `• ${item.condition}`}
                            </span>
                          </div>
                        </div>
                        <span
                          className="text-sm text-muted-foreground truncate max-w-[200px]"
                          title={item.owner_name || item.owner_id}
                        >
                          {item.owner_name || item.owner_id}
                        </span>
                      </button>
                      {expandedItems.has(item.id) && (
                        <div className="p-4 pt-0 border-t bg-muted/20">
                          <ItemEditor key={`${item.id}-${lastFetched}`} item={item} onSubmit={data => handleItemSubmit(data, item.id)} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
