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

export default function ManifestationPage({ params }: { params: { id: string } }) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <div className="flex-1 mx-auto w-full max-w-7xl px-6 py-12 text-center">
        <h1 className="font-serif text-2xl font-bold">Global Catalog Manifestation</h1>
        <p className="mt-4 text-muted-foreground">Manifestation ID: {params.id}</p>
        <p className="mt-6 text-sm">Full global catalog item details view coming soon.</p>
      </div>
      <Footer />
    </div>
  );
}
