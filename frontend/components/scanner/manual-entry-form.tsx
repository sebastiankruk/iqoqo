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
/**
 * Manual entry form component for adding items when lookup fails.
 *
 * @module components/scanner/manual-entry-form
 */
"use client";

import React, { useState } from "react";
import { Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";

import { ScanFormat, SCAN_FORMATS } from "@/types/frbr";
import { MEDIA_REGISTRY } from "@/lib/media";

export interface ManualEntryData {
  title: string;
  authors: string;
  identifier: string;
  publisher: string;
  year: string;
  format: ScanFormat;
}

interface ManualEntryFormProps {
  onSubmit: (data: ManualEntryData) => Promise<void>;
  onCancel: () => void;
  initialIdentifier?: string;
  initialFormat?: ScanFormat;
  initialTitle?: string;
  initialAuthors?: string;
}

/**
 * A form component for manually entering item metadata.
 *
 * @param props - Component props
 * @param props.onSubmit - Callback for form submission
 * @param props.onCancel - Callback for cancellation
 * @param props.initialIdentifier - Initial identifier (ISBN/UPC)
 * @param props.initialFormat - Initial media format
 * @param props.initialTitle - Initial title if already partially known
 * @param props.initialAuthors - Initial authors if already partially known
 * @returns {JSX.Element} The rendered form element
 */
export function ManualEntryForm({
  onSubmit,
  onCancel,
  initialIdentifier = "",
  initialFormat = "book",
  initialTitle = "",
  initialAuthors = "",
}: ManualEntryFormProps) {
  const [formData, setFormData] = useState<ManualEntryData>({
    title: initialTitle,
    authors: initialAuthors,
    identifier: initialIdentifier,
    publisher: "",
    year: "",
    format: initialFormat,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    if (name === "format") {
      setFormData(prev => ({ ...prev, format: value as ScanFormat }));
      return;
    }
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(formData);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex w-full flex-col bg-card px-6 py-4">
      <div className="mb-4 flex items-center justify-between border-b border-border pb-4">
        <h3 className="text-lg font-semibold tracking-tight text-foreground">Manual Item Entry</h3>
        <Button variant="ghost" size="icon" onClick={onCancel} aria-label="Close manual entry" className="rounded-full">
          <X className="h-5 w-5" />
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="manual-format" className="text-sm font-medium text-foreground">
            Format
          </label>
          <select
            id="manual-format"
            name="format"
            value={formData.format}
            onChange={handleChange}
            className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {SCAN_FORMATS.map(f => (
              <option key={f} value={f}>
                {MEDIA_REGISTRY[f].label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="manual-title" className="text-sm font-medium text-foreground">
            Title *
          </label>
          <input
            id="manual-title"
            required
            type="text"
            name="title"
            value={formData.title}
            onChange={handleChange}
            placeholder="e.g. The Lord of the Rings"
            className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="manual-authors" className="text-sm font-medium text-foreground">
            Creator(s)
          </label>
          <input
            id="manual-authors"
            type="text"
            name="authors"
            value={formData.authors}
            onChange={handleChange}
            placeholder="Comma separated (e.g. Director, Author)"
            className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="manual-identifier" className="text-sm font-medium text-foreground">
            Identifier (ISBN/UPC)
          </label>
          <input
            id="manual-identifier"
            type="text"
            name="identifier"
            value={formData.identifier}
            onChange={handleChange}
            placeholder="e.g. 9780261102385"
            className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="manual-publisher" className="text-sm font-medium text-foreground">
              Publisher/Label
            </label>
            <input
              id="manual-publisher"
              type="text"
              name="publisher"
              value={formData.publisher}
              onChange={handleChange}
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="manual-year" className="text-sm font-medium text-foreground">
              Year
            </label>
            <input
              id="manual-year"
              type="text"
              name="year"
              value={formData.year}
              onChange={handleChange}
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <Button type="submit" disabled={isSubmitting || !formData.title} className="mt-4 w-full">
          {isSubmitting ? (
            <>
              <Save className="mr-2 h-5 w-5 animate-pulse" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-5 w-5" />
              Save Manual Entry
            </>
          )}
        </Button>
      </form>
    </div>
  );
}
