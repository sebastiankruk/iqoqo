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
/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { RichText, decodeHtmlEntities, containsHtmlTags, sanitizeRichHtml } from "@/components/ui/rich-text";

describe("RichText helper functions", () => {
  it("decodes single and double encoded HTML entities", () => {
    expect(decodeHtmlEntities("&lt;p&gt;Hello&lt;/p&gt;")).toBe("<p>Hello</p>");
    expect(decodeHtmlEntities("&amp;lt;b&amp;gt;World&amp;lt;/b&amp;gt;")).toBe("<b>World</b>");
    expect(decodeHtmlEntities("Tom &amp; Jerry")).toBe("Tom & Jerry");
    expect(decodeHtmlEntities("&#39;quotes&#39;")).toBe("'quotes'");
  });

  it("identifies presence of HTML tags", () => {
    expect(containsHtmlTags("<p>Hello</p>")).toBe(true);
    expect(containsHtmlTags("<b>Bold</b>")).toBe(true);
    expect(containsHtmlTags("Just plain text with 5 < 10")).toBe(false);
    expect(containsHtmlTags("**Markdown only**")).toBe(false);
  });

  it("sanitizes HTML and neutralizes XSS payloads", () => {
    const dirty = '<p>Safe</p><script>alert("xss")</script><img src="x" onerror="alert(1)">';
    const clean = sanitizeRichHtml(dirty);
    expect(clean).toContain("<p>Safe</p>");
    expect(clean).not.toContain("<script>");
    expect(clean).not.toContain("onerror");
  });
});

describe("RichText component", () => {
  it("renders null when content is empty or undefined", () => {
    const { container: c1 } = render(<RichText content="" />);
    expect(c1.firstChild).toBeNull();

    const { container: c2 } = render(<RichText content={null} />);
    expect(c2.firstChild).toBeNull();

    const { container: c3 } = render(<RichText content="   " />);
    expect(c3.firstChild).toBeNull();
  });

  it("renders markdown syntax formatted correctly", () => {
    render(<RichText content="**Strong Text** and *Italic Text*" />);
    const strong = screen.getByText("Strong Text");
    expect(strong.tagName).toBe("STRONG");
    const italic = screen.getByText("Italic Text");
    expect(italic.tagName).toBe("EM");
  });

  it("renders HTML markup safely", () => {
    render(<RichText content="<p>Paragraph text with <b>bold</b> words.</p>" />);
    const bold = screen.getByText("bold");
    expect(bold.tagName).toBe("B");
    expect(screen.getByText(/Paragraph text with/)).toBeInTheDocument();
  });

  it("neutralizes dangerous script injection", () => {
    const { container } = render(<RichText content="<p>Valid text</p><script>window.pwned = true;</script>" />);
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByText("Valid text")).toBeInTheDocument();
  });

  it("enforces safe link attributes (rel=noopener noreferrer, target=_blank)", () => {
    const { container } = render(<RichText content='<p>Read more at <a href="https://iqoqo.cc">iqoqo</a></p>' />);
    const link = container.querySelector("a");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("target")).toBe("_blank");
    expect(link?.getAttribute("rel")).toContain("noopener");
    expect(link?.getAttribute("rel")).toContain("noreferrer");
  });

  it("correctly renders test fixture representing item 2027 with double-encoded entities", () => {
    // Reproduction fixture for item 2027:
    // API returns raw double-encoded & entity-encoded tags: &lt;p&gt;...&amp;lt;b&amp;gt;...
    const item2027Description =
      "&lt;p&gt;Przewodnik encyklopedyczny po &amp;lt;b&amp;gt;dziejach sztuki&amp;lt;/b&amp;gt; polskiej.&lt;/p&gt;";

    const { container } = render(<RichText content={item2027Description} />);

    // Should NOT show raw &lt;p&gt; or <p> as text strings
    expect(container.textContent).not.toContain("&lt;p&gt;");
    expect(container.textContent).not.toContain("<p>");

    // Should render real DOM elements <p> and <b>
    const p = container.querySelector("p");
    expect(p).not.toBeNull();
    const b = container.querySelector("b");
    expect(b).not.toBeNull();
    expect(b?.textContent).toBe("dziejach sztuki");
  });
});
