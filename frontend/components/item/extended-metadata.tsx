"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface ExtendedMetadataProps {
  meta: Record<string, any>;
}

export function ExtendedMetadata({ meta }: ExtendedMetadataProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const description = meta["Description"] as string | undefined;
  const categories = (meta["Categories"] as string[] | undefined) ?? [];

  // Filter out internal keys and keys already displayed elsewhere
  const hiddenKeys = new Set(["Title", "Authors", "Description", "Categories", "cover_status", "cover_source", "cover_url", "local_cover", "tags", "Year", "Pages", "Subtitle"]);
  const extraKeys = Object.keys(meta).filter(k => !hiddenKeys.has(k) && typeof meta[k] !== 'object');

  if (!description && categories.length === 0 && extraKeys.length === 0) return null;

  return (
    <div className="space-y-4 py-4">
      {/* Always Visible: Categories */}
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <Badge key={cat} variant="secondary">{cat}</Badge>
          ))}
        </div>
      )}

      {/* Always Visible: Description */}
      {description && (
        <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground">
          <p>{description}</p>
        </div>
      )}

      {/* Collapsible: Raw Metadata */}
      {extraKeys.length > 0 && (
        <div className="border rounded-lg p-4 bg-muted/30">
          <Button variant="ghost" size="sm" className="w-full justify-between" onClick={() => setIsExpanded(!isExpanded)}>
            <span className="font-semibold">Additional Details</span>
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>

          {isExpanded && (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 mt-4 text-sm">
              {extraKeys.map(key => (
                <div key={key} className="flex flex-col"><dt className="font-medium text-foreground">{key}</dt><dd className="text-muted-foreground break-words">{String(meta[key])}</dd></div>
              ))}
            </dl>
          )}
        </div>
      )}
    </div>
  );
}
