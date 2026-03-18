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
import { Navbar } from "@/components/dashboard/navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Terms of Service page component.
 *
 * @returns {JSX.Element} The page component
 */
export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto max-w-4xl py-10">
      <Card>
        <CardHeader>
          <CardTitle className="text-3xl">Terms of Service</CardTitle>
          <p className="text-sm text-muted-foreground">Last updated: March 2026</p>
        </CardHeader>
        <CardContent className="space-y-4 text-sm leading-relaxed">
          <h2 className="text-xl font-semibold">1. Acceptance of Terms</h2>
          <p>By registering an account on this iqoqo instance, you agree to be bound by these Terms of Service. If you do not agree, please do not use the service.</p>

          <h2 className="text-xl font-semibold">2. Description of Service</h2>
          <p>iqoqo is a distributed library catalog system. Users can create, manage, and optionally share personal collections of physical and digital media.</p>

          <h2 className="text-xl font-semibold">3. User Conduct and Content</h2>
          <p>You retain ownership of the metadata you generate. However, you agree not to use the service for illegal purposes or to upload malicious content. The instance administrator reserves the right to suspend accounts that violate these terms.</p>

          <h2 className="text-xl font-semibold">4. Federation</h2>
          <p>If you opt-in to federation, your public collections may be shared with other instances across the network via ActivityPub. You can revoke this access at any time in your profile settings, though we cannot guarantee the immediate deletion of cached data on remote instances.</p>

          <h2 className="text-xl font-semibold">5. Termination</h2>
          <p>You may delete your account at any time. We reserve the right to suspend or terminate access to our instance for users who violate these terms.</p>
        </CardContent>
      </Card>
      </main>
      <Footer />
    </div>
  );
}
