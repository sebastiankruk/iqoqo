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

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminLendingPage from "@/app/admin/lending/page";
import { useProfile, useLoanRequests, useResolveLoan } from "@/lib/api/hooks";
import { useRouter } from "next/navigation";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { UserProfile } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
  useLoanRequests: vi.fn(),
  useResolveLoan: vi.fn(),
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

describe("AdminLendingPage", () => {
  const mockPush = vi.fn();
  const mockMutateAsync = vi.fn().mockResolvedValue({});

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      replace: vi.fn(),
      prefetch: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    });
    vi.mocked(useResolveLoan).mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useResolveLoan>);
  });

  it("renders loading state when profile is loading", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof useProfile>);
    vi.mocked(useLoanRequests).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useLoanRequests>);

    render(<AdminLendingPage />);
    expect(screen.getByText("Loading profile...")).toBeInTheDocument();
  });

  it("redirects unauthenticated users to /login", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);
    vi.mocked(useLoanRequests).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useLoanRequests>);

    render(<AdminLendingPage />);
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });

  it("renders empty state when there are no loan requests", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { id: "custodian-1", email: "custodian@iqoqo.cc" } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);
    vi.mocked(useLoanRequests).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useLoanRequests>);

    render(<AdminLendingPage />);
    expect(screen.getByText("No Loan Requests")).toBeInTheDocument();
    expect(screen.getByText(/When other users browse your catalog/i)).toBeInTheDocument();
  });

  it("renders pending loan requests and coordinates approve action", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { id: "custodian-1", email: "custodian@iqoqo.cc" } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    const mockRequests = [
      {
        id: 101,
        item_id: 201,
        item_title: "Solaris (Stanisław Lem)",
        requester_name: "Kelvin",
        created_at: "2026-10-25T12:00:00Z",
        status: "pending",
        notes: "Borrowing for reading group discussion",
      },
    ];

    vi.mocked(useLoanRequests).mockReturnValue({
      data: mockRequests,
      isLoading: false,
    } as unknown as ReturnType<typeof useLoanRequests>);

    render(<AdminLendingPage />);

    expect(screen.getByText("Solaris (Stanisław Lem)")).toBeInTheDocument();
    expect(screen.getByText("Kelvin")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText(/Borrowing for reading group discussion/i)).toBeInTheDocument();

    const approveButton = screen.getByRole("button", { name: "Approve Loan" });
    expect(approveButton).toBeInTheDocument();

    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        requestId: 101,
        action: "approve",
      });
    });
  });

  it("coordinates reject action on pending loan request", async () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { id: "custodian-1", email: "custodian@iqoqo.cc" } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    const mockRequests = [
      {
        id: 102,
        item_id: 202,
        item_title: "Neuromancer (William Gibson)",
        requester_name: "Case",
        created_at: "2026-10-26T14:30:00Z",
        status: "pending",
        notes: null,
      },
    ];

    vi.mocked(useLoanRequests).mockReturnValue({
      data: mockRequests,
      isLoading: false,
    } as unknown as ReturnType<typeof useLoanRequests>);

    render(<AdminLendingPage />);

    const rejectButton = screen.getByRole("button", { name: "Reject Loan" });
    expect(rejectButton).toBeInTheDocument();

    fireEvent.click(rejectButton);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        requestId: 102,
        action: "reject",
      });
    });
  });

  it("renders approved requests as Lent with action buttons hidden", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { id: "custodian-1", email: "custodian@iqoqo.cc" } as unknown as UserProfile,
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    const mockRequests = [
      {
        id: 103,
        item_id: 203,
        item_title: "Dune (Frank Herbert)",
        requester_name: "Paul",
        created_at: "2026-10-20T10:00:00Z",
        status: "approved",
      },
    ];

    vi.mocked(useLoanRequests).mockReturnValue({
      data: mockRequests,
      isLoading: false,
    } as unknown as ReturnType<typeof useLoanRequests>);

    render(<AdminLendingPage />);

    expect(screen.getByText("Dune (Frank Herbert)")).toBeInTheDocument();
    expect(screen.getByText("Lent")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve Loan" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject Loan" })).not.toBeInTheDocument();
  });
});
