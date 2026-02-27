import type { Metadata, Viewport } from "next";
import { Merriweather, Inter } from "next/font/google";
import { Providers } from "@/components/providers";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

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
  description:
    "Your personal library dashboard for books, games, music and collections",
  icons: {
    icon: "/icon.svg",
    apple: "/apple-icon",
  },
};

export const viewport: Viewport = {
  themeColor: "#2C3E50",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${merriweather.variable} ${inter.variable}`} suppressHydrationWarning>
      <head />
      <body className="font-sans antialiased">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <Providers>{children}</Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
