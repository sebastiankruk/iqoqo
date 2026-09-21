# 🔗 Tutorial: Linked Data Integration

Learn how to consume iqoqo's Linked Data endpoints from external applications, AI agents, and search engines.

## 🎯 Learning Objectives

By the end of this tutorial, you will be able to:

- Fetch FRBR entities as JSON-LD, Turtle, or N-Triples
- Use content negotiation to select RDF formats
- Traverse the FRBR hierarchy via Linked Data IRIs
- Integrate iqoqo data with AI agents and LLMs
- Consume RSS feeds for collection discovery
- Understand CORS headers for cross-origin access

## 📋 Prerequisites

- A running iqoqo instance with some public items (see [Installation Guide](../INSTALL.md))
- At least one user with `visibility: "public"` and non-hidden items
- `curl` or a programming language with HTTP client support
- Basic understanding of JSON-LD or Turtle (helpful but not required)

## 🌐 Step 1: Fetch Your First Linked Data Resource

Public endpoints don't require authentication. Fetch a Work entity:

```bash
# JSON-LD (default)
curl http://localhost:8000/api/public/works/1
```

**Expected Output:**

```json
{
  "@context": {
    "frbr": "http://purl.org/vocab/frbr/core#",
    "dc": "http://purl.org/dc/terms/",
    "schema": "https://schema.org/"
  },
  "@id": "https://iqoqo.cc/works/1",
  "@type": ["frbr:Work", "schema:CreativeWork"],
  "dc:title": "The Hobbit",
  "dc:creator": "J.R.R. Tolkien"
}
```

## 🔄 Step 2: Content Negotiation

Request the same resource in different formats:

```bash
# Turtle
curl -H "Accept: text/turtle" http://localhost:8000/api/public/works/1

# N-Triples
curl -H "Accept: application/n-triples" http://localhost:8000/api/public/works/1

# Via query parameter (alternative to Accept header)
curl "http://localhost:8000/api/public/works/1?format=turtle"
```

**Turtle Output:**

```turtle
@prefix frbr: <http://purl.org/vocab/frbr/core#> .
@prefix dc: <http://purl.org/dc/terms/> .
@prefix schema: <https://schema.org/> .

<https://iqoqo.cc/works/1> a frbr:Work, schema:CreativeWork ;
    dc:title "The Hobbit" ;
    dc:creator "J.R.R. Tolkien" .
```

## 🏗️ Step 3: Traverse the FRBR Hierarchy

Linked Data IRIs are dereferenceable — follow them to discover related entities.

### From Work to Expressions

```bash
# Get a Work (includes links to expressions)
curl -H "Accept: application/ld+json" http://localhost:8000/api/public/works/1 \
  | python3 -m json.tool
```

Look for `frbr:embodiment` or related expression IRIs in the response, then follow them:

```bash
# Follow an Expression IRI
curl -H "Accept: application/ld+json" http://localhost:8000/api/public/expressions/1
```

### From Expression to Manifestations

```bash
# Get a Manifestation (specific edition)
curl -H "Accept: application/ld+json" http://localhost:8000/api/public/manifestations/42
```

### From Manifestation to Items

```bash
# Get an Item (specific copy)
curl -H "Accept: application/ld+json" http://localhost:8000/api/public/items/7
```

## 🤖 Step 4: AI Agent Integration

AI agents and LLMs can consume iqoqo's Linked Data to answer questions about collections.

### Example: Ask an AI About a Collection

```bash
# Fetch a user's public collection as JSON-LD
COLLECTION=$(curl -s -H "Accept: application/ld+json" \
  "http://localhost:8000/api/public/u/alice/items?limit=50")

# Feed to an LLM prompt
echo "Here is Alice's library collection in JSON-LD format:
$COLLECTION

What types of media does Alice collect? What are the most common authors?"
```

### CORS for Browser-Based Agents

All public endpoints include open CORS headers, allowing browser-based AI agents to access data directly:

```javascript
// JavaScript example — fetch from a browser
const response = await fetch('http://iqoqo.example.com/api/public/works/1', {
  headers: { 'Accept': 'application/ld+json' }
});
const data = await response.json();
console.log(data['dc:title']); // "The Hobbit"
```

