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
"use client";

import React, { useMemo } from "react";
import DOMPurify from "dompurify";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

export interface RichTextProps {
  content?: string | null;
  className?: string;
}

const ALLOWED_TAGS = [
  "b",
  "i",
  "em",
  "strong",
  "u",
  "p",
  "br",
  "ul",
  "ol",
  "li",
  "code",
  "pre",
  "blockquote",
  "a",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "table",
  "thead",
  "tbody",
  "tr",
  "th",
  "td",
  "hr",
];

const ALLOWED_ATTR = ["href", "target", "rel", "title"];

let hookConfigured = false;

/**
 * Obtain DOMPurify instance configured with safe attribute hooks.
 *
 * @returns {typeof DOMPurify | null} Configured DOMPurify instance or null on server.
 */
function getPurifier() {
  if (typeof window === "undefined") {
    return null;
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const purify = typeof DOMPurify.sanitize === "function" ? DOMPurify : (DOMPurify as any)(window);
  if (purify && !hookConfigured && typeof purify.addHook === "function") {
    purify.addHook("afterSanitizeAttributes", (node: Element) => {
      if (node.tagName === "A") {
        node.setAttribute("target", "_blank");
        node.setAttribute("rel", "noopener noreferrer");
      }
    });
    hookConfigured = true;
  }
  return purify;
}

/**
 * Safely decodes HTML entities (e.g., &lt; to <, &amp; to &), handling up to
 * two decoding passes for double-encoded entities delivered by external APIs.
 *
 * @param raw - The raw text containing encoded HTML entities.
 * @returns Decoded text string.
 */
export function decodeHtmlEntities(raw: string): string {
  let decoded = raw;
  for (let pass = 0; pass < 2; pass++) {
    const next = decoded
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#0*39;/g, "'")
      .replace(/&apos;/g, "'")
      .replace(/&#0*47;/g, "/")
      .replace(/&#x0*2[fF];/g, "/")
      .replace(/&nbsp;/g, " ")
      .replace(/&#(\d+);/g, (match, num) => {
        const code = parseInt(num, 10);
        return code > 0 && code < 65536 ? String.fromCharCode(code) : match;
      })
      .replace(/&#x([0-9a-fA-F]+);/g, (match, hex) => {
        const code = parseInt(hex, 16);
        return code > 0 && code < 65536 ? String.fromCharCode(code) : match;
      });
    if (next === decoded) break;
    decoded = next;
  }
  return decoded;
}

/**
 * Sanitizes an HTML string using DOMPurify with strict tag and attribute whitelists.
 * When window or DOMPurify context is unavailable (SSR), strips all HTML tags to prevent XSS.
 *
 * @param dirty - Unsanitized HTML string.
 * @returns Sanitized safe HTML string.
 */
export function sanitizeRichHtml(dirty: string): string {
  const purify = getPurifier();
  if (!purify) {
    // During SSR or when window/DOMPurify context is unavailable, strip scripts and styles
    // including their contents, strip HTML tags, and entity-encode any residual markup characters.
    let clean = dirty.replace(/<script[\s\S]*?<\/script>/gi, "").replace(/<style[\s\S]*?<\/style>/gi, "");

    clean = clean.replace(/<[^>]*>/g, "");
    clean = clean.replace(/</g, "&lt;").replace(/>/g, "&gt;");

    return clean;
  }

  return purify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ADD_ATTR: ["target", "rel"],
  });
}

/**
 * Checks whether text contains HTML tags.
 *
 * @param text - Input text string.
 * @returns True if text contains HTML elements.
 */
export function containsHtmlTags(text: string): boolean {
  return /<[a-z][\s\S]*>/i.test(text);
}

/**
 * Unified component for rendering rich descriptions across iqoqo views.
 * Handles entity-decoded HTML, DOMPurify sanitization, and Markdown formatting.
 *
 * @param props - Component properties.
 * @param props.content - Markdown or HTML string content.
 * @param props.className - Additional CSS classes.
 * @returns Rendered JSX Element.
 */
export function RichText({ content, className }: RichTextProps) {
  const processed = useMemo(() => {
    if (!content || !content.trim()) return null;

    const decoded = decodeHtmlEntities(content);
    const hasHtml = containsHtmlTags(decoded);

    if (hasHtml) {
      const sanitized = sanitizeRichHtml(decoded);
      return { type: "html" as const, value: sanitized };
    }

    return { type: "markdown" as const, value: decoded };
  }, [content]);

  if (!processed) return null;

  const baseClassName = cn("prose prose-sm dark:prose-invert max-w-none break-words", className);

  if (processed.type === "html") {
    return <div className={baseClassName} dangerouslySetInnerHTML={{ __html: processed.value }} />;
  }

  return (
    <div className={baseClassName}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          img: ({ ...imgProps }) => (
            <span className="my-6 block overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img {...imgProps} alt={imgProps.alt || "Guide illustration"} className="w-full object-cover" />
              {imgProps.alt && (
                <span className="block border-t border-border/40 px-3 py-2 text-center text-xs text-muted-foreground italic">
                  {imgProps.alt}
                </span>
              )}
            </span>
          ),
          table: ({ ...tableProps }) => (
            <div className="my-6 w-full overflow-x-auto rounded-lg border border-border">
              <table {...tableProps} className="w-full border-collapse text-left text-xs sm:text-sm" />
            </div>
          ),
          th: ({ ...thProps }) => (
            <th {...thProps} className="bg-muted px-4 py-2.5 font-semibold text-foreground border-b border-border" />
          ),
          td: ({ ...tdProps }) => (
            <td {...tdProps} className="px-4 py-2 border-b border-border/60 text-muted-foreground" />
          ),
        }}
      >
        {processed.value}
      </ReactMarkdown>
    </div>
  );
}

export default RichText;
