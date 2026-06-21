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

export const metadata: Metadata = {
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
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <NextIntlClientProvider locale={locale} messages={messages}>
            <Providers>
              {children}
              <CookieConsent />
            </Providers>
          </NextIntlClientProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