## 📡 Step 5: RSS Feed Discovery

Subscribe to collection feeds for real-time updates.

### Global Fresh Arrivals

```bash
curl http://localhost:8000/api/public/feed.xml
```

### User Collection Feed

```bash
curl http://localhost:8000/api/public/u/alice/feed.xml
```

### Shared Collection Feed

```bash
curl http://localhost:8000/api/public/share/TOKEN/feed.xml
```

### Feed with FRBR Level Filtering

```bash
# Works-level granularity
curl "http://localhost:8000/api/public/feed.xml?view=works"

# Expressions-level
curl "http://localhost:8000/api/public/feed.xml?view=expressions"

# Manifestations-level (default)
curl "http://localhost:8000/api/public/feed.xml?view=manifestations"
```

## 🗺️ Step 6: Sitemap for Search Engines

The XML sitemap lists all public entities for search engine indexing:

```bash
curl http://localhost:8000/api/public/sitemap.xml
```

Add to your `robots.txt`:

```text
Sitemap: https://iqoqo.cc/api/public/sitemap.xml
```

## 🔎 Step 7: Check If a User Has an Item

Use the "check if I have it" feature:

```bash
curl -X POST http://localhost:8000/api/public/u/alice/check \
  -H "Content-Type: application/json" \
  -d '{"query": "9780547928227"}'
```

**Response (item owned):**

```json
{
  "success": true,
  "data": [
    {
      "type": "item",
      "id": 42,
      "manifestation_id": 99,
      "title": "The Hobbit",
      "status": "available",
      "cover_url": "/static/covers/abc123.jpg"
    }
  ]
}
```

**Response (not owned, but in catalog):**

```json
{
  "success": true,
  "data": [
    {
      "type": "manifestation",
      "id": 99,
      "title": "The Hobbit",
      "publisher": "Mariner Books",
      "cover_url": "/static/covers/abc123.jpg"
    }
  ]
}
```

## 🐍 Step 8: Python Integration Example

```python
import requests

BASE = "http://localhost:8000/api/public"

# Fetch a work as JSON-LD
work = requests.get(f"{BASE}/works/1",
    headers={"Accept": "application/ld+json"}).json()

print(f"Title: {work.get('dc:title')}")
print(f"Author: {work.get('dc:creator')}")

# Fetch user collection
items = requests.get(f"{BASE}/u/alice/items",
    headers={"Accept": "application/ld+json"},
    params={"limit": 10}).json()

for item in items.get("@graph", []):
    print(f"  - {item.get('dc:title', 'Unknown')}")
```

## 🌍 Step 9: RDFlib Integration (Python)

Parse iqoqo's Turtle output with RDFlib:

```python
from rdflib import Graph

g = Graph()
g.parse("http://localhost:8000/api/public/works/1",
        format="turtle",
        headers={"Accept": "text/turtle"})

# Query the parsed graph
for s, p, o in g:
    print(f"{s} {p} {o}")
```

## ❓ Troubleshooting

### 404 Not Found

- The entity ID doesn't exist
- For items: the item may be hidden (`is_hidden: true`)
- For users: the user may not have `visibility: "public"`

### Empty JSON-LD Response

- Verify the user has non-hidden items
- Check that `limit` parameter is at least 1

### CORS Errors in Browser

- iqoqo public endpoints include `Access-Control-Allow-Origin: *`
- If you see CORS errors, check that you're hitting the public endpoint (`/api/public/...`), not an authenticated endpoint

### Wrong Format Returned

- Check your `Accept` header spelling
- Try the `?format=` query parameter as an alternative
- Default format is JSON-LD for public endpoints

## 📚 Next Steps

- **[Semantic Web Guide](../SEMANTIC_WEB.md)** — Complete Linked Data documentation
- **[API Reference](../API.md)** — All public endpoint details
- **[SPARQL Tutorial](sparql-queries.md)** — Query your collection with SPARQL
- **[Data Export Tutorial](data-export-walkthrough.md)** — Export your library
