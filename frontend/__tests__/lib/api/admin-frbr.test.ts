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
import { describe, it, expect, vi, beforeEach } from "vitest";
import { getFrbrTree, updateFrbrEntity, searchFrbrEntities } from "@/lib/api/admin";
import { apiFetch, apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
  apiClient: {
    put: vi.fn(),
  },
}));

describe("Admin API - FRBR endpoints", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getFrbrTree", () => {
    it("should successfully fetch the FRBR tree for a manifestation", async () => {
      const mockResponse = {
        work: { id: 1, title: "Test Work" },
        expression: { id: 2, work_id: 1, content_type: "text", language: "en", meta: {} },
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: "9781234567890",
          upc: null,
          ean: null,
          publisher: "Test",
          publication_date: null,
          meta: {},
        },
        items: [],
      };
      vi.mocked(apiFetch).mockResolvedValueOnce(mockResponse);

      const result = await getFrbrTree(123);

      expect(apiFetch).toHaveBeenCalledWith("/v1/admin/frbr/tree/manifestation/123");
      expect(result).toEqual(mockResponse);
    });

    it("should throw an error if apiFetch fails", async () => {
      vi.mocked(apiFetch).mockRejectedValueOnce(new Error("Network error"));
      await expect(getFrbrTree(123)).rejects.toThrow("Network error");
    });
  });

  describe("updateFrbrEntity", () => {
    it("should send a PUT request to update a work", async () => {
      const mockPayload = { title: "Updated Title", meta: { key: "value" } };
      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: true, data: { id: 1 } },
        status: 200,
        statusText: "OK",
        headers: {},
        config: {} as any,
      });

      const result = await updateFrbrEntity("work", 1, mockPayload);

      expect(apiClient.put).toHaveBeenCalledWith("/v1/admin/frbr/work/1", mockPayload);
      expect(result).toEqual({ id: 1 });
    });

    it("should send a PUT request to update an expression", async () => {
      const mockPayload = { content_type: "audio", language: "pl" };
      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: true, data: { id: 2 } },
        status: 200,
        statusText: "OK",
        headers: {},
        config: {} as any,
      });

      const result = await updateFrbrEntity("expression", 2, mockPayload);

      expect(apiClient.put).toHaveBeenCalledWith("/v1/admin/frbr/expression/2", mockPayload);
      expect(result).toEqual({ id: 2 });
    });

    it("should send a PUT request to update a manifestation", async () => {
      const mockPayload = { publisher: "New Publisher", isbn13: "9781234567890" };
      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: true, data: { id: 3 } },
        status: 200,
        statusText: "OK",
        headers: {},
        config: {} as any,
      });

      const result = await updateFrbrEntity("manifestation", 3, mockPayload);

      expect(apiClient.put).toHaveBeenCalledWith("/v1/admin/frbr/manifestation/3", mockPayload);
      expect(result).toEqual({ id: 3 });
    });

    it("should send a PUT request to update an item", async () => {
      const mockPayload = { status: "lent", condition: "Good" };
      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: true, data: { id: 10 } },
        status: 200,
        statusText: "OK",
        headers: {},
        config: {} as any,
      });

      const result = await updateFrbrEntity("item", 10, mockPayload);

      expect(apiClient.put).toHaveBeenCalledWith("/v1/admin/frbr/item/10", mockPayload);
      expect(result).toEqual({ id: 10 });
    });

    it("should throw an error if the API returns success: false", async () => {
      vi.mocked(apiClient.put).mockResolvedValueOnce({
        data: { success: false, error: "Validation failed" },
        status: 400,
        statusText: "Bad Request",
        headers: {},
        config: {} as any,
      });

      await expect(updateFrbrEntity("expression", 2, {})).rejects.toThrow("Validation failed");
    });
  });

  describe("searchFrbrEntities", () => {
    it("should search manifestations by ISBN", async () => {
      const mockResponse = [{ id: 1, title: "Test Book", isbn13: "9781234567890", type: "manifestation" as const }];
      vi.mocked(apiFetch).mockResolvedValueOnce(mockResponse);

      const result = await searchFrbrEntities("9781234567890", "manifestation");

      expect(apiFetch).toHaveBeenCalledWith("/v1/admin/frbr/search?q=9781234567890&type=manifestation&limit=20");
      expect(result).toEqual(mockResponse);
    });

    it("should search works by title", async () => {
      const mockResponse = [{ id: 1, title: "Dune", type: "work" as const }];
      vi.mocked(apiFetch).mockResolvedValueOnce(mockResponse);

      const result = await searchFrbrEntities("Dune", "work");

      expect(apiFetch).toHaveBeenCalledWith("/v1/admin/frbr/search?q=Dune&type=work&limit=20");
      expect(result).toEqual(mockResponse);
    });
  });
});
