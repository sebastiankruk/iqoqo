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

import * as React from "react";
import { useEffect } from "react";
import { ThemeProvider as NextThemesProvider, type ThemeProviderProps } from "next-themes";

/**
 * Theme provider component.
 *
 * @param props - The provider props
 * @param props.children - The children to render within the provider.
 * @returns {JSX.Element} The component
 */
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  useEffect(() => {
    // Suppress React's dev-only warning about rendering a <script> tag, which
    // we do intentionally for JSON-LD structured data (see
    // frontend/app/manifestation/[id]/page.tsx). Scoped to a mount effect
    // (rather than module-load top-level code) with a cleanup that restores
    // the original console.error, so it doesn't accumulate extra wrapper
    // layers across Fast Refresh/HMR or React Strict Mode's dev
    // mount->unmount->remount cycle. Development-only: production builds
    // don't emit this warning in the first place.
    if (typeof window === "undefined" || process.env.NODE_ENV === "production") {
      return undefined;
    }

    const originalError = console.error;
    console.error = (...args: unknown[]) => {
      if (
        args[0] &&
        typeof args[0] === "string" &&
        args[0].includes("Encountered a script tag while rendering React component")
      ) {
        return;
      }
      originalError.apply(console, args);
    };

    return () => {
      console.error = originalError;
    };
  }, []);

  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
