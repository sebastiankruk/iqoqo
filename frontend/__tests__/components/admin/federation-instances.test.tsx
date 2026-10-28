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
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FederationInstancesManager } from "@/components/admin/federation-instances";
import * as federationHooks from "@/lib/api/hooks/federation";
import { toast } from "sonner";
import enMessages from "@/messages/en.json";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: (namespace?: string) => {
    const dict = namespace === "AdminFederation" ? (enMessages as any).AdminFederation : {};
    return (key: string, values?: Record<string, any>) => {
      let str = dict[key] || key;
      if (values) {
        Object.entries(values).forEach(([k, v]) => {
          str = str.replace(`{${k}}`, String(v));
        });
      }
      return str;
    };
  },
}));

vi.mock("@/lib/api/hooks/federation", () => ({
  useFederationInstances: vi.fn(),
  useAddFederationInstance: vi.fn(),
  useUpdateInstanceTrust: vi.fn(),
  useRemoveFederationInstance: vi.fn(),
}));

describe("FederationInstancesManager Component", () => {
  const mockAddMutate = vi.fn();
  const mockUpdateTrustMutate = vi.fn();
  const mockRemoveMutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(federationHooks.useAddFederationInstance).mockReturnValue({
      mutateAsync: mockAddMutate,
      isPending: false,
    } as any);

    vi.mocked(federationHooks.useUpdateInstanceTrust).mockReturnValue({
      mutateAsync: mockUpdateTrustMutate,
      isPending: false,
    } as any);

    vi.mocked(federationHooks.useRemoveFederationInstance).mockReturnValue({
      mutateAsync: mockRemoveMutate,
      isPending: false,
    } as any);
  });

  it("renders empty state when no peer instances are registered", () => {
    vi.mocked(federationHooks.useFederationInstances).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as any);

    render(<FederationInstancesManager />);

    expect(screen.getByTestId("peering-guidance-banner")).toBeInTheDocument();
    expect(screen.getByText("ActivityPub Peering is Unilateral")).toBeInTheDocument();
    expect(
      screen.getByText(/The remote peer administrator must also add your instance for reciprocal trust/i)
    ).toBeInTheDocument();
    expect(screen.getByText("No peer instances registered yet")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("library.example.org")).toBeInTheDocument();
  });

  it("renders peer instances list with domains, software, and trust badges", () => {
    vi.mocked(federationHooks.useFederationInstances).mockReturnValue({
      data: [
        {
          id: 1,
          domain: "library.alpha.org",
          software_name: "iqoqo",
          software_version: "0.9.1",
          trust_level: "trusted",
          last_seen_at: null,
        },
        {
          id: 2,
          domain: "bookwyrm.social",
          software_name: "BookWyrm",
          software_version: "0.7.0",
          trust_level: "pending",
          last_seen_at: new Date(Date.now() - 120000).toISOString(),
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    render(<FederationInstancesManager />);

    expect(screen.getByText("library.alpha.org")).toBeInTheDocument();
    expect(screen.getByText("iqoqo 0.9.1")).toBeInTheDocument();
    expect(screen.getByText("bookwyrm.social")).toBeInTheDocument();
    expect(screen.getByText("BookWyrm 0.7.0")).toBeInTheDocument();
    expect(screen.getAllByText("Trusted").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Pending Review")).toBeInTheDocument();
  });

  it("discovers and adds a peer instance", async () => {
    const user = userEvent.setup();
    vi.mocked(federationHooks.useFederationInstances).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as any);
    mockAddMutate.mockResolvedValueOnce({ id: 3, domain: "peer.example.org" });

    render(<FederationInstancesManager />);

    const input = screen.getByPlaceholderText("library.example.org");
    const submitBtn = screen.getByRole("button", { name: /Add Peer/i });

    await user.type(input, "peer.example.org");
    await user.click(submitBtn);

    expect(mockAddMutate).toHaveBeenCalledWith("peer.example.org");
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Discovered and registered instance peer.example.org");
    });
  });

  it("updates trust level when changed via dropdown", async () => {
    const user = userEvent.setup();
    vi.mocked(federationHooks.useFederationInstances).mockReturnValue({
      data: [
        {
          id: 1,
          domain: "library.alpha.org",
          software_name: "iqoqo",
          software_version: "0.9.1",
          trust_level: "pending",
          last_seen_at: null,
        },
      ],
      isLoading: false,
      error: null,
    } as any);
    mockUpdateTrustMutate.mockResolvedValueOnce({ id: 1, trust_level: "trusted" });

    render(<FederationInstancesManager />);

    const select = screen.getByLabelText("Change trust level for library.alpha.org");
    await user.selectOptions(select, "trusted");

    expect(mockUpdateTrustMutate).toHaveBeenCalledWith({
      instanceId: 1,
      trustLevel: "trusted",
    });
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Updated trust level for library.alpha.org to trusted");
    });
  });

  it("opens delete confirmation dialog and removes instance", async () => {
    const user = userEvent.setup();
    vi.mocked(federationHooks.useFederationInstances).mockReturnValue({
      data: [
        {
          id: 1,
          domain: "library.alpha.org",
          software_name: "iqoqo",
          software_version: "0.9.1",
          trust_level: "trusted",
          last_seen_at: null,
        },
      ],
      isLoading: false,
      error: null,
    } as any);
    mockRemoveMutate.mockResolvedValueOnce(undefined);

    render(<FederationInstancesManager />);

    const deleteBtn = screen.getByLabelText("Remove instance library.alpha.org");
    await user.click(deleteBtn);

    expect(screen.getByText("Remove Peer Instance")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Are you sure you want to remove library.alpha.org? This will terminate metadata sync with this instance."
      )
    ).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: "Remove Peer" });
    await user.click(confirmBtn);

    expect(mockRemoveMutate).toHaveBeenCalledWith(1);
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Removed instance library.alpha.org");
    });
  });
});
