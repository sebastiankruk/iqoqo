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
import type { Metadata, Viewport } from "next";
import { Merriweather, Inter, Geist } from "next/font/google";
import { Providers } from "@/components/providers";
import { ThemeProvider } from "@/components/theme-provider";
import { CookieConsent } from "@/components/cookie-consent";
import { BrowserTelemetry } from "@/components/browser-telemetry";
import { BrowserOpenObserveRum } from "@/components/browser-openobserve-rum";
import { JsonLdConsoleFilter } from "@/components/json-ld-console-filter";
import "./globals.css";
import { cn } from "@/lib/utils";
import { getMessages, getLocale } from "next-intl/server";
import { NextIntlClientProvider } from "next-intl";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });

const merriweather = Merriweather({
  subsets: ["latin"],
  weight: ["300", "400", "700", "900"],
  variable: "--font-merriweather",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const frontendUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || "https://preview.iqoqo.cc";

/**
 * Resolve the OpenObserve RUM configuration to hand to the browser.
 *
 * Read here, on the server, at request time — not from `NEXT_PUBLIC_*`, which
 * Next.js inlines into the client bundle at build time. `--prebuilt`
 * deployments pull the frontend image from a registry where it was built on
 * CI, so a build-time value would either be impossible to set per instance or
 * would bake one instance's token into a shared image.
 *
 * Returns null when no token is configured, which disables the SDK cleanly.
 *
 * A RUM client token is public by construction: it is a write-only bearer
 * credential that necessarily reaches the browser, so serving it here changes
 * nothing about what an attacker can do with it. What *is* enforced is that it
 * only ever travels alongside a validated ingest target.
 *
 * @returns The RUM configuration to hand to the client component, or null to leave RUM disabled.
 */
function resolveRumConfig(): {
  clientToken: string;
  site?: string;
  insecureHTTP?: boolean;
} | null {
  const clientToken = (process.env.OPENOBSERVE_RUM_CLIENT_TOKEN ?? "").trim();
  if (!clientToken) return null;

  // Set by the provisioning step (scripts/provision_rum_token.py) only after
  // validating the target. Unset means "use the page host", which is the
  // component's own safe default.
  const site = (process.env.OPENOBSERVE_RUM_SITE ?? "").trim();

  // Left undefined when not configured, so the component derives the transport
  // from the page it is running on: correct for a bare-HTTP dev instance and
  // secure for an HTTPS deployment, with no per-mode override to get wrong.
  const configured = (process.env.OPENOBSERVE_RUM_INSECURE_HTTP ?? "").trim();
  const insecureHTTP = configured === "" ? undefined : configured === "true";

  return { clientToken, site: site || undefined, insecureHTTP };
}

export const metadata: Metadata = {
  metadataBase: new URL(frontendUrl),
  title: "iqoqo – The Library of Everything",
  description: "Your personal library dashboard for books, games, music and collections",
  icons: {
    icon: "/icon.svg",
    apple: "/apple-icon",
  },
  alternates: {
    types: {
      "application/rss+xml": [{ url: "/api/public/feed.xml", title: "iqoqo Fresh Arrivals Feed" }],
    },
  },
};

export const viewport: Viewport = {
  themeColor: "#2C3E50",
};

/**
 * Root layout component.
 *
 * @param root0 - The props object
 * @param root0.children - The child components
 * @returns {JSX.Element} The root layout
 */
export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();
  // Resolved per request on the server; see resolveRumConfig for why this is
  // not a NEXT_PUBLIC_* build-time value.
  const rumConfig = resolveRumConfig();

  return (
    <html
      lang={locale}
      className={cn(merriweather.variable, inter.variable, "font-sans", geist.variable)}
      suppressHydrationWarning
    >
      <head />
      <body className="font-sans antialiased">
        {/* Layer 5: Browser Web Vitals — client-side OTel initialisation (loads asynchronously, never blocks render) */}
        <BrowserTelemetry />
        <JsonLdConsoleFilter />
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <NextIntlClientProvider locale={locale} messages={messages}>
            <Providers>
              {rumConfig ? <BrowserOpenObserveRum {...rumConfig} /> : <BrowserOpenObserveRum />}
              {children}
              <CookieConsent />
            </Providers>
          </NextIntlClientProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
