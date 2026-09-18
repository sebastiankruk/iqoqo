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
import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ExpressionStructuredData } from "@/components/expression/expression-structured-data";

describe("ExpressionStructuredData Component (Schema.org CreativeWork)", () => {
  it("renders a valid CreativeWork JSON-LD script tag modeling FRBR Expression", () => {
    const exprData = {
      id: 2062,
      workId: 1993,
      workTitle: "The Singles 1992 - 2003",
      authors: ["No Doubt"],
      language: "eng",
      contentType: "music",
      manifestations: [
        {
          id: 2053,
          title: "The Singles 1992 - 2003 (CD)",
          isbn: "602498613818",
          language: "eng",
          contentType: "music",
          year: 2003,
        },
      ],
    };

    const { container } = render(<ExpressionStructuredData data={exprData} />);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();

    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    expect(jsonLd["@type"]).toBe("CreativeWork");
    expect(jsonLd["name"]).toContain("The Singles 1992 - 2003");
    expect(jsonLd["author"]["name"]).toBe("No Doubt");
    expect(jsonLd["identifier"]).toBe(2062);
    expect(jsonLd["isPartOf"]["identifier"]).toBe(1993);
    expect(jsonLd["isPartOf"]["url"]).toBe("/work/1993");

    const workExamples = jsonLd["workExample"] as any[];
    expect(Array.isArray(workExamples)).toBe(true);
    expect(workExamples).toHaveLength(1);
    expect(workExamples[0]["@type"]).toBe("MusicAlbum");
    expect(workExamples[0]["name"]).toBe("The Singles 1992 - 2003 (CD)");
  });
});
