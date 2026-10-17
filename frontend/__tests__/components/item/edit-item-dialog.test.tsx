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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { EditItemDialog } from "@/components/item/edit-item-dialog";

const mockMutateAsync = vi.fn().mockResolvedValue({});

vi.mock("@/lib/api/hooks", () => ({
  useUpdateItem: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe("EditItemDialog", () => {
  const mockItem = {
    id: 123,
    manifestation_id: 10,
    owner_id: "user-1",
    status: "read",
    collection_status: "available",
    condition: "Good",
    local_barcode: "TAG-456",
    meta: {},
  } as any;

  it("renders local barcode and condition fields with initial item values", () => {
    render(<EditItemDialog item={mockItem} isOpen={true} onOpenChange={vi.fn()} />);

    expect(screen.getByDisplayValue("TAG-456")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Good")).toBeInTheDocument();
  });

  it("submits updated local barcode on save", async () => {
    const onOpenChange = vi.fn();
    render(<EditItemDialog item={mockItem} isOpen={true} onOpenChange={onOpenChange} />);

    const barcodeInput = screen.getByLabelText(/Local Barcode/i);
    fireEvent.change(barcodeInput, { target: { value: "NEW-SHELF-99" } });

    const submitBtn = screen.getByRole("button", { name: /Save Changes/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        local_barcode: "NEW-SHELF-99",
        condition: "Good",
      });
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("submits null when local barcode is cleared", async () => {
    render(<EditItemDialog item={mockItem} isOpen={true} onOpenChange={vi.fn()} />);

    const barcodeInput = screen.getByLabelText(/Local Barcode/i);
    fireEvent.change(barcodeInput, { target: { value: "" } });

    const submitBtn = screen.getByRole("button", { name: /Save Changes/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        local_barcode: null,
        condition: "Good",
      });
    });
  });
});
