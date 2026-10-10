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

import { useQuery } from "@tanstack/react-query";

export interface AuthProviders {
  google: boolean;
}

export const DEFAULT_AUTH_PROVIDERS: AuthProviders = {
  google: false,
};

/**
 * Fetch available authentication providers from the backend.
 *
 * @returns {Promise<AuthProviders>} Resolved active providers
 */
export async function fetchAuthProviders(): Promise<AuthProviders> {
  try {
    const res = await fetch("/api/auth/providers");
    if (!res.ok) {
      return DEFAULT_AUTH_PROVIDERS;
    }
    const data = await res.json();
    return {
      google: Boolean(data?.google),
    };
  } catch {
    return DEFAULT_AUTH_PROVIDERS;
  }
}

/**
 * React hook to retrieve authentication provider availability.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult<AuthProviders>} Query result
 */
export function useAuthProviders() {
  return useQuery({
    queryKey: ["auth", "providers"],
    queryFn: fetchAuthProviders,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}
