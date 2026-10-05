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

import { Suspense } from "react";
import { AccountDeletion } from "@/components/account/account-deletion";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";

/**
 * Account-deletion confirmation page, reached from the link in a deletion mail.
 *
 * Renders nothing destructive on load. The token in the URL is read and reported
 * as usable or not; the account is removed only when the button is pressed, which
 * requires an authenticated session for that account and CSRF proof.
 *
 * This is the page a security appliance fetches within seconds of the mail
 * arriving, so the distinction between "render" and "act" is the whole design:
 * a scanner and a human get an identical GET, and only the human gets a POST.
 *
 * @returns {JSX.Element} The page
 */
export default function AccountDeletePage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-2xl mx-auto p-6">
        <Suspense fallback={<div className="p-8 text-center text-muted-foreground">Loading...</div>}>
          <AccountDeletion />
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}
