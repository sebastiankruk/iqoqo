import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function TermsOfServicePage() {
  return (
    <div className="container max-w-4xl py-10">
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
    </div>
  );
}
