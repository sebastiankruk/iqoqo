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
import { Play, Download, Loader2 } from "lucide-react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";

const EXAMPLE_QUERIES = [
  {
    label: "All works with authors",
    query: `SELECT ?work ?title ?author
WHERE {
  ?work a <http://iflastandards.info/ns/frbr/frbrer/Work> .
  ?manif <https://schema.org/name> ?title .
  ?manif <https://schema.org/author> ?author .
}`,
  },
  {
    label: "Items with ISBN",
    query: `SELECT ?manif ?title ?isbn
WHERE {
  ?manif a <http://iflastandards.info/ns/frbr/frbrer/Manifestation> .
  ?manif <https://schema.org/name> ?title .
  ?manif <https://schema.org/isbn> ?isbn .
}`,
  },
  {
    label: "All triples (limited)",
    query: `SELECT ?s ?p ?o
WHERE { ?s ?p ?o }
LIMIT 50`,
  },
  {
    label: "Items by status",
    query: `SELECT ?item ?status
WHERE {
  ?item a <http://iflastandards.info/ns/frbr/frbrer/Item> .
  ?item <https://schema.org/itemCondition> ?status .
}`,
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

export default function SPARQLExplorerPage() {
  const [query, setQuery] = useState(EXAMPLE_QUERIES[0].query);
  const [results, setResults] = useState<SPARQLResults | null>(null);
  const [rawOutput, setRawOutput] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const executeQuery = async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    setRawOutput(null);

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

      if (isConstruct) {
        setRawOutput(typeof response.data === "string" ? response.data : JSON.stringify(response.data));
      } else {
        setResults(response.data as SPARQLResults);
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { error?: string } }; message?: string };
      setError(axiosErr.response?.data?.error || axiosErr.message || "Query execution failed");
    } finally {
      setLoading(false);
    }
  };

  const downloadResults = () => {
    const content = rawOutput || JSON.stringify(results, null, 2);
    const blob = new Blob([content], { type: rawOutput ? "text/turtle" : "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = rawOutput ? "sparql_results.ttl" : "sparql_results.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <div className="flex-1 mx-auto w-full max-w-6xl px-6 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">SPARQL Explorer</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Query your collection using SPARQL over the FRBR/Schema.org RDF graph.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Example queries sidebar */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Example Queries</CardTitle>
              <CardDescription className="text-xs">Click to load</CardDescription>
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
                <div className="flex gap-2 mt-3">
                  <Button onClick={executeQuery} disabled={loading || !query.trim()} size="sm">
                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Play className="h-4 w-4 mr-1" />}
                    Execute
                  </Button>
                  {(results || rawOutput) && (
                    <Button variant="outline" onClick={downloadResults} size="sm">
                      <Download className="h-4 w-4 mr-1" />
                      Download
                    </Button>
                  )}
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
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Results ({results.results.bindings.length} rows)</CardTitle>
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
                        {results.results.bindings.map((binding, i) => (
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
