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
import { RequestNewTypeModal } from "@/components/social/request-new-type-modal";

vi.mock("next-intl", () => ({
  useTranslations: () => {
    return (key: string) => {
      const msgs: Record<string, string> = {
        requestNewMediaType: "Request New Media Type",
        requestNewMediaTypeTitle: "Request New Media Type or Format",
        requestNewMediaTypeDesc: "Propose a new media category or physical format not yet supported in iqoqo.",
        proposedCategoryLabel: "Proposed Category",
        proposedFormatLabel: "Proposed Format",
        parentFrbrClassLabel: "Ontology FRBR Class",
        sampleIdentifierLabel: "Sample Barcode, Identifier or URL",
        rationaleLabel: "Rationale & Why it should be added",
        submitRequest: "Submit Request",
        cancel: "Cancel",
        confirm: "Close",
        submitting: "Submitting...",
        requestSubmittedTitle: "Proposal Submitted",
        newMediaTypeSubmittedToast: "New media type request submitted to custodians",
        allRequiredFieldsError: "Please fill in all required fields.",
        failedToSubmit: "Failed to submit escalation request",
      };
      return msgs[key] || key;
    };
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockMutate = vi.fn();
vi.mock("@/lib/api/escalations", () => ({
  useCreateNewMediaTypeEscalation: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

describe("RequestNewTypeModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders trigger and opens dialog on click", async () => {
    render(<RequestNewTypeModal defaultSampleIdentifier="123456789" />);

    const trigger = screen.getByTestId("request-new-type-trigger");
    expect(trigger).toBeInTheDocument();

    await userEvent.click(trigger);

    expect(screen.getByTestId("request-new-type-modal")).toBeInTheDocument();
    expect(screen.getByTestId("sample-identifier-input")).toHaveValue("123456789");
  });

  it("submits proposal with valid inputs", async () => {
    const onSuccess = vi.fn();
    mockMutate.mockImplementation((payload, { onSuccess: cb }) => {
      cb();
    });

    render(<RequestNewTypeModal open={true} onSuccess={onSuccess} />);

    await userEvent.type(screen.getByTestId("proposed-category-input"), "Lego Sets");
    await userEvent.type(screen.getByTestId("proposed-format-input"), "Standard Box");
    await userEvent.type(
      screen.getByTestId("rationale-input"),
      "Collectors want set numbering and brick counts tracked."
    );

    const submitBtn = screen.getByTestId("submit-new-type-btn");
    await userEvent.click(submitBtn);

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        proposed_category: "Lego Sets",
        proposed_format: "Standard Box",
        parent_frbr_class: "F1_Work",
        rationale: "Collectors want set numbering and brick counts tracked.",
      }),
      expect.any(Object)
    );

    await waitFor(() => {
      expect(screen.getByText("Proposal Submitted")).toBeInTheDocument();
    });
    expect(onSuccess).toHaveBeenCalled();
  });
});
