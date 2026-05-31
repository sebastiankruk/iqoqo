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
// frontend/app/api/auth-exchange/route.capacitor.ts
//
// Capacitor static-export STUB — substituted for route.ts during `make mobile-build`.
// The native auth flow uses app/auth-exchange/page.tsx + setAuthToken() and never
// calls this endpoint; this stub satisfies Next.js `output: "export"` requirements.
import { NextResponse } from "next/server";

export const dynamic = "force-static";

/** No-op handler — never called in Capacitor builds. */
export async function GET() {
  return new NextResponse(null, { status: 204 });
}
