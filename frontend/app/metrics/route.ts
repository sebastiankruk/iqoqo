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

import { NextResponse } from "next/server";
import client from "prom-client";

export const dynamic = "force-dynamic";

// Ensure default metrics are collected once across hot reloads in development
if (typeof globalThis !== "undefined") {
  const globalContext = globalThis as typeof globalThis & {
    _prometheusInitialized?: boolean;
  };
  if (!globalContext._prometheusInitialized) {
    client.collectDefaultMetrics();
    globalContext._prometheusInitialized = true;
  }
}

/**
 * Handle GET requests to expose Prometheus metrics.
 *
 * @returns {Promise<NextResponse>} The Next.js response containing raw metrics text
 */
export async function GET() {
  const metrics = await client.register.metrics();
  return new NextResponse(metrics, {
    headers: {
      "Content-Type": client.register.contentType,
    },
  });
}
