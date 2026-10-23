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

import React, { useState } from "react";
import Link from "next/link";
import { Navbar } from "@/components/dashboard/navbar";
import { Footer } from "@/components/dashboard/footer";
import { HELP_ARTICLES, HelpArticle } from "@/lib/help-articles";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Search, ArrowRight, Layers, ScanLine, Share2, Shield, Wrench } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

/**
 * Help and documentation hub page rendering guide search and category navigation.
 *
 * @returns {JSX.Element} The rendered help hub page.
 */
export default function HelpHubPage() {
  const t = useTranslations("HelpHub");
  const rawLocale = useLocale();
  const locale = (rawLocale === "pl" ? "pl" : "en") as "en" | "pl";
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const categories: Array<HelpArticle["category"]> = ["cataloging", "tools", "privacy", "federation", "curation"];

  const filteredArticles = HELP_ARTICLES.filter(article => {
    const matchesCategory = selectedCategory === "all" || article.category === selectedCategory;
    const title = article.title[locale].toLowerCase();
    const desc = article.description[locale].toLowerCase();
    const query = searchTerm.toLowerCase();
    const matchesSearch = title.includes(query) || desc.includes(query);
    return matchesCategory && matchesSearch;
  });

  const getCategoryIcon = (category: HelpArticle["category"]) => {
    switch (category) {
      case "cataloging":
        return <Layers className="h-3.5 w-3.5 text-primary" />;
      case "tools":
        return <ScanLine className="h-3.5 w-3.5 text-emerald-500" />;
      case "privacy":
        return <Shield className="h-3.5 w-3.5 text-amber-500" />;
      case "federation":
        return <Share2 className="h-3.5 w-3.5 text-indigo-500" />;
      case "curation":
        return <Wrench className="h-3.5 w-3.5 text-purple-500" />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <BookOpen className="h-8 w-8 text-primary" />
            <h1 className="text-3xl font-serif font-bold tracking-tight">{t("title")}</h1>
          </div>
          <p className="text-muted-foreground mt-2 max-w-2xl">{t("description")}</p>
        </div>

        {/* Search & Category Filter Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 mb-8">
          <div className="relative max-w-md w-full">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder={t("searchPlaceholder")}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="h-9 w-full rounded-md border border-input bg-transparent pl-9 pr-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          {/* Category Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <button
              type="button"
              onClick={() => setSelectedCategory("all")}
              className={`px-3 py-1.5 rounded-full border transition-colors ${
                selectedCategory === "all"
                  ? "bg-primary text-primary-foreground border-primary font-medium"
                  : "bg-muted/50 text-muted-foreground border-border hover:bg-muted hover:text-foreground"
              }`}
            >
              {t("filterAll")}
            </button>
            {categories.map(cat => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full border transition-colors ${
                  selectedCategory === cat
                    ? "bg-primary text-primary-foreground border-primary font-medium"
                    : "bg-muted/50 text-muted-foreground border-border hover:bg-muted hover:text-foreground"
                }`}
              >
                {getCategoryIcon(cat)}
                <span>{t(`categories.${cat}`)}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Articles Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredArticles.map(article => (
            <Link key={article.slug} href={`/help/${article.slug}`} className="group">
              <Card className="h-full hover:border-primary/50 transition-all group-hover:shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="outline" className="gap-1.5 capitalize text-xs">
                      {getCategoryIcon(article.category)}
                      {t(`categories.${article.category}`)}
                    </Badge>
                  </div>
                  <CardTitle className="text-lg font-semibold group-hover:text-primary transition-colors flex items-center justify-between">
                    <span>{article.title[locale]}</span>
                    <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity transform group-hover:translate-x-1" />
                  </CardTitle>
                  <CardDescription className="text-sm mt-1 leading-relaxed">
                    {article.description[locale]}
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>

        {filteredArticles.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <BookOpen className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>{t("noArticlesFound")}</p>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
