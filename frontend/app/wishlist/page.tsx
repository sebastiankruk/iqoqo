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

"use client";

import { Loader2 } from "lucide-react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { WishlistCard } from "@/components/collection/wishlist-card";
import { useWishlist } from "@/lib/api/wishlist";

export default function WishlistPage() {
  const { data, isLoading, isError } = useWishlist({ limit: 100 });
  const items = data?.data ?? [];

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h1 className="font-serif text-2xl font-bold text-foreground">Wishlist</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {data?.total ?? 0} {data?.total === 1 ? "item" : "items"}
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20" aria-label="Loading wishlist">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : isError ? (
          <div className="rounded-xl border border-destructive/30 bg-card p-8 text-center text-sm text-destructive">
            Unable to load your wishlist.
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-card p-10 text-center">
            <h2 className="font-serif text-lg font-bold">Your wishlist is empty</h2>
            <p className="mt-2 text-sm text-muted-foreground">Add works from the catalog to see them here.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {items.map(item => <WishlistCard key={item.id} item={item} />)}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
