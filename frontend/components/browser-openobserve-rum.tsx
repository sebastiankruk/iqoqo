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

export interface BrowserOpenObserveRumProps {
  /**
   * RUM client token, injected by the server layout at request time.
   *
   * Deliberately a prop and not a `NEXT_PUBLIC_*` read: Next.js inlines
   * `process.env.NEXT_PUBLIC_*` into the client bundle at **build** time, and
   * `--prebuilt` deployments pull the frontend image from a registry where it
   * was built on CI. A build-time value would either be impossible to set per
   * instance or would bake one instance's token into a shared image.
   *
   * This does not weaken the posture — a RUM client token is public by
   * construction, since anyone who can view the page source can read it.
   */
  clientToken?: string;
  /** Validated ingest target. Defaults to the host of the page the SDK runs on. */
  site?: string;
  /** Transport override. When omitted, derived from the page's own protocol. */
  insecureHTTP?: boolean;
  /** Session replay privacy level. Defaults to masking user input. */
  privacyLevel?: "allow" | "mask-user-input" | "mask";
}

/**
 * BrowserOpenObserveRum — client-side bootstrap for OpenObserve RUM and Logs SDKs.
 *
 * Renders nothing. Must be placed inside the React Query <Providers> context
 * in the root layout so RUM and Logs can initialize in the browser.
 *
 * @param props - Optional server-provided configuration; see the interface above.
 * @param props.clientToken - RUM client token, injected by the server layout at request time.
 * @param props.site - Validated ingest target. Defaults to the host of the page the SDK runs on.
 * @param props.insecureHTTP - Transport override. When omitted, derived from the page's own protocol.
 * @param props.privacyLevel - Session replay privacy level. Defaults to masking user input.
 * @returns {null} Always returns null — no DOM output.
 */
export function BrowserOpenObserveRum({
  clientToken: clientTokenProp,
  site: siteProp,
  insecureHTTP: insecureHTTPProp,
  privacyLevel: privacyLevelProp,
}: BrowserOpenObserveRumProps = {}): null {
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
        // Prop wins over the build-time inlined value: the prop is the
        // per-request value, the env var is whatever the image was built with.
        const clientToken = clientTokenProp ?? process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN;
        if (!clientToken) {
          // No default: a hardcoded client token here would silently ship every
          // deployment's RUM data to whichever OpenObserve org that token was
          // originally provisioned for. Skip RUM entirely rather than guess.
          console.warn("⚠️ OpenObserve RUM & Logs disabled: no client token configured.");
          return;
        }
        const applicationId = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_APPLICATION_ID ?? "iqoqo";
        const site = siteProp ?? process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_SITE ?? window.location.host;
        const service =
          process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_SERVICE ??
          (env === "production" ? "iqoqo-frontend" : `iqoqo-frontend-${env}`);
        const version = process.env.NEXT_PUBLIC_APP_VERSION ?? "0.0.1";
        const organizationIdentifier = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_ORG_ID ?? "default";

        // Transport is derived from the page the SDK is actually running on
        // when nothing explicit is configured. Deriving it matters: the deploy
        // path used to force INSECURE_HTTP=true unconditionally, which both
        // sent the token in cleartext from a production deployment and, once
        // the SITE override was removed, would have broken a bare-HTTP dev
        // instance by making the SDK attempt https:// against an http:// page.
        const configuredInsecure = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP;
        const insecureHTTP =
          insecureHTTPProp ??
          (configuredInsecure !== undefined && configuredInsecure !== ""
            ? configuredInsecure === "true"
            : window.location.protocol === "http:");

        const apiVersion = process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_API_VERSION ?? "v1";
        const configuredPrivacyLevel =
          privacyLevelProp ??
          (process.env.NEXT_PUBLIC_OPENOBSERVE_RUM_PRIVACY_LEVEL as "allow" | "mask-user-input" | "mask" | undefined);
        const isProduction = process.env.NODE_ENV === "production" || env === "production";
        // Session replay recording is unconditional below, so this privacy
        // level is the only thing standing between an operator's users and
        // unmasked DOM text and keystrokes. It defaults to masking in *every*
        // environment; only production refuses to be overridden at all.
        // (run.sh previously defaulted this to "allow", which recorded user
        // input unmasked with no retention configured anywhere.)
        const defaultPrivacyLevel = isProduction ? "mask-user-input" : (configuredPrivacyLevel ?? "mask-user-input");

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
        // Log the message only. If the SDK ever throws with its config
        // attached, logging the error object would put the client token in the
        // browser console.
        console.warn("⚠️ OpenObserve RUM/Logs initialization failed (non-fatal):", err?.message ?? String(err));
      });
    // The props are intentionally excluded from the dependency list. The SDKs
    // are initialised exactly once per page load; re-initialising on a prop
    // change would double-count sessions and restart session replay. A changed
    // token takes effect on the next page load, which is the correct behaviour
    // for a per-request credential.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}
