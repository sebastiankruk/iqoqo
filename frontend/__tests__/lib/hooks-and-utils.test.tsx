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
import { act, render, renderHook, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";
import NotFound from "@/app/not-found";
import { useMediaQuery } from "@/hooks/use-media-query";
import { useDebounce } from "@/lib/hooks/use-debounce";
import enMessages from "@/messages/en.json";

describe("Frontend utility hooks & NotFound page", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("useDebounce delays updating until timeout elapses", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(({ val }) => useDebounce(val, 250), {
      initialProps: { val: "initial" },
    });

    expect(result.current).toBe("initial");
    rerender({ val: "updated" });
    expect(result.current).toBe("initial");

    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(result.current).toBe("updated");
  });

  it("useMediaQuery tracks matchMedia state and reacts to change events", () => {
    let listener: (() => void) | undefined;
    let matches = false;
    vi.spyOn(window, "matchMedia").mockImplementation(
      (query: string) =>
        ({
          matches,
          media: query,
          addEventListener: (_event: string, cb: () => void) => {
            listener = cb;
          },
          removeEventListener: vi.fn(),
        }) as unknown as MediaQueryList
    );

    const { result } = renderHook(() => useMediaQuery("(max-width: 768px)"));
    expect(result.current).toBe(false);

    matches = true;
    act(() => {
      listener?.();
    });
    expect(result.current).toBe(true);
  });

  it("NotFound renders localized 404 heading and home link", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <NotFound />
      </NextIntlClientProvider>
    );
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", "/");
  });
});
