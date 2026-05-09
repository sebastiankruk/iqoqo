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

import { Suspense } from "react";
import { Navbar } from "./navbar";

/**
 * Skeleton placeholder for the Navbar during suspense loading.
 *
 * @returns {JSX.Element} The rendered skeleton.
 */
function NavbarSkeleton() {
  return <div className="sticky top-0 z-50 h-16 bg-primary" />;
}

/**
 * Navbar component wrapped in Suspense for client-side hydration.
 *
 * @returns {JSX.Element} The rendered navbar with suspense.
 */
export function NavbarWithSuspense() {
  return (
    <Suspense fallback={<NavbarSkeleton />}>
      <Navbar />
    </Suspense>
  );
}
