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

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import Image from "next/image";

interface DiscoverItem {
  id: number;
  title?: string;
  cover_path?: string;
  author?: string;
  isbn13?: string;
  publisher?: string;
  cover_url?: string; // add this field to hold the full URL for the cover image
  // add other fields you expect from the API like isbn13, publisher, etc.
}

export default function DiscoverPage() {
  const [manifestations, setManifestations] = useState<DiscoverItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("/api/discover");
        const data = await res.json();
        setManifestations(data.manifestations);
        setLoading(false);
      } catch {
        toast.error("Failed to load global library");
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const addToCollection = async (manifestationId: number) => {
    // You'd typically need an endpoint like POST /api/items to add by manifestation ID
    console.log("Adding manifestation:", manifestationId); // Now it's used!
    toast.success("Feature coming soon: Add directly from discover!");
  };

  if (loading) return <div className="p-8 text-center">Loading discover feed...</div>;

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Discover</h1>
        <p className="text-muted-foreground">Explore all manifestations cataloged on this local iqoqo instance.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
        {manifestations.map((m) => (
          <Card key={m.id} className="overflow-hidden flex flex-col">
            <div className="aspect-[2/3] bg-muted relative">
              {m.cover_url ? (
                <Image src={m.cover_url} alt={m.title || "Book cover"} className="object-cover w-full h-full" />
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">No Cover</div>
              )}
            </div>
            <CardContent className="p-4 flex-1 flex flex-col justify-between">
              <div>
                <h3 className="font-semibold line-clamp-2 text-sm">{m.title}</h3>
                <p className="text-xs text-muted-foreground mt-1">{m.author}</p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                className="w-full mt-4"
                onClick={() => addToCollection(m.id)}
              >
                I own this
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
