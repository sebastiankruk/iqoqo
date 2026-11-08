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
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ExtendedMetadataMaps } from "@/components/item/extended-metadata-maps";
import { apiClient } from "@/lib/api/client";

// Mock Next.js Image component
vi.mock("next/image", () => ({
  default: ({ src, alt, ...props }: { src: string; alt: string } & Record<string, unknown>) => {
    const rest = { ...props };
    delete rest.fill;
    delete rest.priority;
    delete rest.unoptimized;
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} {...rest} />;
  },
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("ExtendedMetadataMaps", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();
  });

  const sampleMeta = {
    has_map: true,
    map_scale: "1:50,000",
    map_projection: "Transverse Mercator",
    map_attachments: [
      {
        id: "att-1",
        title: "County Atlas Plate",
        type: "atlas_plate",
        image_url: "/uploads/maps/plate1.jpg",
      },
    ],
  };

  it("renders scale, projection, and attachments", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ExtendedMetadataMaps meta={sampleMeta} manifestationId={42} canEdit={true} />
      </QueryClientProvider>
    );

    expect(screen.getByText("Cartography & Map Supplements")).toBeInTheDocument();
    expect(screen.getByText("1:50,000")).toBeInTheDocument();
    expect(screen.getByText("Transverse Mercator")).toBeInTheDocument();
    expect(screen.getByText("County Atlas Plate")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inspect Map" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
  });

  it("calls DELETE when deleting an attachment", async () => {
    vi.mocked(apiClient.delete).mockResolvedValueOnce({
      data: { success: true, message: "Map attachment removed" },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ExtendedMetadataMaps meta={sampleMeta} manifestationId={42} canEdit={true} />
      </QueryClientProvider>
    );

    const deleteBtn = screen.getByRole("button", { name: /delete/i });
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith("/manifestations/42/map-attachments/att-1");
    });
  });

  it("opens Add Map dialog and submits with scale and projection", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, data: { id: "att-2" } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ExtendedMetadataMaps meta={sampleMeta} manifestationId={42} canEdit={true} />
      </QueryClientProvider>
    );

    const addBtn = screen.getByRole("button", { name: "Add Map" });
    fireEvent.click(addBtn);

    expect(screen.getByText("Add Map Attachment")).toBeInTheDocument();

    const urlInput = screen.getByPlaceholderText(/https:\/\/example.com\/map.jpg/i);
    fireEvent.change(urlInput, { target: { value: "https://example.com/new_map.jpg" } });

    const scaleInput = screen.getByPlaceholderText(/1:50,000/i);
    fireEvent.change(scaleInput, { target: { value: "1:25,000" } });

    const submitBtn = screen.getByRole("button", { name: "Save Attachment" });
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        "/manifestations/42/map-attachments",
        expect.objectContaining({
          image_url: "https://example.com/new_map.jpg",
          scale: "1:25,000",
        })
      );
    });
  });
});
