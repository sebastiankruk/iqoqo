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

import { Navbar } from "@/components/dashboard/navbar";
import { Footer } from "@/components/dashboard/footer";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { CurrentContext } from "@/components/dashboard/current-context";
import { FreshArrivals } from "@/components/dashboard/fresh-arrivals";
import { Hero } from "@/components/landing/hero";
import { GlobalStats } from "@/components/landing/global-stats";
import { useProfile } from "@/lib/api/hooks";
import { Loader2 } from "lucide-react";

export default function DashboardPage() {
  const { data: user, isLoading } = useProfile();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      <main className="flex-1 container mx-auto px-4 py-8">
        {user ? (
          // Authenticated Dashboard
          <div className="space-y-8">
            <h1 className="text-3xl font-bold tracking-tight">Welcome back, {user.display_name ?? user.email}</h1>
            <StatsCards />
            <div className="grid gap-8 md:grid-cols-2">
              <CurrentContext />
              <FreshArrivals />
            </div>
          </div>
        ) : (
          // Unauthenticated Landing Page
          <div className="space-y-8">
            <Hero />
            <GlobalStats />
            <section>
              <FreshArrivals publicMode={true} />
            </section>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
