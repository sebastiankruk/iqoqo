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
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SidebarCover } from "@/components/item/sidebar/sidebar-cover";
import type { Item } from "@/types/frbr";

describe("SidebarCover Unit Test (Plain Props)", () => {
  const baseItem = {
    id: 1,
    title: "Dune",
    manifestation_meta: { cover_source: "manual" },
    meta: {},
  } as unknown as Item;

  it("renders cover image when coverUrl is provided", () => {
    render(
      <SidebarCover
        item={baseItem}
        coverUrl="/api/static/covers/dune.jpg"
        format="book"
        isAudio={false}
        isVideo={false}
        isGame={false}
        isBook={true}
      />
    );

    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "/api/static/covers/dune.jpg");
    expect(img).toHaveAttribute("alt", "Dune");
  });

  it("renders audio fallback icon when coverUrl is absent and media is audio", () => {
    const { container } = render(
      <SidebarCover item={baseItem} format="audio" isAudio={true} isVideo={false} isGame={false} isBook={false} />
    );

    expect(screen.queryByRole("img")).toBeNull();
    expect(container.querySelector(".aspect-square")).toBeInTheDocument();
  });
});
