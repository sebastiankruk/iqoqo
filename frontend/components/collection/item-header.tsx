"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { queryKeys, useManifestationWithPolling, useRegenerateCover } from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";
import { useQueryClient } from "@tanstack/react-query";

interface ItemHeaderProps {
  initialItem: Item;
}

export function ItemHeader({ initialItem }: ItemHeaderProps) {
  // Use our hook to handle the real-time update via polling
  const { item, } = useManifestationWithPolling(initialItem);
  const qc = useQueryClient(); // Add this to access the React Query cache!
  const regenerateCover = useRegenerateCover();
  const [isRequesting, setIsRequesting] = useState(false);

  const isPending = item?.cover_status === 'pending';

  const handleRegenerate = async () => {
    if (!item.manifestation_id) return;

    setIsRequesting(true);
    try {
      await regenerateCover.mutateAsync(item.manifestation_id);
      // Tell React Query to update the cache for this specific item
      qc.setQueryData(queryKeys.item(item.id), (prev: Item | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          cover_status: 'pending'
        };
      });
    } catch (error) {
      console.error("Failed to schedule regeneration:", error);
    } finally {
      setIsRequesting(false);
    }
  };

  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRegenerate}
          disabled={isPending || isRequesting}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isPending ? 'animate-spin' : ''}`} />
          {isPending ? "Generating..." : "Regenerate Cover"}
        </Button>
      </div>
    </div>
  );
}
