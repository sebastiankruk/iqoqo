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

import Link from "next/link";
import { Search, ScanLine, Library, Loader2, Settings, User, LogOut, AlertTriangle } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";
import { Avatar } from "@/components/ui/avatar";
import { ModeToggle } from "@/components/mode-toggle";
import { useQueryClient } from "@tanstack/react-query";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useProfile, useAppConfig } from "@/lib/api/hooks";

/**
 * Sticky top navigation bar – "Modern Athenaeum" style.
 *
 * @returns {JSX.Element} The component
 */
export function Navbar() {
  const { data: profile, isLoading } = useProfile();
  const { data: config } = useAppConfig();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [searchQuery, setSearchQuery] = useState(searchParams?.get("q") || searchParams?.get("search") || "");
  const queryClient = useQueryClient();

  const isMaintenanceMode = config?.maintenance_mode === true;

  useEffect(() => {
    setSearchQuery(searchParams?.get("q") || searchParams?.get("search") || "");
  }, [searchParams]);

  /**
   * Handles the user logout process.
   */
  const handleLogout = async () => {
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error(`Logout failed with status ${response.status} ${response.statusText}`);
      }
    } catch (err) {
      console.error("Failed to logout:", err);
    } finally {
      queryClient.clear();
      router.push("/login");
    }
  };

  /**
   * Handles the search form submission.
   *
   * @param {React.FormEvent} e - The form event.
   */
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams(searchParams?.toString() || "");
    if (searchQuery.trim()) {
      params.set("q", searchQuery.trim());
      params.delete("search");
    } else {
      params.delete("q");
      params.delete("search");
    }
    params.set("page", "1");
    router.push(`/collection?${params.toString()}`);
  };

  return (
    <nav className="sticky top-0 z-50 bg-primary text-primary-foreground dark:bg-[#040608] dark:text-foreground dark:border-b">
      {isMaintenanceMode && (
        <div className="bg-amber-500 py-2 px-4 text-center text-xs font-bold uppercase tracking-wider text-black flex items-center justify-center gap-2 border-b border-amber-600/20">
          <AlertTriangle className="h-3.5 w-3.5" />
          Maintenance Mode Active – Some features may be limited
        </div>
      )}
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-6">
        {/* Brand */}
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center">
            <svg width="40" height="40" viewBox="0 0 220 220" fill="none" className="text-accent">
              <path
                d="M93.277 63.006c4.45 5.767 10.29 10.276 15.025 15.792 3.44 1.225 6.364-9.314 12.814-7.214 7.541 1.269 14.798 5.992 22.713 3.521 14.12-2.612 22.913-18.61 18.618-32.087-3.194-13.315-18.547-20.861-31.248-16.623-11.354 2.896-18.128 14.592-18.054 25.834-1.468 8.942-11.797 13.14-19.868 10.777zm45.102-22.73c10.704-.885 13.856 15.998 3.925 19.57-9.23 4.123-18-8.436-11.403-15.963 1.73-2.328 4.6-3.647 7.478-3.607zM33.397 49.461C22.93 50.4 14.511 62.25 19.24 72.218c5.641 10.926 19.541 16.39 21.698 29.38 2.527 10.343-3.872 20.002-11.441 26.43-6.166 5.612-13.748 13.016-10.947 22.266 2.18 10.308 15.145 16.06 24.032 10.148 8.631-6.34 15.393-14.886 23.155-22.234 6.924-7.413 14.48-14.287 20.996-22.04 5.271-8.098 2.558-19.081-4.567-25.107-13.087-12.463-24.812-26.326-38.272-38.385-2.951-2.302-6.706-3.806-10.496-3.215zm35.89 5.374c-5.778.299-13.917 6.625-5.661 10.881 8.593 9.055 17.852 17.509 26.114 26.846 7.38 9.675 5.276 24.323-4.116 31.934-8.844 8.682-17.356 17.704-26.085 26.496.847 7.065 12.387 9.312 18.372 6.271 8.688-4.794 14.339-13.432 21.55-20.047 7.041-7.998 16.127-14.422 21.406-23.807 4.371-8.841-1.54-18.163-8.267-23.793-10.262-10.327-20.208-21.003-30.752-31.023-3.481-2.843-8.046-4.517-12.561-3.758zm54.698 40.414c3.777 6.944 4.3 15.94-.124 22.721-.59 3.33 7.362-3.902 10.655-4.058 8.566-4.258 13.918 4.024 19.292 8.918 10.489 7.904 27.436-.194 28.17-13.22 1.377-10.898-8.405-21.746-19.601-20.325-10.174-.764-13.182 11.75-22.243 12.745-6.16.168-10.698-4.759-16.15-6.781zm39.152 3.894c10.456-1.775 11.747 16.646 1.107 16.29-10.782.948-10.906-15.081-1.107-16.29zm-53.547 34.49c-5.328 5.424-10.705 10.802-15.737 16.505 9.608-3.999 22.518.318 23.985 11.66 2.624 11.27 17.49 16.854 26.74 9.697 10.91-7.28 8.375-26.234-4.122-30.334-8.378-4.24-17.279 4.926-25.226-.264-2.62-1.783-3.67-4.914-5.64-7.264zm23.799 15.601c7.33-1.65 12.438 8.037 7.651 13.514-4.526 6.245-15.954 1.962-14.706-5.878.282-3.755 3.227-7.218 7.055-7.636z"
                fill="currentColor"
              />
            </svg>
          </div>
          <span className="font-serif text-xl font-bold tracking-tight">iqoqo</span>
        </Link>

        {/* Search */}
        <form onSubmit={handleSearch} className="relative mx-auto w-full max-w-md">
          <div className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center">
            <Search className="h-4 w-4 text-primary-foreground/50 dark:text-white/50" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search your collection..."
            className="h-9 w-full rounded-full border border-primary-foreground/15 bg-primary-foreground/10 pl-10 pr-4 text-sm text-primary-foreground placeholder-primary-foreground/40 outline-none transition-colors focus:border-accent focus:bg-primary-foreground/15 dark:border-white/10 dark:bg-white/10 dark:text-white dark:placeholder-white/60"
          />
        </form>

        {/* Right section */}
        <div className="flex shrink-0 items-center gap-4">
          <Link
            href="/collection"
            className="hidden items-center gap-1.5 rounded-full border border-primary-foreground/20 px-3.5 py-1.5 text-xs font-medium text-primary-foreground/80 transition-colors hover:border-primary-foreground/40 hover:text-primary-foreground sm:flex dark:border-white/20 dark:text-white/90 dark:hover:text-white dark:hover:bg-transparent"
          >
            <Library className="h-3.5 w-3.5" />
            Collection
          </Link>
          {profile ? (
            <div className="flex items-center gap-2">
              <Link
                href="/scan"
                className="flex h-9 items-center gap-1.5 rounded-full bg-accent px-3.5 text-xs font-semibold text-accent-foreground transition-opacity hover:opacity-90"
              >
                <ScanLine className="h-4 w-4" />
                <span className="hidden sm:inline">Scan</span>
              </Link>
            </div>
          ) : (
            <span />
          )}

          <ModeToggle />

          {/* Auth State Rendering */}
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          ) : profile ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-foreground transition-opacity hover:opacity-90 overflow-hidden outline-none"
                  aria-label="User menu"
                >
                  <Avatar
                    src={profile.avatar_url}
                    alt={`${profile.display_name || profile.email}'s profile picture`}
                    size={36}
                    className="rounded-full"
                    fallback={(profile.display_name?.charAt(0) || profile.email?.charAt(0) || "?").toUpperCase()}
                  />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                className="w-60 p-2 dark:bg-[#0a0c10] dark:border-white/10 shadow-xl rounded-xl"
              >
                <div className="px-2 py-2.5">
                  <p className="text-sm font-medium leading-none">{profile.display_name || "User"}</p>
                  <p className="text-xs text-muted-foreground mt-1.5 truncate">{profile.email}</p>
                </div>
                <DropdownMenuSeparator className="dark:bg-white/10" />
                <DropdownMenuGroup>
                  {profile.public_username && (
                    <DropdownMenuItem asChild className="cursor-pointer rounded-md py-2 px-3 text-sm">
                      <Link href={`/u/${profile.public_username}`}>
                        <User className="mr-2 h-4 w-4" /> Public Profile
                      </Link>
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem asChild className="cursor-pointer rounded-md py-2 px-3 text-sm">
                    <Link href="/admin/settings">
                      <Settings className="mr-2 h-4 w-4" /> Profile Settings
                    </Link>
                  </DropdownMenuItem>
                  {profile.roles?.includes("admin") && (
                    <DropdownMenuItem asChild className="cursor-pointer rounded-md py-2 px-3 text-sm">
                      <Link href="/admin/settings?tab=instance">
                        <Settings className="mr-2 h-4 w-4" /> Admin Configuration
                      </Link>
                    </DropdownMenuItem>
                  )}
                </DropdownMenuGroup>
                <DropdownMenuSeparator className="dark:bg-white/10" />
                <DropdownMenuItem
                  asChild
                  className="cursor-pointer rounded-md py-2 px-3 text-sm text-red-500 focus:text-red-500 focus:bg-red-500/10"
                >
                  <button onClick={handleLogout} className="w-full flex items-center">
                    <LogOut className="mr-2 h-4 w-4" /> Log out
                  </button>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <div className="flex items-center gap-2">
              <Link href="/login" className="text-sm font-medium hover:underline">
                Sign In
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
