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
import { WorkStructuredData } from "@/components/work/work-structured-data";

describe("WorkStructuredData Component (Schema.org CreativeWork)", () => {
  it("renders a valid CreativeWork JSON-LD script tag modeling FRBR hierarchy", () => {
    const workData = {
      id: 501,
      title: "The Left Hand of Darkness",
      authors: ["Ursula K. Le Guin"],
      manifestations: [
        {
          id: 1001,
          title: "The Left Hand of Darkness (Ace Books)",
          isbn: "9780441478125",
          language: "eng",
          contentType: "book",
          year: 1969,
        },
        {
          id: 1002,
          title: "The Left Hand of Darkness (Audiobook)",
          language: "eng",
          contentType: "audiobook",
          year: 2018,
        },
      ],
    };

    const { container } = render(<WorkStructuredData data={workData} />);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();

    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    expect(jsonLd["@type"]).toBe("CreativeWork");
    expect(jsonLd["name"]).toBe("The Left Hand of Darkness");
    expect(jsonLd["author"]["name"]).toBe("Ursula K. Le Guin");
    expect(jsonLd["identifier"]).toBe(501);

    const workExamples = jsonLd["workExample"] as any[];
    expect(Array.isArray(workExamples)).toBe(true);
    expect(workExamples).toHaveLength(2);

    expect(workExamples[0]["@type"]).toBe("Book");
    expect(workExamples[0]["name"]).toBe("The Left Hand of Darkness (Ace Books)");
    expect(workExamples[0]["isbn"]).toBe("9780441478125");
    expect(workExamples[0]["inLanguage"]).toBe("en");
    expect(workExamples[0]["datePublished"]).toBe(1969);

    expect(workExamples[1]["@type"]).toBe("Audiobook");
    expect(workExamples[1]["name"]).toBe("The Left Hand of Darkness (Audiobook)");
    expect(workExamples[1]["inLanguage"]).toBe("en");
    expect(workExamples[1]["datePublished"]).toBe(2018);
  });

  it("handles work without manifestations gracefully", () => {
    const workData = {
      id: 99,
      title: "Solitary Work",
      authors: ["Anonymous"],
    };

    const { container } = render(<WorkStructuredData data={workData} />);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();

    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    expect(jsonLd["@type"]).toBe("CreativeWork");
    expect(jsonLd["name"]).toBe("Solitary Work");
    expect(jsonLd["workExample"]).toBeUndefined();
  });
});
