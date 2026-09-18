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

import { describe, it, expect } from "vitest";
import {
  resolveSchemaType,
  resolveInLanguage,
  mapCollectionStatusToAvailability,
  buildOfferJsonLd,
  buildManifestationJsonLd,
  buildCollectionJsonLd,
  buildWorkJsonLd,
} from "@/lib/schema-org";

describe("Schema.org Utilities & JSON-LD Builders", () => {
  describe("resolveSchemaType", () => {
    it("maps text and book to Book", () => {
      expect(resolveSchemaType("text")).toBe("Book");
      expect(resolveSchemaType("book")).toBe("Book");
    });

    it("maps comics and graphic novels to ComicStory", () => {
      expect(resolveSchemaType("text", undefined, "comic_book")).toBe("ComicStory");
      expect(resolveSchemaType("book", undefined, "graphic_novel")).toBe("ComicStory");
      expect(resolveSchemaType(undefined, undefined, "comic_book")).toBe("ComicStory");
    });

    it("maps audiobook formats to Audiobook", () => {
      expect(resolveSchemaType("audiobook")).toBe("Audiobook");
      expect(resolveSchemaType("audio", undefined, "audiobook_cd")).toBe("Audiobook");
      expect(resolveSchemaType(undefined, undefined, "audiobook_digital")).toBe("Audiobook");
    });

    it("maps video games to VideoGame", () => {
      expect(resolveSchemaType("board_game", undefined, "video_game")).toBe("VideoGame");
      expect(resolveSchemaType("video_game")).toBe("VideoGame");
    });

    it("maps movies and video to Movie", () => {
      expect(resolveSchemaType("movie")).toBe("Movie");
      expect(resolveSchemaType("video")).toBe("Movie");
    });

    it("maps board games to Game", () => {
      expect(resolveSchemaType("board_game")).toBe("Game");
      expect(resolveSchemaType("cards")).toBe("Game");
    });

    it("maps music to MusicAlbum", () => {
      expect(resolveSchemaType("music")).toBe("MusicAlbum");
    });

    it("maps puzzles to Product", () => {
      expect(resolveSchemaType("puzzle")).toBe("Product");
      expect(resolveSchemaType(undefined, undefined, "jigsaw_puzzle")).toBe("Product");
    });

    it("falls back to CreativeWork for unknown or empty input", () => {
      expect(resolveSchemaType(undefined, undefined, undefined)).toBe("CreativeWork");
      expect(resolveSchemaType("unknown_custom_type")).toBe("CreativeWork");
    });
  });

  describe("resolveInLanguage", () => {
    it("normalizes standard 3-letter codes to 2-letter BCP 47", () => {
      expect(resolveInLanguage("eng")).toBe("en");
      expect(resolveInLanguage("pol")).toBe("pl");
      expect(resolveInLanguage("fra")).toBe("fr");
      expect(resolveInLanguage("deu")).toBe("de");
    });

    it("retains already valid 2-letter codes", () => {
      expect(resolveInLanguage("en")).toBe("en");
      expect(resolveInLanguage("pl")).toBe("pl");
      expect(resolveInLanguage("es")).toBe("es");
    });

    it("returns undefined for empty, whitespace, or null", () => {
      expect(resolveInLanguage(null)).toBeUndefined();
      expect(resolveInLanguage(undefined)).toBeUndefined();
      expect(resolveInLanguage("   ")).toBeUndefined();
    });
  });

  describe("mapCollectionStatusToAvailability", () => {
    it("maps in-stock statuses correctly", () => {
      expect(mapCollectionStatusToAvailability("owned")).toBe("https://schema.org/InStock");
      expect(mapCollectionStatusToAvailability("available")).toBe("https://schema.org/InStock");
      expect(mapCollectionStatusToAvailability("in_library")).toBe("https://schema.org/InStock");
      expect(mapCollectionStatusToAvailability("for_sale")).toBe("https://schema.org/InStock");
    });

    it("maps wishlist and ordered statuses to PreOrder", () => {
      expect(mapCollectionStatusToAvailability("wishlist")).toBe("https://schema.org/PreOrder");
      expect(mapCollectionStatusToAvailability("wish_list")).toBe("https://schema.org/PreOrder");
      expect(mapCollectionStatusToAvailability("wanted")).toBe("https://schema.org/PreOrder");
      expect(mapCollectionStatusToAvailability("ordered")).toBe("https://schema.org/PreOrder");
    });

    it("maps loan statuses to LimitedAvailability", () => {
      expect(mapCollectionStatusToAvailability("lent")).toBe("https://schema.org/LimitedAvailability");
      expect(mapCollectionStatusToAvailability("on_loan")).toBe("https://schema.org/LimitedAvailability");
    });

    it("maps damaged or lost statuses to OutOfStock", () => {
      expect(mapCollectionStatusToAvailability("damaged")).toBe("https://schema.org/OutOfStock");
      expect(mapCollectionStatusToAvailability("lost")).toBe("https://schema.org/OutOfStock");
    });

    it("defaults to InStock for undefined or unknown statuses", () => {
      expect(mapCollectionStatusToAvailability(undefined)).toBe("https://schema.org/InStock");
      expect(mapCollectionStatusToAvailability("unknown_status")).toBe("https://schema.org/InStock");
    });
  });

  describe("buildOfferJsonLd", () => {
    it("constructs standard offer with default seller and price", () => {
      const offer = buildOfferJsonLd({ status: "owned" });
      expect(offer).toEqual({
        "@type": "Offer",
        availability: "https://schema.org/InStock",
        itemCondition: "https://schema.org/UsedCondition",
        price: "0",
        priceCurrency: "USD",
        seller: {
          "@type": "Organization",
          name: "iqoqo Library",
        },
      });
    });

    it("allows custom price, currency, and seller", () => {
      const offer = buildOfferJsonLd({
        status: "for_sale",
        price: 25.5,
        currency: "EUR",
        sellerName: "Alice Bookstore",
      });
      expect(offer["price"]).toBe("25.5");
      expect(offer["priceCurrency"]).toBe("EUR");
      expect((offer["seller"] as any)?.name).toBe("Alice Bookstore");
    });
  });

  describe("buildManifestationJsonLd", () => {
    it("builds a complete Manifestation JSON-LD payload", () => {
      const jsonLd = buildManifestationJsonLd({
        id: 42,
        title: "The Hobbit",
        authors: ["J.R.R. Tolkien"],
        coverUrl: "https://example.com/cover.jpg",
        isbn: "9780261102217",
        publisher: "George Allen & Unwin",
        datePublished: 1937,
        language: "eng",
        contentType: "book",
        offers: [{ status: "owned" }],
      });

      expect(jsonLd["@context"]).toBe("https://schema.org");
      expect(jsonLd["@type"]).toBe("Book");
      expect(jsonLd["name"]).toBe("The Hobbit");
      expect(jsonLd["identifier"]).toBe(42);
      expect(jsonLd["image"]).toBe("https://example.com/cover.jpg");
      expect(jsonLd["isbn"]).toBe("9780261102217");
      expect(jsonLd["publisher"]).toBe("George Allen & Unwin");
      expect(jsonLd["datePublished"]).toBe(1937);
      expect(jsonLd["inLanguage"]).toBe("en");
      expect(Array.isArray(jsonLd["offers"])).toBe(true);
      expect((jsonLd["offers"] as any[])[0]["availability"]).toBe("https://schema.org/InStock");
    });
  });

  describe("buildCollectionJsonLd", () => {
    it("builds CollectionPage with ItemList", () => {
      const jsonLd = buildCollectionJsonLd({
        name: "My Rare Books",
        description: "Curated 1st editions",
        totalCount: 2,
        authorName: "Sebastian",
        items: [
          { id: 1, title: "Book 1", url: "https://example.com/manifestation/1", contentType: "book" },
          { id: 2, title: "Game 1", url: "https://example.com/manifestation/2", contentType: "board_game" },
        ],
      });

      expect(jsonLd["@context"]).toBe("https://schema.org");
      expect(jsonLd["@type"]).toBe("CollectionPage");
      expect(jsonLd["name"]).toBe("My Rare Books");
      expect(jsonLd["numberOfItems"]).toBe(2);
      expect((jsonLd["author"] as any)?.name).toBe("Sebastian");

      const mainEntity = jsonLd["mainEntity"] as any;
      expect(mainEntity["@type"]).toBe("ItemList");
      expect(mainEntity["numberOfItems"]).toBe(2);
      expect(mainEntity["itemListElement"]).toHaveLength(2);
      expect(mainEntity["itemListElement"][0]["item"]["@type"]).toBe("Book");
      expect(mainEntity["itemListElement"][1]["item"]["@type"]).toBe("Game");
    });
  });

  describe("buildWorkJsonLd", () => {
    it("builds CreativeWork with workExample manifestations", () => {
      const jsonLd = buildWorkJsonLd({
        id: 101,
        title: "Dune",
        authors: ["Frank Herbert"],
        manifestations: [
          {
            id: 201,
            title: "Dune (Hardcover 1965)",
            isbn: "9780441172719",
            language: "eng",
            contentType: "book",
            year: 1965,
          },
          {
            id: 202,
            title: "Dune (Audiobook)",
            language: "eng",
            contentType: "audiobook",
            year: 2006,
          },
        ],
      });

      expect(jsonLd["@context"]).toBe("https://schema.org");
      expect(jsonLd["@type"]).toBe("CreativeWork");
      expect(jsonLd["name"]).toBe("Dune");
      expect((jsonLd["author"] as any)?.name).toBe("Frank Herbert");
      expect(jsonLd["identifier"]).toBe(101);

      const examples = jsonLd["workExample"] as any[];
      expect(examples).toHaveLength(2);
      expect(examples[0]["@type"]).toBe("Book");
      expect(examples[0]["isbn"]).toBe("9780441172719");
      expect(examples[0]["inLanguage"]).toBe("en");
      expect(examples[1]["@type"]).toBe("Audiobook");
    });
  });
});
