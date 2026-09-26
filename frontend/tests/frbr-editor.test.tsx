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
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FrbrEditor } from "@/components/admin/frbr-editor";
import * as adminApi from "@/lib/api/admin";
import { PermissionName } from "@/lib/permissions";

vi.mock("@/lib/api/admin");

vi.mock("@/lib/api/escalations", () => ({
  useCreateEscalation: vi.fn(() => ({
    mutateAsync: vi.fn(),
  })),
}));

const mockFrbrTree = {
  work: { id: 1, title: "Dune", meta: { original_language: "en" } },
  expression: { id: 2, work_id: 1, content_type: "text", language: "en", kind: "live_performance", meta: {} },
  manifestation: {
    id: 3,
    expression_id: 2,
    isbn13: "9780441172719",
    upc: null,
    ean: null,
    publisher: "Ace Books",
    publication_date: "1965-08-01",
    format: null,
    label: null,
    barcode: null,
    catalog_number: null,
    meta: { pages: "412", type: "Book" },
  },
  items: [
    {
      id: 10,
      manifestation_id: 3,
      condition: "like_new",
      status: "available",
      local_barcode: null,
      inventory_tag: null,
      meta: {},
      owner_id: "user1",
      owner_name: "Test User",
    },
  ],
};

const mockUpdateMutation = {
  mutateAsync: vi.fn().mockResolvedValue({ id: 1 }),
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  status: "idle" as const,
  data: undefined,
  error: null,
  variables: undefined,
  reset: vi.fn(),
  submittedAt: 0,
  failureCount: 0,
  failureReason: null,
  context: undefined,
};

const mockDeleteMutation = {
  mutateAsync: vi.fn().mockResolvedValue({}),
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  status: "idle" as const,
  data: undefined,
  error: null,
  variables: undefined,
  reset: vi.fn(),
  submittedAt: 0,
  failureCount: 0,
  failureReason: null,
  context: undefined,
};

const mockAddChildMutation = {
  mutateAsync: vi.fn().mockResolvedValue({ id: 99 }),
  mutate: vi.fn(),
  isPending: false,
};

