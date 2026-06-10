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

import Link from "next/link";
import { Button } from "@/components/ui/button";

/**
 * Custom 404 page for the Next.js App Router.
 * Returns a clean 404 response when a resource or page is not found.
 * @returns {JSX.Element}
 */
export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <h1 className="text-4xl font-serif font-bold mb-4">404 - Page Not Found</h1>
      <p className="text-muted-foreground mb-8 max-w-md">
        The page you are looking for does not exist, has been removed, or has been made private.
      </p>
      <Button asChild>
        <Link href="/">Go back home</Link>
      </Button>
    </div>
  );
}
