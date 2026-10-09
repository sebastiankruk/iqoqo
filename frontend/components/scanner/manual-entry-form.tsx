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

import React from "react";
import { Save, X, ImagePlus, Loader2, Search, Camera, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api/client";

import { ScanFormat, SCAN_FORMATS } from "@/types/frbr";
import { MEDIA_REGISTRY } from "@/lib/media";

export interface ManualEntryData {
  title: string;
  authors: string;
  identifier: string;
  publisher: string;
  year: string;
  format: ScanFormat;
  coverFile?: File | null;
}

export interface ManualEntryFormProps {
  onSubmit: (data: ManualEntryData) => Promise<void>;
  onCancel: () => void;
  initialIdentifier?: string;
  initialFormat?: ScanFormat;
  initialTitle?: string;
  initialAuthors?: string;
  initialCoverFile?: File | null;
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
  initialCoverFile = null,
}: ManualEntryFormProps) {
  const t = useTranslations("scanner");
  const [formData, setFormData] = React.useState<ManualEntryData>({
    title: initialTitle,
    authors: initialAuthors,
    identifier: initialIdentifier,
    publisher: "",
    year: "",
    format: initialFormat,
    coverFile: initialCoverFile,
  });
  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null);
  const galleryInputRef = React.useRef<HTMLInputElement | null>(null);
  const cameraInputRef = React.useRef<HTMLInputElement | null>(null);

  const [isSubmitting, setIsSubmitting] = React.useState(false);
  /** Phase 4 UX Polish: tracks in-flight metadata lookup to prevent double-click */
  const [isLookingUp, setIsLookingUp] = React.useState(false);

  // Manage preview object URL lifecycle
  React.useEffect(() => {
    if (formData.coverFile) {
      const url = URL.createObjectURL(formData.coverFile);
      setPreviewUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    } else {
      setPreviewUrl(null);
    }
  }, [formData.coverFile]);

  // Sync state with props if they change (e.g. from a new scan or extraction)
  React.useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setFormData(prev => ({
      ...prev,
      title: initialTitle,
      authors: initialAuthors,
      identifier: initialIdentifier,
      format: initialFormat,
      ...(initialCoverFile !== undefined ? { coverFile: initialCoverFile } : {}),
    }));
  }, [initialTitle, initialAuthors, initialIdentifier, initialFormat, initialCoverFile]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    if (name === "format") {
      setFormData(prev => ({ ...prev, format: value as ScanFormat }));
      return;
    }
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  /**
   * Phase 4 UX Polish: Perform an inline metadata lookup for the current
   * identifier/ISBN so users can pre-populate form fields without re-scanning.
   *
   * The button is disabled and a spinner is shown while the request is in-flight
   * to prevent redundant requests and communicate that work is happening.
   */
  const handleLookup = async () => {
    if (!formData.identifier) return;
    setIsLookingUp(true);
    try {
      const res = await apiFetch<{
        title?: string;
        authors?: string;
        publisher?: string;
        year?: string;
      }>(`/lookup/${encodeURIComponent(formData.identifier)}`);
      if (res && res.title) {
        setFormData(prev => ({
          ...prev,
          title: res.title || prev.title,
          authors: res.authors || prev.authors,
          publisher: res.publisher || prev.publisher,
          year: res.year || prev.year,
        }));
        toast.success("Metadata found and populated.");
      } else {
        toast.error("No metadata found for this identifier.");
      }
    } catch {
      toast.error("Lookup failed. Please enter details manually.");
    } finally {
      setIsLookingUp(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    if (file) {
      setFormData(prev => ({ ...prev, coverFile: file }));
    }
  };

  const handleRemoveCover = () => {
    setFormData(prev => ({ ...prev, coverFile: null }));
    if (galleryInputRef.current) galleryInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
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
            {SCAN_FORMATS.map(groupId => (
              <optgroup key={groupId} label={MEDIA_REGISTRY[groupId].label}>
                <option value={groupId}>{MEDIA_REGISTRY[groupId].label} (Generic)</option>
                {Object.entries(MEDIA_REGISTRY)
                  .filter(([id, meta]) => meta.parent === groupId && id !== groupId)
                  .map(([id, meta]) => (
                    <option key={id} value={id}>
                      {meta.label}
                    </option>
                  ))}
              </optgroup>
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
          {/* Phase 4: inline Lookup button + spinner for UX feedback */}
          <div className="flex gap-2">
            <input
              id="manual-identifier"
              type="text"
              name="identifier"
              value={formData.identifier}
              onChange={handleChange}
              disabled={isSubmitting || isLookingUp}
              placeholder="e.g. 9780261102385"
              className="h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
            />
            <Button
              id="lookup-identifier-button"
              type="button"
              variant="secondary"
              onClick={handleLookup}
              disabled={!formData.identifier || isLookingUp || isSubmitting}
              aria-label="Look up metadata for identifier"
            >
              {isLookingUp ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              <span className="ml-2">{isLookingUp ? "Searching..." : "Lookup"}</span>
            </Button>
          </div>
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

        <div className="flex flex-col gap-2">
          <label htmlFor="manual-cover-gallery" className="text-sm font-medium text-foreground">
            {t("manualEntry.manualCoverUpload")}
          </label>
          <div className="flex flex-col gap-2">
            {formData.coverFile && previewUrl ? (
              <div className="flex items-center gap-3 rounded-lg border border-border p-2.5 bg-muted/20">
                <div className="relative h-16 w-16 overflow-hidden rounded-md border border-border bg-muted shrink-0">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={previewUrl} alt={t("manualEntry.coverPreview")} className="h-full w-full object-cover" />
                </div>
                <div className="flex flex-col gap-1.5 min-w-0 flex-1">
                  <span className="truncate text-xs font-medium text-foreground">{formData.coverFile.name}</span>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => galleryInputRef.current?.click()}
                      className="h-7 text-xs"
                    >
                      <ImagePlus className="mr-1 h-3.5 w-3.5 text-primary" />
                      {t("manualEntry.changeImage")}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={handleRemoveCover}
                      className="h-7 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                      <Trash2 className="mr-1 h-3.5 w-3.5" />
                      {t("manualEntry.removeImage")}
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => galleryInputRef.current?.click()}
                  className="flex h-9 items-center gap-2"
                >
                  <ImagePlus className="h-4 w-4 text-primary" />
                  {t("manualEntry.chooseFromPhotos")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => cameraInputRef.current?.click()}
                  className="flex h-9 items-center gap-2"
                >
                  <Camera className="h-4 w-4 text-primary" />
                  {t("manualEntry.takePhoto")}
                </Button>
              </div>
            )}
            <input
              ref={galleryInputRef}
              id="manual-cover-gallery"
              type="file"
              accept="image/*"
              aria-label={t("manualEntry.chooseFromPhotos")}
              onChange={handleFileChange}
              className="sr-only"
            />
            <input
              ref={cameraInputRef}
              id="manual-cover-camera"
              type="file"
              accept="image/*"
              capture="environment"
              aria-label={t("manualEntry.takePhoto")}
              onChange={handleFileChange}
              className="sr-only"
            />
          </div>
        </div>

        <Button type="submit" disabled={isSubmitting || isLookingUp || !formData.title} className="mt-4 w-full">
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
