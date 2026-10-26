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

import React from "react";
import Link from "next/link";
import { useParams, notFound } from "next/navigation";
import { Navbar } from "@/components/dashboard/navbar";
import { Footer } from "@/components/dashboard/footer";
import { HELP_ARTICLES } from "@/lib/help-articles";
import { RichText } from "@/components/ui/rich-text";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

/**
 * Help article detail page rendering markdown documentation with locale support.
 *
 * @returns {JSX.Element} The rendered help article detail page.
 */
export default function HelpArticleDetailPage() {
  const t = useTranslations("HelpHub");
  const rawLocale = useLocale();
  const locale = (rawLocale === "pl" ? "pl" : "en") as "en" | "pl";
  const params = useParams();
  const slug = params?.slug as string;

  const article = HELP_ARTICLES.find(a => a.slug === slug);
  if (!article) {
    notFound();
  }

  const rawContent = article.content[locale];
  // Strip redundant leading H1 title if present in markdown content
  const content = rawContent.replace(/^#\s+[^\n]+\n+/, "");

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8">
        <div className="mb-6">
          <Button variant="ghost" size="sm" asChild className="gap-2 text-muted-foreground hover:text-foreground mb-4">
            <Link href="/help">
              <ArrowLeft className="h-4 w-4" />
              {t("backToHub")}
            </Link>
          </Button>

          <div className="flex items-center gap-2 mb-2">
            <Badge variant="outline" className="capitalize text-xs">
              {t(`categories.${article.category}`)}
            </Badge>
          </div>
          <h1 className="text-3xl sm:text-4xl font-serif font-bold tracking-tight">{article.title[locale]}</h1>
          <p className="text-muted-foreground text-lg mt-2 leading-relaxed">{article.description[locale]}</p>
        </div>

        <div className="border-t border-border pt-6">
          <article className="prose dark:prose-invert max-w-none">
            <RichText content={content} />
          </article>
        </div>
      </main>
      <Footer />
    </div>
  );
}
