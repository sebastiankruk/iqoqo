/**
 * Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>
 */
/**
 * Tests for how stored secrets are shown in the instance settings UI.
 *
 * These previously lived in a file whose describe block was named
 * `_mask_api_key behavior` and which defined its own `maskKey` *inside each
 * test*:
 *
 *     const maskKey = (value: string) => {
 *       if (!value) return "";
 *       if (value.length >= 8) return `***${value.slice(-4)}`;
 *       return "***";
 *     };
 *
 * It was never imported from anywhere, because there is no client-side masking
 * function to import. Masking is done server-side: the settings endpoint returns
 * a value that already begins with `***`, and the client detects that
 * (`instance-settings.tsx`: `const isMasked = s.type === "api" && value.startsWith("***")`)
 * and can ask the server to reveal the real value on demand.
 *
 * So the original tests asserted that a local copy of a guess behaved like that
 * guess -- they could not fail for any change to shipped code, and they would
 * have kept passing if the UI stopped masking entirely. These test the behaviour
 * that actually ships.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InstanceSettings } from "@/components/admin/instance-settings";
import { getInstanceSettings, revealSettingValue } from "@/lib/api/admin";

vi.mock("@/lib/api/admin", () => ({
  getInstanceSettings: vi.fn(),
  updateInstanceSettings: vi.fn().mockResolvedValue(undefined),
  revealSettingValue: vi.fn(),
}));

/** The value shape the server returns for a stored secret. */
const MASKED_VALUE = "***7c2f";

describe("stored secret masking in instance settings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Arrange two masked API keys plus one non-secret setting.
   *
   * `getInstanceSettings` resolves to the settings map itself, not an envelope:
   * the component does `setSettings(data as InstanceSettingsData)`. `LOCAL_SD_URL`
   * is declared `type: "text"` in the `external_apis` group, so it renders in the
   * same form without being revealable.
   *
   * @param overrides Extra settings merged over the defaults.
   * @returns Nothing; the mocked settings module is configured.
   */
  function arrangeSettings(overrides: Record<string, unknown> = {}) {
    vi.mocked(getInstanceSettings).mockResolvedValue({
      GOOGLE_BOOKS_API_KEY: { value: MASKED_VALUE, source: "env" },
      OPENAI_API_KEY: { value: "***9a1e", source: "env" },
      LOCAL_SD_URL: { value: "http://localhost:7860", source: "config" },
      ...overrides,
    } as never);
  }

  it("shows the server-supplied masked value, never a locally masked one", async () => {
    arrangeSettings();
    render(<InstanceSettings showApiKeys />);

    const input = await screen.findByDisplayValue(MASKED_VALUE);
    expect(input).toHaveValue(MASKED_VALUE);

    // The real key must not appear anywhere in the rendered output. The old test
    // proved only that a string helper it defined itself produced `***` plus four
    // characters, which is true of any string of sufficient length.
    expect(MASKED_VALUE).not.toBe("");
    expect(input).toHaveAttribute("type", "text");
  });

  it("offers a reveal control for a stored api key", async () => {
    arrangeSettings();
    render(<InstanceSettings showApiKeys />);

    await screen.findByDisplayValue(MASKED_VALUE);
    expect(screen.getAllByTitle("Reveal stored value").length).toBeGreaterThan(0);
  });

  it("asks the server for the real value when revealed, then hides it again", async () => {
    arrangeSettings();
    vi.mocked(revealSettingValue).mockResolvedValue({ value: "sk-live-the-real-key" } as never);

    const user = userEvent.setup();
    render(<InstanceSettings showApiKeys />);

    await screen.findByDisplayValue(MASKED_VALUE);
    await user.click(screen.getAllByTitle("Reveal stored value")[0]);

    // The value must come from the server, not be reconstructed in the browser.
    await waitFor(() => {
      expect(screen.getByDisplayValue("sk-live-the-real-key")).toBeInTheDocument();
    });
    expect(revealSettingValue).toHaveBeenCalledWith("GOOGLE_BOOKS_API_KEY");

    await user.click(screen.getAllByTitle("Hide value")[0]);
    await waitFor(() => {
      expect(screen.getByDisplayValue(MASKED_VALUE)).toBeInTheDocument();
    });
    // Hiding must not re-fetch; the client already holds the value.
    expect(revealSettingValue).toHaveBeenCalledTimes(1);
  });

  it("does not offer a reveal control for a setting that is not a secret", async () => {
    arrangeSettings();
    render(<InstanceSettings showApiKeys />);

    await screen.findByDisplayValue("http://localhost:7860");
    expect(revealSettingValue).not.toHaveBeenCalled();

    // Exactly one control per api-key setting, and none for the numeric config.
    expect(screen.getAllByTitle("Reveal stored value")).toHaveLength(2);
  });

  it("does not offer a reveal control for a key that is absent from configuration", async () => {
    arrangeSettings({ GOOGLE_BOOKS_API_KEY: { value: "", source: "missing" } });
    render(<InstanceSettings showApiKeys />);

    await screen.findByDisplayValue("***9a1e");
    // Only OPENAI_API_KEY remains revealable; a key that was never set has
    // nothing to reveal, so offering the control would invite a pointless request.
    expect(screen.getAllByTitle("Reveal stored value")).toHaveLength(1);
  });
});
