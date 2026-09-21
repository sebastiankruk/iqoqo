# 🔍 Tutorial: SPARQL Queries on Your Collection

Learn how to query your iqoqo library using SPARQL — the standard query language for the Semantic Web.

## 🎯 Learning Objectives

By the end of this tutorial, you will be able to:

- Execute SPARQL queries against your iqoqo collection
- Use SELECT queries to find specific books, authors, and formats
- Write CONSTRUCT queries to build custom RDF sub-graphs
- Understand SPARQL result formats and content negotiation
- Apply resource limit awareness to write efficient queries

## 📋 Prerequisites

- A running iqoqo instance (see [Installation Guide](../INSTALL.md))
- At least a few items in your collection
- `curl` or a REST client (e.g., Postman, HTTPie)
- Basic familiarity with RDF concepts (helpful but not required)

## 🔐 Step 1: Get an Authentication Token

The SPARQL endpoint requires authentication. First, obtain a JWT token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"your_password"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])')

echo "Token: ${TOKEN:0:20}..."
```

## 📚 Step 2: Your First SPARQL Query

Let's list all works in your collection:

```bash
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode 'query=
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX frbr: <http://purl.org/vocab/frbr/core#>

SELECT ?title ?author
WHERE {
  ?work a frbr:Work ;
        dc:title ?title ;
        dc:creator ?author .
}
ORDER BY ?title
LIMIT 10' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/sparql-results+json"
```

**Expected Output:**

```json
{
  "head": { "vars": ["title", "author"] },
  "results": {
    "bindings": [
      {
        "title": { "type": "literal", "value": "The Hobbit" },
        "author": { "type": "literal", "value": "J.R.R. Tolkien" }
      },
      {
        "title": { "type": "literal", "value": "Dune" },
        "author": { "type": "literal", "value": "Frank Herbert" }
      }
    ]
  }
}
```

## 🎨 Step 3: Query by Format

Find all board games in your collection:

```bash
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode 'query=
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX schema: <https://schema.org/>
PREFIX frbr: <http://purl.org/vocab/frbr/core#>

SELECT ?title ?players
WHERE {
  ?work a frbr:Work ;
        dc:title ?title .
  ?expression frbr:expressionOf ?work .
  ?manifestation frbr:embodimentOf ?expression ;
        a schema:Game .
  OPTIONAL { ?manifestation schema:numberOfPlayers ?players }
}
ORDER BY ?title' \
  -H "Authorization: Bearer $TOKEN"
```

## 📊 Step 4: Aggregate Queries

Count your items by media type:

```bash
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode 'query=
PREFIX schema: <https://schema.org/>
PREFIX frbr: <http://purl.org/vocab/frbr/core#>

SELECT ?type (COUNT(?item) AS ?count)
WHERE {
  ?item a frbr:Item ;
        frbr:exemplarOf ?manifestation .
  ?manifestation a ?type .
  FILTER(?type != frbr:Manifestation)
}
GROUP BY ?type
ORDER BY DESC(?count)' \
  -H "Authorization: Bearer $TOKEN"
```

## 🏗️ Step 5: CONSTRUCT Queries

Build a custom sub-graph of books by a specific author:

```bash
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode 'query=
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX frbr: <http://purl.org/vocab/frbr/core#>
PREFIX schema: <https://schema.org/>

CONSTRUCT {
  ?work dc:title ?title ;
        dc:creator ?author ;
        schema:isbn ?isbn .
}
WHERE {
  ?work a frbr:Work ;
        dc:title ?title ;
        dc:creator ?author .
  ?expression frbr:expressionOf ?work .
  ?manifestation frbr:embodimentOf ?expression ;
        schema:isbn ?isbn .
  FILTER(CONTAINS(LCASE(?author), "tolkien"))
}' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/turtle"
```

**Expected Output (Turtle):**

```turtle
@prefix dc: <http://purl.org/dc/terms/> .
@prefix schema: <https://schema.org/> .

<https://iqoqo.cc/works/42> dc:title "The Hobbit" ;
    dc:creator "J.R.R. Tolkien" ;
    schema:isbn "9780547928227" .
```

## 🔄 Step 6: Content Negotiation

Try the same query in different formats:

```bash
# SPARQL JSON (default)
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode "query=SELECT * WHERE { ?s ?p ?o } LIMIT 3" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/sparql-results+json"

# CSV format
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode "query=SELECT * WHERE { ?s ?p ?o } LIMIT 3" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/csv"

# XML format
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode "query=SELECT * WHERE { ?s ?p ?o } LIMIT 3" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/sparql-results+xml"
```

## ⚡ Step 7: POST Requests

For complex queries, use POST with a JSON body:

```bash
curl -X POST http://localhost:8000/api/sparql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PREFIX dc: <http://purl.org/dc/terms/> PREFIX frbr: <http://purl.org/vocab/frbr/core#> SELECT ?title WHERE { ?work a frbr:Work ; dc:title ?title . } LIMIT 5"
  }'
```

## 🧪 Step 8: ASK Queries

Check if a specific work exists:

```bash
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode 'query=
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX frbr: <http://purl.org/vocab/frbr/core#>

ASK {
  ?work a frbr:Work ;
        dc:title "The Hobbit" .
}' \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Output:**

```json
{
  "head": {},
  "boolean": true
}
```

## ❓ Troubleshooting

### "Rate limit exceeded"

You've exceeded 10 queries per minute. Wait 60 seconds and try again.

### "Query too large"

Your query exceeds the 10KB limit. Simplify it or break it into multiple queries.

### "Timeout"

Your query exceeded the 15-second execution limit. Add `LIMIT` clauses or reduce the scope of your query.

### "Write rejected"

SPARQL endpoint is read-only. `INSERT`, `DELETE`, and `UPDATE` operations are not allowed.

### Empty results

- Verify you have items in your collection
- Check namespace prefixes are correct
- Try a simpler query first: `SELECT * WHERE { ?s ?p ?o } LIMIT 5`

## 📚 Next Steps

- **[Semantic Web Guide](../SEMANTIC_WEB.md)** — Full SPARQL documentation
- **[API Reference](../API.md)** — Endpoint details and error codes
- **[Linked Data Integration Tutorial](linked-data-integration.md)** — Consuming Linked Data from iqoqo
