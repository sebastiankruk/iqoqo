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
import { Plus, X, Pencil } from "lucide-react";
import { formatKeyForDisplay, type MetaField } from "./types";

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
export function EditableKeyField({ value, onChange }: EditableKeyFieldProps) {
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
        data-testid="editable-key-input"
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
        data-testid="edit-key-button"
      >
        <Pencil className="w-3 h-3" />
      </Button>
    </div>
  );
}

/**
 * Props for the MetaFieldsEditor component.
 */
interface MetaFieldsEditorProps {
  fields: MetaField[];
  onChange: (fields: MetaField[]) => void;
}

/**
 * A reusable dynamic metadata key-value editor.
 * Renders a list of editable key-value pairs with add/remove functionality.
 *
 * @param props - Component properties
 * @param props.fields - The current meta fields
 * @param props.onChange - Callback when fields change
 * @returns JSX element
 */
export function MetaFieldsEditor({ fields, onChange }: MetaFieldsEditorProps) {
  return (
    <div className="space-y-2">
      <h4 className="font-medium text-sm text-muted-foreground">Dynamic Metadata</h4>
      {fields.map((field, index) => (
        <div key={index} className="flex gap-2 items-center">
          <EditableKeyField
            value={field.key}
            onChange={newKey => {
              const newFields = [...fields];
              newFields[index].key = newKey;
              onChange(newFields);
            }}
          />
          <input
            placeholder="Value"
            value={field.value}
            onChange={e => {
              const newFields = [...fields];
              newFields[index].value = e.target.value;
              onChange(newFields);
            }}
            data-testid={`meta-value-${index}`}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex-1"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => onChange(fields.filter((_, i) => i !== index))}
            data-testid={`remove-meta-${index}`}
          >
            <X className="w-4 h-4 text-destructive" />
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => onChange([...fields, { key: "", value: "" }])}
        data-testid="add-meta-field"
      >
        <Plus className="w-4 h-4 mr-2" />
        Add Field
      </Button>
    </div>
  );
}
