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

import { useState } from "react";
import { Play, Download, Loader2, Clock, ChevronLeft, ChevronRight, FileSpreadsheet, FileJson } from "lucide-react";
import Link from "next/link";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { useProfile } from "@/lib/api/hooks";
import { PermissionName } from "@/lib/permissions";

const EXAMPLE_QUERIES = [
  {
    label: "All Works",
    query: `SELECT ?work ?title ?author
WHERE {
  ?work a <http://iflastandards.info/ns/frbr/frbrer/Work> .
  OPTIONAL { ?work <https://schema.org/name> ?title } .
  OPTIONAL { ?work <https://schema.org/author> ?author } .
}
LIMIT 50`,
  },
  {
    label: "Manifestations by format",
    query: `SELECT ?manif ?title ?isbn
WHERE {
  ?manif a <http://iflastandards.info/ns/frbr/frbrer/Manifestation> .
  OPTIONAL { ?manif <https://schema.org/name> ?title } .
  OPTIONAL { ?manif <https://schema.org/isbn> ?isbn } .
}
LIMIT 50`,
  },
  {
    label: "Recent Items",
    query: `SELECT ?item ?status
WHERE {
  ?item a <http://iflastandards.info/ns/frbr/frbrer/Item> .
  OPTIONAL { ?item <https://schema.org/itemCondition> ?status } .
}
LIMIT 50`,
  },
  {
    label: "All triples (limited)",
    query: `SELECT ?s ?p ?o
WHERE { ?s ?p ?o }
LIMIT 50`,
  },
  {
    label: "CONSTRUCT - Full graph (limited)",
    query: `CONSTRUCT { ?s ?p ?o }
WHERE { ?s ?p ?o }
LIMIT 100`,
  },
];

interface SPARQLBinding {
  [key: string]: { type: string; value: string; datatype?: string; "xml:lang"?: string };
}

interface SPARQLResults {
  head: { vars: string[] };
  results: { bindings: SPARQLBinding[] };
}

const PAGE_SIZE = 25;

/**
 * SPARQL Explorer Page component.
 * Allows administrators and custodians to query the FRBR/Schema.org RDF graph using SPARQL.
 *
 * @returns The SPARQL Explorer Page component UI.
 */
