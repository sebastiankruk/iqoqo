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

import { useParams } from "next/navigation";
import Image from "next/image";
import { BookOpen, Loader2 } from "lucide-react";
import { Navbar } from "@/components/dashboard/navbar";
import { Footer } from "@/components/dashboard/footer";
import { useManifestation, useProfile, useAddItem } from "@/lib/api/hooks";
import { getCoverUrl } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ManifestationActions } from "@/components/manifestation/manifestation-actions";
import { CameraCapture } from "@/components/scanner/camera-capture";
import { ImagePlus } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

/**
 * Page displaying a single manifestation with metadata and add-to-collection action.
 *
 * @returns {JSX.Element}
 */
export default function ManifestationPage() {
  const params = useParams();
  const manifestationId = Number(params?.id);

  const { data: userProfile } = useProfile();
  const { data: manifestation, isLoading, isError } = useManifestation(manifestationId);
  const { mutate: addItem, isPending: isAdding } = useAddItem();
  const router = useRouter();

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

  const coverUrl = getCoverUrl(manifestation.cover_url || undefined) || (manifestation.meta?.["cover_url"] as string | undefined);

  /**
   * Add the current manifestation to the user's collection when an ISBN is available.
   * @returns {void}
   */
  const handleAddToCollection = () => {
    if (manifestation.isbn13) {
      addItem({ isbn: manifestation.isbn13 });
    }
  };

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
            {!coverUrl && (
              <div className="mt-4">
                <CameraCapture
                  manifestationId={manifestation.id}
                  onUploadComplete={() => {
                    toast.success("Cover contributed! Processing started.");
                    router.refresh();
                  }}
                  label="Contribute Cover"
                  icon={<ImagePlus className="mr-2 h-4 w-4" />}
                  className="[&>button]:w-full [&>button]:rounded-xl [&>button]:py-6"
                />
              </div>
            )}
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
                  <dd className="font-medium">{(manifestation.meta?.Publisher as string) || "Unknown"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Year</dt>
                  <dd className="font-medium">{(manifestation.meta?.Year as string) || "Unknown"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Language</dt>
                  <dd className="font-medium">{(manifestation.meta?.Language as string) || "Unknown"}</dd>
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
                    <Button onClick={handleAddToCollection} disabled={isAdding || !manifestation.isbn13} size="sm">
                      {isAdding ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <BookOpen className="mr-2 h-4 w-4" />
                      )}
                      Add to My Collection
                    </Button>
                  )}
                  {!manifestation.isbn13 && !manifestation.user_owns && (
                    <p className="mt-2 text-xs text-destructive">Cannot be added automatically (No ISBN available).</p>
                  )}
                </div>

                {/* Admin Actions extracted to standalone component */}
                <ManifestationActions manifestation={manifestation} />
              </div>
            )}
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
