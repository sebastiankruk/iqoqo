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

/** Sticky top navigation bar – "Modern Athenaeum" style. */
export function Footer() {
  const uiVersion = process.env.NEXT_PUBLIC_APP_VERSION || 'dev';

  return (
          <footer className="border-t border-border bg-card">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <p className="text-xs text-muted-foreground">
            <span className="font-serif font-bold text-foreground">iqoqo</span>
            {" "}&middot;{" "}The Library of Everything
            {" "}&middot;{" "}{uiVersion}
          </p>
          <p className="text-xs text-muted-foreground">Your library, your rules.</p>
        </div>
      </footer>
  );
}