export default function SPARQLExplorerPage() {
  const { data: profile, isLoading } = useProfile();
  const [query, setQuery] = useState(EXAMPLE_QUERIES[0].query);
  const [results, setResults] = useState<SPARQLResults | null>(null);
  const [rawOutput, setRawOutput] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const permissions = profile?.permissions ?? [];
  const roles = profile?.roles ?? [];
  const hasPermission = (perm: PermissionName): boolean => permissions.includes(perm);
  const canAccessSparql =
    roles.includes("admin") ||
    roles.includes("contributor") ||
    hasPermission(PermissionName.READ_METADATA) ||
    hasPermission(PermissionName.WRITE_METADATA);

  const executeQuery = async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    setRawOutput(null);
    setLatencyMs(null);
    setCurrentPage(1);

    const startTime = performance.now();

    try {
      const isConstruct = /^\s*(CONSTRUCT|DESCRIBE)/i.test(query);

      const response = await apiClient.post(
        "/sparql",
        { query },
        {
          headers: {
            Accept: isConstruct ? "text/turtle" : "application/sparql-results+json",
          },
          // Don't parse response as JSON for CONSTRUCT
          ...(isConstruct ? { responseType: "text", transformResponse: [(data: string) => data] } : {}),
        }
      );

      const endTime = performance.now();
      setLatencyMs(Math.round(endTime - startTime));

      if (isConstruct) {
        setRawOutput(typeof response.data === "string" ? response.data : JSON.stringify(response.data));
      } else {
        setResults(response.data as SPARQLResults);
      }
    } catch (err: unknown) {
      const endTime = performance.now();
      setLatencyMs(Math.round(endTime - startTime));
      const axiosErr = err as { response?: { data?: { error?: string } }; message?: string };
      setError(axiosErr.response?.data?.error || axiosErr.message || "Query execution failed");
    } finally {
      setLoading(false);
    }
  };

  const downloadJSON = () => {
    if (!results) return;
    const content = JSON.stringify(results, null, 2);
    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sparql_results.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadCSV = () => {
    if (!results) return;
    const vars = results.head.vars;
    const rows = results.results.bindings.map(b =>
      vars
        .map(v => {
          const val = b[v]?.value ?? "";
          return `"${val.replace(/"/g, '""')}"`;
        })
        .join(",")
    );
    const csvContent = [vars.join(","), ...rows].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sparql_results.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadTurtle = () => {
    if (!rawOutput) return;
    const blob = new Blob([rawOutput], { type: "text/turtle" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sparql_results.ttl";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading || !profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
      </div>
    );
  }

  if (!canAccessSparql) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-4">
          <h1 className="text-2xl font-bold">Access Denied</h1>
          <p className="text-muted-foreground max-w-md">
            You need custodian permissions to access the SPARQL Explorer.
          </p>
          <Button asChild>
            <Link href="/dashboard">Back to Dashboard</Link>
          </Button>
        </div>
        <Footer />
      </div>
    );
  }

  const bindings = results?.results.bindings ?? [];
  const totalRows = bindings.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / PAGE_SIZE));
  const paginatedBindings = bindings.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <div className="flex-1 mx-auto w-full max-w-6xl px-6 py-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold">SPARQL Explorer</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Query the library catalog using SPARQL over the FRBR/Schema.org RDF graph.
            </p>
          </div>
          <Button variant="outline" asChild>
            <Link href="/admin/content">Back to Custodians</Link>
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Example queries sidebar */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Example Queries</CardTitle>
              <CardDescription className="text-xs">Click to load query template</CardDescription>
            </CardHeader>
            <CardContent className="space-y-1">
              {EXAMPLE_QUERIES.map(ex => (
                <button
                  key={ex.label}
                  onClick={() => setQuery(ex.query)}
                  className="block w-full text-left px-2 py-1.5 text-xs rounded hover:bg-muted transition-colors"
                >
                  {ex.label}
                </button>
              ))}
            </CardContent>
          </Card>

          {/* Query editor + results */}
          <div className="lg:col-span-3 space-y-4">
            <Card>
              <CardContent className="pt-4">
                <textarea
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  className="w-full h-40 font-mono text-sm p-3 border rounded-md bg-muted/30 resize-y focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Enter SPARQL query..."
                  spellCheck={false}
                />
                <div className="flex flex-wrap items-center justify-between gap-2 mt-3">
                  <div className="flex items-center gap-2">
                    <Button onClick={executeQuery} disabled={loading || !query.trim()} size="sm">
                      {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Play className="h-4 w-4 mr-1" />}
                      Execute
                    </Button>
                    {latencyMs !== null && (
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground font-mono">
                        <Clock className="h-3 w-3" />
                        {latencyMs}ms
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {results && (
                      <>
                        <Button variant="outline" onClick={downloadCSV} size="sm">
                          <FileSpreadsheet className="h-4 w-4 mr-1" />
                          Download CSV
                        </Button>
                        <Button variant="outline" onClick={downloadJSON} size="sm">
                          <FileJson className="h-4 w-4 mr-1" />
                          Download JSON
                        </Button>
                      </>
                    )}
                    {rawOutput && (
                      <Button variant="outline" onClick={downloadTurtle} size="sm">
                        <Download className="h-4 w-4 mr-1" />
                        Download Turtle
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {error && (
              <Card className="border-destructive">
                <CardContent className="pt-4">
                  <p className="text-sm text-destructive font-mono">{error}</p>
                </CardContent>
              </Card>
            )}

            {results && (
              <Card>
                <CardHeader className="pb-2 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-sm">Results ({totalRows} rows)</CardTitle>
                    <CardDescription className="text-xs">
                      Showing {totalRows > 0 ? (currentPage - 1) * PAGE_SIZE + 1 : 0} to{" "}
                      {Math.min(currentPage * PAGE_SIZE, totalRows)} of {totalRows}
                    </CardDescription>
                  </div>
                  {totalPages > 1 && (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        disabled={currentPage === 1}
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <span className="text-xs text-muted-foreground font-mono">
                        {currentPage} / {totalPages}
                      </span>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        disabled={currentPage === totalPages}
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr className="border-b">
                          {results.head.vars.map(v => (
                            <th key={v} className="text-left p-2 font-semibold">
                              ?{v}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedBindings.map((binding, i) => (
                          <tr key={i} className="border-b last:border-0 hover:bg-muted/30">
                            {results.head.vars.map(v => (
                              <td key={v} className="p-2 max-w-xs truncate" title={binding[v]?.value}>
                                {binding[v]?.value || ""}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {rawOutput && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">RDF Output</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs font-mono bg-muted/30 p-3 rounded overflow-x-auto max-h-96">{rawOutput}</pre>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
