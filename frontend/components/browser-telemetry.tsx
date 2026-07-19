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
// Layer 5: Client-Side Browser Telemetry (Web Vitals)
//
// Initializes the OpenTelemetry Web SDK in the browser runtime.
// Instruments DOM document load events and user interactions (clicks, submits)
// and ships traces directly to the OTel Collector via OTLP HTTP.
//
// The Collector must have CORS enabled for localhost:3000 — this is configured
// in deploy/otel-collector-local.yaml under `receivers.otlp.protocols.http.cors`.
//
// Traces are stitched to server-side spans via W3C Trace Context headers that
// Next.js propagates through its fetch() calls.
"use client";

import { useEffect } from "react";

/**
 * BrowserTelemetry — client-side OpenTelemetry bootstrap.
 *
 * Renders nothing. Must be placed inside <body> in the root layout so it
 * initialises before any user interaction occurs.
 *
 * Guards against double-initialisation in React Strict Mode (double-invoke).
 *
 * @returns {null} Always returns null — no DOM output.
 */
export function BrowserTelemetry(): null {
  useEffect(() => {
    // Guard: prevent double-initialisation from React Strict Mode or HMR.
    if (typeof window === "undefined") return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if ((window as any).__OTEL_BROWSER_INITIALIZED__) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).__OTEL_BROWSER_INITIALIZED__ = true;

    // Dynamic import keeps all OTel browser SDK code out of the initial bundle.
    // It is only loaded after the page hydrates, so it never blocks LCP.
    import("@opentelemetry/sdk-trace-web")
      .then(({ WebTracerProvider }) =>
        Promise.all([
          import("@opentelemetry/sdk-trace-base"),
          import("@opentelemetry/exporter-trace-otlp-http"),
          import("@opentelemetry/instrumentation-document-load"),
          import("@opentelemetry/instrumentation-user-interaction"),
          import("@opentelemetry/instrumentation"),
          import("@opentelemetry/resources"),
          import("@opentelemetry/semantic-conventions"),
          import("@opentelemetry/context-zone"),
        ]).then(
          ([
            { BatchSpanProcessor },
            { OTLPTraceExporter },
            { DocumentLoadInstrumentation },
            { UserInteractionInstrumentation },
            { registerInstrumentations },
            { resourceFromAttributes },
            { SEMRESATTRS_SERVICE_NAME },
            { ZoneContextManager },
          ]) => {
            // Target the host-exposed OTel Collector port.
            // CORS is whitelisted for localhost:3000 in otel-collector-local.yaml.
            const collectorUrl = process.env.NEXT_PUBLIC_OTEL_COLLECTOR_URL ?? window.location.origin + "/v1/traces";

            const provider = new WebTracerProvider({
              resource: resourceFromAttributes({
                [SEMRESATTRS_SERVICE_NAME]: "iqoqo-browser-client",
              }),
              spanProcessors: [new BatchSpanProcessor(new OTLPTraceExporter({ url: collectorUrl }))],
            });

            provider.register({
              contextManager: new ZoneContextManager(),
            });

            // Auto-instrument document load (Core Web Vitals) and user interactions.
            registerInstrumentations({
              instrumentations: [new DocumentLoadInstrumentation(), new UserInteractionInstrumentation()],
            });

            console.log("🏗️ iqoqo Browser OpenTelemetry initialised →", collectorUrl);
          }
        )
      )
      .catch(err => {
        // Non-fatal: telemetry failure must never break the application.
        console.warn("⚠️ iqoqo Browser OTel init failed (non-fatal):", err);
      });
  }, []);

  return null;
}
