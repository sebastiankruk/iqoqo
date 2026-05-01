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
import { Footer } from "@/components/dashboard/footer";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Privacy Policy page component.
 *
 * @returns {JSX.Element} The page component
 */
export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto max-w-4xl py-10">
        <Card>
          <CardHeader>
            <CardTitle className="text-3xl">Privacy Policy</CardTitle>
            <p className="text-sm text-muted-foreground">Last updated: March 2026</p>
          </CardHeader>
          <CardContent className="space-y-4 text-sm leading-relaxed">
            <p>
              This Privacy Policy explains how we collect, use, and handle your data in compliance with the General Data
              Protection Regulation (GDPR).
            </p>

            <h2 className="text-xl font-semibold">1. Data We Collect</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Account Information:</strong> Email address, hashed password, and optional display name.
              </li>
              <li>
                <strong>Collection Data:</strong> Items you add to your library, statuses, and custom tags.
              </li>
            </ul>

            <h2 className="text-xl font-semibold">2. How We Use Your Data</h2>
            <p>
              Your data is primarily used to provide the core functionality of the iqoqo catalog. We do not sell your
              personal data to third parties.
            </p>

            <h2 className="text-xl font-semibold">3. Explicit Consents (Opt-In)</h2>
            <p>We rely on your explicit consent for the following features, which can be managed in your Profile:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Federation (ActivityPub):</strong> Sharing your public catalog with other instances.
              </li>
              <li>
                <strong>AI Telemetry:</strong> Sending anonymized metadata to external LLM providers (e.g., OpenAI,
                Google) to generate covers or recommendations.
              </li>
            </ul>

            <h2 className="text-xl font-semibold">4. Your GDPR Rights</h2>
            <p>You have the right to:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Access the personal data we hold about you.</li>
              <li>Request correction of inaccurate data.</li>
              <li>Request deletion of your data (Right to be Forgotten).</li>
              <li>Withdraw your consent at any time.</li>
            </ul>
            <p>
              To exercise these rights, please use the account management tools provided in the app or contact the
              instance administrator.
            </p>
          </CardContent>
        </Card>
      </main>
      <Footer />
    </div>
  );
}
