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
import { AccountVerification } from "@/components/account/account-verification";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";

/**
 * Email-verification confirmation page, reached from the link in a
 * verification mail.
 *
 * The page reads the token from the query string and never mutates anything on
 * render. That is deliberate: this URL is fetched by mail clients, link
 * previewers and security scanners within seconds of the message arriving, so
 * anything that changed state on load would fire before the recipient had read a
 * word. Confirmation happens only when the button is pressed.
 *
 * `Referrer-Policy: no-referrer` is set for this route in `next.config.ts`. That
 * header, not the absence of subresources, is what stops the single-use token in
 * the URL from reaching anything this page loads.
 *
 * @returns {JSX.Element} The page
 */
export default function AccountVerifyPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-2xl mx-auto p-6">
        <Suspense fallback={<div className="p-8 text-center text-muted-foreground">Loading...</div>}>
          <AccountVerification />
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}
