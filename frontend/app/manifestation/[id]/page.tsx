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
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { BookOpen, Loader2, RefreshCw, ImageIcon, Trash2 } from "lucide-react";
import { Navbar } from "@/components/dashboard/navbar";
import { Footer } from "@/components/dashboard/footer";
import { useManifestation, useProfile, useAddItem } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";

export default function ManifestationPage() {
  const params = useParams();
  const router = useRouter();
  const manifestationId = Number(params?.id);

  const [isActionLoading, setIsActionLoading] = useState(false);
  const { data: userProfile } = useProfile();
  const { data: manifestation, isLoading, isError } = useManifestation(manifestationId);
  const { mutate: addItem, isPending: isAdding } = useAddItem();

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
        <Footer />
      </div>
    );
  }

  if (isError || !manifestation) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-muted-foreground">Manifestation not found.</p>
        </div>
        <Footer />
      </div>
    );
  }

  const coverUrl = manifestation.cover_path
    ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api"}${manifestation.cover_path}`
    : manifestation.meta?.["cover_url"] as string | undefined;

  const handleAddToCollection = () => {
    if (manifestation.isbn13) {
      addItem({ isbn: manifestation.isbn13 });
    }
  };

  const handleAdminAction = async (endpoint: string, method: string = "POST") => {
    setIsActionLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api"}/manifestations/${manifestationId}${endpoint}`;

      const res = await fetch(url, { method, headers, credentials: "omit" });

      if (res.ok) {
        if (method === "DELETE") {
          router.push("/collection");
        } else {
          window.location.reload();
        }
      } else {
        alert("Action failed. Ensure you have the right permissions.");
      }
    } catch (e) {
      console.error(e);
      alert("An error occurred performing this action.");
    } finally {
      setIsActionLoading(false);
    }
  };

  const canRefetch = userProfile?.permissions?.includes("refetch:metadata");
  const canRegenerate = userProfile?.permissions?.includes("regenerate:cover");
  const canDelete = userProfile?.permissions?.includes("delete:manifestation");

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <div className="flex-1 mx-auto w-full max-w-5xl px-6 py-12">
        <div className="flex flex-col md:flex-row gap-8">
          {/* Cover Art */}
          <div className="w-full md:w-1/3 max-w-sm mx-auto">
            <div className="relative aspect-[2/3] w-full overflow-hidden rounded-xl border border-border bg-secondary shadow-lg">
              {coverUrl ? (
                <Image
                  src={coverUrl}
                  alt={`Cover of ${manifestation.title}`}
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  unoptimized
                  className="object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <BookOpen className="h-24 w-24 text-muted-foreground/30" />
                </div>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="flex-1 space-y-6">
            <div>
              <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
                {manifestation.title || "Untitled Work"}
              </h1>
              <p className="mt-2 text-xl text-muted-foreground">
                {manifestation.authors?.join(", ") || "Unknown Author"}
              </p>
            </div>

            <div className="space-y-3 pt-6 border-t border-border">
              <h2 className="text-lg font-semibold">Publication Details</h2>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3 text-sm">
                <div>
                  <dt className="text-muted-foreground">ISBN-13</dt>
                  <dd className="font-medium">{manifestation.isbn13 || "N/A"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Publisher</dt>
                  <dd className="font-medium">{manifestation.meta?.Publisher as string || "Unknown"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Year</dt>
                  <dd className="font-medium">{manifestation.meta?.Year as string || "Unknown"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Language</dt>
                  <dd className="font-medium">{manifestation.meta?.Language as string || "Unknown"}</dd>
                </div>
              </dl>
            </div>

            {userProfile && (
              <div className="pt-6 space-y-4">
                <div>
                  {manifestation.user_owns ? (
                    <div className="inline-flex items-center rounded-lg bg-primary/10 px-4 py-2 font-medium text-primary">
                      <span className="mr-2 block h-2 w-2 rounded-full bg-primary" />
                      Already in your collection
                    </div>
                  ) : (
                    <Button
                      onClick={handleAddToCollection}
                      disabled={isAdding || !manifestation.isbn13}
                      size="sm"
                    >
                      {isAdding ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BookOpen className="mr-2 h-4 w-4" />}
                      Add to My Collection
                    </Button>
                  )}
                  {!manifestation.isbn13 && !manifestation.user_owns && (
                    <p className="mt-2 text-xs text-destructive">Cannot be added automatically (No ISBN available).</p>
                  )}
                </div>

                {/* Admin Actions */}
                {(canRefetch || canRegenerate || canDelete) && (
                  <div className="flex flex-wrap gap-2 pt-4 border-t border-border">
                    {canRefetch && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isActionLoading || !manifestation.isbn13}
                        onClick={() => handleAdminAction("/refetch-metadata")}
                      >
                        <RefreshCw className={`w-4 h-4 mr-2 ${isActionLoading ? "animate-spin" : ""}`} />
                        Refetch
                      </Button>
                    )}
                    {canRegenerate && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isActionLoading}
                        onClick={() => handleAdminAction("/regenerate-cover")}
                      >
                        <ImageIcon className="w-4 h-4 mr-2" />
                        Regen Cover
                      </Button>
                    )}
                    {canDelete && (
                      <Button
                        variant="destructive"
                        size="sm"
                        disabled={isActionLoading}
                        onClick={() => {
                          if (confirm("Are you sure you want to delete this manifestation?")) {
                            handleAdminAction("", "DELETE");
                          }
                        }}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Delete
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
