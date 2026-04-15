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

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import { apiClient } from "@/lib/api/client";
import { ImageIcon, Maximize2 } from "lucide-react";
import { resolveApiUrl } from "@/lib/utils";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

interface ImageScan {
  id: number;
  url: string;
  label: string;
  source: string;
  added_at: string;
}

/**
 * Component for viewing additional scans of a manifestation.
 *
 * @param {object} props - Component props.
 * @param {number} props.manifestationId - ID of the manifestation.
 * @returns {JSX.Element}
 */
export function MultiScanGallery({ manifestationId }: { manifestationId: number }) {

  const { data: scans, isLoading } = useQuery<ImageScan[]>({
    queryKey: ["manifestation", manifestationId, "images"],
    queryFn: async () => {
      const res = await apiClient.get(`/manifestations/${manifestationId}/images`);
      return res.data.data;
    },
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="aspect-square animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    );
  }

  if (!scans || scans.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed border-border/40 rounded-2xl bg-muted/5">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/50 mb-4">
          <ImageIcon className="h-6 w-6 text-muted-foreground/40" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">No additional scans</h3>
        <p className="text-xs text-muted-foreground mt-1 px-4">
          Front cover is displayed above. Other scans like discs, back covers, or booklets will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
      {scans.map(scan => (
        <Dialog key={scan.id}>
          <DialogTrigger asChild>
            <button className="group relative aspect-square overflow-hidden rounded-xl border bg-card/50 transition-all hover:ring-2 hover:ring-primary/50 text-left">
              <Image
                src={resolveApiUrl(scan.url)}
                alt={scan.label}
                fill
                unoptimized
                className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-black/0 transition-colors group-hover:bg-black/20" />
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2 opacity-0 transition-opacity group-hover:opacity-100">
                <p className="text-[10px] font-bold uppercase tracking-widest text-white truncate">{scan.label}</p>
              </div>
              <div className="absolute right-2 top-2 rounded-full bg-black/50 p-1.5 text-white opacity-0 transition-opacity group-hover:opacity-100">
                <Maximize2 className="h-3 w-3" />
              </div>
            </button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl border-none bg-transparent p-0 shadow-none sm:max-w-4xl focus:outline-none">
            <div className="sr-only">
              <DialogTitle>{scan.label}</DialogTitle>
              <DialogDescription>
                Viewing {scan.label} from {scan.source}
              </DialogDescription>
            </div>
            <div className="flex flex-col items-center justify-center min-h-[50vh] p-4">
              <div className="relative h-[70vh] sm:h-[80vh] w-full">
                <Image
                  src={resolveApiUrl(scan.url)}
                  alt={scan.label}
                  fill
                  unoptimized
                  className="rounded-lg object-contain drop-shadow-2xl"
                />
              </div>
              <div className="mt-4 flex w-full items-center justify-between px-4 text-white">
                <div>
                  <h4 className="text-sm font-bold uppercase tracking-widest">{scan.label}</h4>
                  <p className="text-xs opacity-60">Source: {scan.source}</p>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      ))}
    </div>
  );
}
