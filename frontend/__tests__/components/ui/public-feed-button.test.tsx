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

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PublicFeedButton } from "@/components/ui/public-feed-button";
import * as platform from "@/lib/capacitor/platform";
import * as navigation from "@/lib/capacitor/navigation";
import * as storage from "@/lib/capacitor/storage";

describe("PublicFeedButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with default label and title", () => {
    render(<PublicFeedButton feedPath="/api/public/feed.xml" />);
    const link = screen.getByRole("link", { name: /rss feed/i });
    expect(link).toBeInTheDocument();
  });

  it("resolves URL against instance URL on native mobile and intercepts click", () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    vi.spyOn(storage, "getSyncInstanceUrl").mockReturnValue("https://preview.iqoqo.cc");
    const openSpy = vi.spyOn(navigation, "openExternalUrl").mockResolvedValue(undefined);

    render(<PublicFeedButton feedPath="/api/public/feed.xml" />);
    const link = screen.getByRole("link", { name: /rss feed/i });
    expect(link).toHaveAttribute("href", "https://preview.iqoqo.cc/api/public/feed.xml");

    fireEvent.click(link);
    expect(openSpy).toHaveBeenCalledWith("https://preview.iqoqo.cc/api/public/feed.xml");
  });
});