vi.mock("@/lib/api/hooks", () => ({
  useWorkParts: vi.fn(() => ({
    data: { data: [] },
    isLoading: false,
    refetch: vi.fn(),
  })),
  useProfile: vi.fn(() => ({
    data: { permissions: [PermissionName.WRITE_METADATA, PermissionName.ESCALATE_REQUEST] },
  })),
  useFrbrTree: vi.fn(() => ({
    data: mockFrbrTree,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
  useUpdateFrbrEntity: vi.fn(() => mockUpdateMutation),
  useDeleteFrbrEntity: vi.fn(() => mockDeleteMutation),
  useAddFrbrChild: vi.fn(() => mockAddChildMutation),
  useUserSearch: vi.fn(() => ({
    data: [],
    isLoading: false,
  })),
}));

vi.mock("@/components/ui/select", () => ({
  Select: ({ value, onValueChange, children }: any) => (
    <select value={value} onChange={e => onValueChange(e.target.value)}>
      {children}
    </select>
  ),
  SelectTrigger: ({ children }: any) => children,
  SelectValue: () => null,
  SelectContent: ({ children }: any) => children,
  SelectGroup: ({ children, ...props }: any) => <optgroup {...props}>{children}</optgroup>,
  SelectLabel: ({ children }: any) => <option disabled>{children}</option>,
  SelectItem: ({ value, children }: any) => <option value={value}>{children}</option>,
}));

vi.mock("@/components/ui/alert-dialog", () => ({
  AlertDialog: ({ children, open }: any) => (open ? <div data-testid="alert-dialog">{children}</div> : null),
  AlertDialogContent: ({ children }: any) => <div>{children}</div>,
  AlertDialogHeader: ({ children }: any) => <div>{children}</div>,
  AlertDialogFooter: ({ children }: any) => <div>{children}</div>,
  AlertDialogTitle: ({ children }: any) => <h2>{children}</h2>,
  AlertDialogDescription: ({ children }: any) => <p>{children}</p>,
  AlertDialogAction: ({ children, onClick, className }: any) => (
    <button onClick={onClick} className={className}>
      {children}
    </button>
  ),
  AlertDialogCancel: ({ children }: any) => <button>{children}</button>,
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children, open }: any) => (open ? <div data-testid="dialog">{children}</div> : null),
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
  DialogDescription: ({ children }: any) => <p>{children}</p>,
  DialogFooter: ({ children }: any) => <div>{children}</div>,
}));

describe("FrbrEditor Component", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminApi.getFrbrTree).mockResolvedValue(mockFrbrTree as any);
    vi.mocked(adminApi.updateFrbrEntity).mockResolvedValue({
      data: { success: true },
    } as any);
  });

  it("renders the FRBR tree view and level selector", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => {
      expect(screen.getByTestId("frbr-tree-view")).toBeInTheDocument();
      expect(screen.getByText("Work (F1)")).toBeInTheDocument();
      expect(screen.getByText("Expression (F2)")).toBeInTheDocument();
      expect(screen.getByText("Manifestation (F3)")).toBeInTheDocument();
      expect(screen.getByText(/Items \(F5\)/)).toBeInTheDocument();
    });
  });

  it("displays manifestation data in the form", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("9780441172719")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Ace Books")).toBeInTheDocument();
    });
  });

  it("allows switching to the Work tab and displays correct data", async () => {
    const { container } = render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByDisplayValue("Ace Books")).toBeInTheDocument());

    const levelSelect = container.querySelector("select") as HTMLSelectElement;
    fireEvent.change(levelSelect, { target: { value: "work" } });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Dune")).toBeInTheDocument();
    });
  });

  it("allows switching to the Expression tab", async () => {
    const { container } = render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByDisplayValue("Ace Books")).toBeInTheDocument());

    const levelSelect = container.querySelector("select") as HTMLSelectElement;
    fireEvent.change(levelSelect, { target: { value: "expression" } });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Text (Book/Comic/Manga/Magazine)")).toBeInTheDocument();
      expect(screen.getByDisplayValue("en")).toBeInTheDocument();
    });
  });

  it("allows switching to the Items tab and expanding an item", async () => {
    const { container } = render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByDisplayValue("Ace Books")).toBeInTheDocument());

    const levelSelect = container.querySelector("select") as HTMLSelectElement;
    fireEvent.change(levelSelect, { target: { value: "items" } });

    await waitFor(() => {
      expect(screen.getByText(/Item #10/)).toBeInTheDocument();
    });

    // Click on the expand button for the item row
    const expandButtons = screen.getAllByRole("button");
    const itemExpandButton = expandButtons.find(btn => btn.textContent?.includes("Item #10"));
    if (itemExpandButton) {
      fireEvent.click(itemExpandButton);
    }

    await waitFor(() => {
      const statusInputs = screen.queryAllByDisplayValue("available");
      expect(statusInputs.length).toBeGreaterThan(0);
    });
  });

  it("submits updated manifestation data via the mutation hook", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByDisplayValue("Ace Books")).toBeInTheDocument());

    const pubInput = screen.getByDisplayValue("Ace Books");
    fireEvent.change(pubInput, { target: { value: "Penguin" } });

    const saveButton = screen.getByRole("button", { name: /Save Manifestation/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateMutation.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          manifestationId: 3,
          type: "manifestation",
          id: 3,
          data: expect.objectContaining({
            publisher: "Penguin",
            isbn13: "9780441172719",
          }),
        })
      );
    });
  });

  it("renders kind dropdown on the Expression tab and submits kind", async () => {
    const { container } = render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(container.querySelector("select")).toBeInTheDocument());

    const levelSelect = container.querySelector("select") as HTMLSelectElement;
    fireEvent.change(levelSelect, { target: { value: "expression" } });

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Studio / Default" })).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "Live Performance" })).toBeInTheDocument();
    });

    const kindSelect = screen.getByDisplayValue("Live Performance");
    expect(kindSelect).toBeInTheDocument();

    fireEvent.change(kindSelect, { target: { value: "" } });

    const saveButton = screen.getByRole("button", { name: /Save Expression/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateMutation.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          manifestationId: 3,
          type: "expression",
          id: 2,
          data: expect.objectContaining({
            kind: "",
          }),
        })
      );
    });
  });

  it("tree view displays entity nodes with correct badges", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => {
      expect(screen.getByTestId("tree-node-work")).toBeInTheDocument();
      expect(screen.getByTestId("tree-node-expression")).toBeInTheDocument();
      expect(screen.getByTestId("tree-node-manifestation")).toBeInTheDocument();
    });
  });

  it("tree view node selection switches the active tab", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => {
      expect(screen.getByTestId("tree-node-work")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tree-node-work"));

    await waitFor(() => {
      expect(screen.getByDisplayValue("Dune")).toBeInTheDocument();
    });
  });
});
