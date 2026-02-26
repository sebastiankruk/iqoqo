import type { Metadata, Viewport } from "next";
import { Merriweather, Inter } from "next/font/google";
import { Providers } from "@/components/providers";
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
  title: "iqoqo – Modern Athenaeum",
  description:
    "Your personal library dashboard for books, games, music and collections",
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
    <html lang="en" className={`${merriweather.variable} ${inter.variable}`}>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
