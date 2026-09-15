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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

/**
 * Global client-side providers: React Query + Sonner toasts.
 * Wraps the entire application via `app/layout.tsx`.
 *
 * @param root0 - The props object
 * @param root0.children - The child components
 * @returns {JSX.Element} The component
 */
export function Providers({ children }: { children: React.ReactNode }) {
  // Create a stable QueryClient per render tree (avoids shared state across
  // server renders when running in SSR mode).
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10_000,
            retry: 1,
          },
        },
      })
  );

  // Responsive toast placement: top-center on mobile (< 640px) to prevent bottom nav bar collision
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 640);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        richColors
        position={isMobile ? "top-center" : "bottom-right"}
        mobileOffset={{
          top: "calc(env(safe-area-inset-top, 0px) + 12px)",
          bottom: "5.5rem",
        }}
      />
    </QueryClientProvider>
  );
}
