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
import { Navbar } from "@/components/dashboard/navbar";
import { Footer } from "@/components/dashboard/footer";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { CurrentContext } from "@/components/dashboard/current-context";
import { FreshArrivals } from "@/components/dashboard/fresh-arrivals";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8">
          <h1 className="font-serif text-2xl font-bold text-foreground">
            Welcome to your library
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your collection is growing nicely. Here is what is happening.
          </p>
        </div>

        <div className="flex flex-col gap-10">
          <StatsCards />
          <CurrentContext />
          <FreshArrivals />
        </div>
      </main>

      <Footer />
    </div>
  );
}
