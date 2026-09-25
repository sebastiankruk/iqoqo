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

"use client";

import { useEffect } from "react";

/**
 * BrowserOpenObserveRum — client-side bootstrap for OpenObserve RUM and Logs SDKs.
 *
 * Renders nothing. Must be placed inside the React Query <Providers> context
 * in the root layout so RUM and Logs can initialize in the browser.
 *
 * @returns {null} Always returns null — no DOM output.
 */
export function BrowserOpenObserveRum(): null {
  useEffect(() => {
    // Guard: prevent double-initialisation from React Strict Mode or HMR.
    if (typeof window === "undefined") return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if ((window as any).__OPENOBSERVE_RUM_INITIALIZED__) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).__OPENOBSERVE_RUM_INITIALIZED__ = true;

    // Load SDKs dynamically to ensure code splitting and prevent server-side evaluation errors.
    Promise.all([import("@openobserve/browser-rum"), import("@openobserve/browser-logs")])
      .then(([{ openobserveRum }, { openobserveLogs }]) => {
        const env = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_ENV ?? "development";
        if (env === "test") {
          console.log("🚫 OpenObserve RUM & Logs client SDKs disabled in test mode.");
          return;
        }
        const clientToken = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN;
        if (!clientToken) {
          // No default: a hardcoded client token here would silently ship every
          // deployment's RUM data to whichever OpenObserve org that token was
          // originally provisioned for. Skip RUM entirely rather than guess.
          console.warn("⚠️ NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN is not set; OpenObserve RUM & Logs disabled.");
          return;
        }
        const applicationId = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_APPLICATION_ID ?? "iqoqo";
        const site = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_SITE ?? window.location.host;
        const service =
          process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_SERVICE ??
          (env === "production" ? "iqoqo-frontend" : `iqoqo-frontend-${env}`);
        const version = process.env.NEXT_PUBLIC_APP_VERSION ?? "0.0.1";
        const organizationIdentifier = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_ORG_ID ?? "default";
        const insecureHTTP = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP === "true";
        const apiVersion = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_API_VERSION ?? "v1";
        const configuredPrivacyLevel = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_PRIVACY_LEVEL;
        const isProduction = process.env.NODE_ENV === "production" || env === "production";
        const defaultPrivacyLevel =
          isProduction
            ? "mask-user-input"
            : (configuredPrivacyLevel as "allow" | "mask-user-input" | "mask" | undefined) ?? "mask-user-input";

        openobserveRum.init({
          applicationId,
          clientToken,
          site,
          organizationIdentifier,
          service,
          env,
          version,
          trackResources: true,
          trackLongTasks: true,
          trackUserInteractions: true,
          apiVersion,
          insecureHTTP,
          defaultPrivacyLevel,
        });

        openobserveLogs.init({
          clientToken,
          site,
          organizationIdentifier,
          service,
          env,
          version,
          forwardErrorsToLogs: true,
          insecureHTTP,
          apiVersion,
        });

        openobserveRum.startSessionReplayRecording();
        console.log("🏗️ OpenObserve RUM & Logs client SDKs initialised.");
      })
      .catch(err => {
        console.warn("⚠️ OpenObserve RUM/Logs initialization failed (non-fatal):", err);
      });
  }, []);

  return null;
}
