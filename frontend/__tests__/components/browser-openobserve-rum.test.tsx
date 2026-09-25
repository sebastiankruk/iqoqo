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

  it("uses secure transport and masks user input by default", async () => {
    render(<BrowserOpenObserveRum />);

    await waitFor(() => expect(rum.init).toHaveBeenCalledTimes(1));
    expect(rum.init).toHaveBeenCalledWith(expect.objectContaining({
      insecureHTTP: false,
      defaultPrivacyLevel: "mask-user-input",
    }));
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
