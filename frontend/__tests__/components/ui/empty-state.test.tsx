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
import { EmptyState } from "@/components/ui/empty-state";
import { Box } from "lucide-react";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(
      <EmptyState 
        title="Empty Cave" 
        description="No rocks found here." 
        icon={Box} 
      />
    );
    expect(screen.getByText("Empty Cave")).toBeInTheDocument();
    expect(screen.getByText("No rocks found here.")).toBeInTheDocument();
  });

  it("renders children/CTA", () => {
    render(
      <EmptyState 
        title="T" 
        description="D" 
        icon={Box} 
        action={<button>Hunt Rocks</button>} 
      />
    );
    expect(screen.getByRole("button", { name: /Hunt Rocks/i })).toBeInTheDocument();
  });
});
