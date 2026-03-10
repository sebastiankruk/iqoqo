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
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button"; // Assuming you are using shadcn/ui

export function CookieConsent() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Only check localStorage after client hydration to avoid hydration mismatch.
    // This is a necessary pattern for client-side persistent state in Next.js.
    const consent = localStorage.getItem("iqoqo-cookie-consent");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsVisible(!consent);
  }, []);

  const acceptCookies = () => {
    localStorage.setItem("iqoqo-cookie-consent", "true");
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm p-4 bg-background border border-border rounded-lg shadow-lg flex flex-col gap-3 animate-in fade-in slide-in-from-bottom-5">
      <div className="text-sm italic text-muted-foreground font-serif">
        <p>Small crumbs of data,</p>
        <p>Guide your journey through the books,</p>
        <p>Accept and read on.</p>
      </div>
      <div className="flex justify-between items-center mt-1">
        <a href="/privacy" className="text-xs text-muted-foreground underline hover:text-primary transition-colors">
          Privacy Policy
        </a>
        <Button size="sm" onClick={acceptCookies} className="text-xs h-8" variant="ghost">
          Got it
        </Button>
      </div>
    </div>
  );
}
