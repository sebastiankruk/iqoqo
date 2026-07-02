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
import { useProfile } from "@/lib/api/hooks";

/**
 * BrowserOpenObserveRum — client-side bootstrap for OpenObserve RUM and Logs SDKs.
 *
 * Renders nothing. Must be placed inside the React Query <Providers> context
 * in the root layout so it can query the active user profile and assign RUM user context.
 *
 * @returns {null} Always returns null — no DOM output.
 */
export function BrowserOpenObserveRum(): null {
  const { data: profile } = useProfile();

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
        const clientToken = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN ?? "rumST8CMTyDstlTbPUm";
        const applicationId = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_APPLICATION_ID ?? "web-application-id";
        const site = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_SITE ?? "localhost:5080";
        const service = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_SERVICE ?? "iqoqo-frontend";
        const env = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_ENV ?? "development";
        const version = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_VERSION ?? "0.0.1";
        const organizationIdentifier = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_ORG_ID ?? "default";
        const insecureHTTP = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP !== "false";
        const apiVersion = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_API_VERSION ?? "v1";
        const defaultPrivacyLevel = (process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_PRIVACY_LEVEL ?? "allow") as
          | "allow"
          | "mask-user-input"
          | "mask";

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

  // Update user context in RUM when the user profile session changes.
  useEffect(() => {
    if (
      typeof window === "undefined" ||
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      !(window as any).__OPENOBSERVE_RUM_INITIALIZED__
    ) {
      return;
    }

    if (profile) {
      import("@openobserve/browser-rum")
        .then(({ openobserveRum }) => {
          openobserveRum.setUser({
            id: profile.id,
            name: profile.display_name ?? profile.email,
            email: profile.email,
          });
        })
        .catch(err => {
          console.warn("⚠️ Failed to set OpenObserve RUM user context:", err);
        });
    }
  }, [profile]);

  return null;
}
