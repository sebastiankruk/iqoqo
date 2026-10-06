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

import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserOpenObserveRum } from "@/components/browser-openobserve-rum";

const rum = vi.hoisted(() => ({
  init: vi.fn(),
  startSessionReplayRecording: vi.fn(),
  setUser: vi.fn(),
}));
const logs = vi.hoisted(() => ({ init: vi.fn() }));

vi.mock("@openobserve/browser-rum", () => ({ openobserveRum: rum }));
vi.mock("@openobserve/browser-logs", () => ({ openobserveLogs: logs }));
vi.mock("@/lib/api/hooks", () => ({
  useProfile: () => ({ data: { id: "user-id", email: "private@example.test", display_name: "Private name" } }),
}));

/**
 * Set the page protocol for the duration of one test.
 *
 * @param protocol - The protocol to simulate the page being served over.
 */
function stubProtocol(protocol: "http:" | "https:") {
  Object.defineProperty(window.location, "protocol", { value: protocol, configurable: true });
}

describe("BrowserOpenObserveRum privacy defaults", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Reflect.deleteProperty(window, "__OPENOBSERVE_RUM_INITIALIZED__");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_ENV", "development");
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN", "test-token");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP", undefined);
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_PRIVACY_LEVEL", undefined);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  // Transport is no longer an unconditional constant: it is derived from the
  // page the SDK runs on. This suite runs on jsdom's default http: page, so the
  // derived value is insecure=true here — the case that keeps a bare-HTTP dev
  // instance working. The secure-by-default guarantee is asserted against an
  // https: page in the "transport derivation" block below.
  it("masks user input by default regardless of transport", async () => {
    render(<BrowserOpenObserveRum />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(
      expect.objectContaining({
        defaultPrivacyLevel: "mask-user-input",
      })
    );
  });

  it("is secure by default on a secure page", async () => {
    Object.defineProperty(window.location, "protocol", { value: "https:", configurable: true });
    render(<BrowserOpenObserveRum />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(
      expect.objectContaining({
        insecureHTTP: false,
        defaultPrivacyLevel: "mask-user-input",
      })
    );
  });

  it("does not allow production configuration to disable input masking", async () => {
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_PRIVACY_LEVEL", "allow");
    render(<BrowserOpenObserveRum />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(expect.objectContaining({ defaultPrivacyLevel: "mask-user-input" }));
  });

  it("fails closed when NODE_ENV is production even if the RUM environment is not", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_ENV", "staging");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_PRIVACY_LEVEL", "allow");
    render(<BrowserOpenObserveRum />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(expect.objectContaining({ defaultPrivacyLevel: "mask-user-input" }));
  });

  it("never identifies a profile using direct personal data", async () => {
    render(<BrowserOpenObserveRum />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.setUser).not.toHaveBeenCalled();
  });
});

describe("BrowserOpenObserveRum transport derivation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Reflect.deleteProperty(window, "__OPENOBSERVE_RUM_INITIALIZED__");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_ENV", "development");
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP", undefined);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  // The deploy path used to force INSECURE_HTTP=true unconditionally. Once
  // that override was removed, a bare-HTTP dev instance would have had the SDK
  // attempt https:// against an http:// page — so the transport has to be
  // derived from the page the SDK is actually running on.
  it("enables insecure ingest on a bare-HTTP dev page when nothing is configured", async () => {
    stubProtocol("http:");
    render(<BrowserOpenObserveRum clientToken="test-token" />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(expect.objectContaining({ insecureHTTP: true }));
  });

  it("keeps ingest secure on an HTTPS page when nothing is configured", async () => {
    stubProtocol("https:");
    render(<BrowserOpenObserveRum clientToken="test-token" />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(expect.objectContaining({ insecureHTTP: false }));
  });

  it("honours an explicit insecureHTTP prop from the server", async () => {
    stubProtocol("https:");
    render(<BrowserOpenObserveRum clientToken="test-token" insecureHTTP={true} />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(expect.objectContaining({ insecureHTTP: true }));
  });

  it("honours an explicit secure prop even on an HTTP page", async () => {
    stubProtocol("http:");
    render(<BrowserOpenObserveRum clientToken="test-token" insecureHTTP={false} />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(expect.objectContaining({ insecureHTTP: false }));
  });
});

describe("BrowserOpenObserveRum server-provided configuration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Reflect.deleteProperty(window, "__OPENOBSERVE_RUM_INITIALIZED__");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_ENV", "production");
    vi.stubEnv("NODE_ENV", "production");
    // A prebuilt image may carry a stale build-time value; the prop must win.
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN", "build-time-token");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_SITE", "stale.example");
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP", undefined);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("prefers the server-provided token over the build-time inlined one", async () => {
    render(<BrowserOpenObserveRum clientToken="per-request-token" site="iqoqo.example" />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(
      expect.objectContaining({ clientToken: "per-request-token", site: "iqoqo.example" })
    );
  });

  it("passes the same validated site to the logs SDK", async () => {
    render(<BrowserOpenObserveRum clientToken="per-request-token" site="iqoqo.example" insecureHTTP={false} />);

    await waitFor(() => expect(logs.init).toHaveBeenCalledTimes(1));
    expect(logs.init).toHaveBeenCalledWith(
      expect.objectContaining({ clientToken: "per-request-token", site: "iqoqo.example", insecureHTTP: false })
    );
  });

  it("stays disabled when no token is available at all", async () => {
    vi.stubEnv("NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN", undefined);
    render(<BrowserOpenObserveRum />);

    await waitFor(() => expect(rum.init).not.toHaveBeenCalled());
  });
});
