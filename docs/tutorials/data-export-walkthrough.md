# 📦 Tutorial: Data Export Walkthrough

Learn how to export your iqoqo library in Linked Data and JSON formats for backup, migration, or interoperability.

## 🎯 Learning Objectives

By the end of this tutorial, you will be able to:

- Export your collection in JSON-LD, Turtle, and JSON formats
- Understand the structure of each export format
- Use exports for backup and disaster recovery
- Migrate data between iqoqo instances
- Parse export files with common tools

## 📋 Prerequisites

- A running iqoqo instance (see [Installation Guide](../INSTALL.md))
- Items in your collection to export
- `curl` or a REST client
- An authentication token (see below)

## 🔐 Step 1: Authenticate

The export endpoint requires authentication:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"your_password"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])')

echo "Token obtained: ${TOKEN:0:20}..."
```

## 📄 Step 2: Export as JSON-LD (Default)

JSON-LD is the recommended format for interoperability and Linked Data applications:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  -o my-library.jsonld \
  "http://localhost:8000/api/items/export"

echo "Exported $(wc -c < my-library.jsonld) bytes"
```

**Sample Output:**

```json
{
  "@context": {
    "frbr": "http://purl.org/vocab/frbr/core#",
    "frbrer": "http://iflastandards.info/ns/frbr/frbrer/",
    "schema": "https://schema.org/",
    "dc": "http://purl.org/dc/terms/",
    "iqoqo": "https://iqoqo.org/ontology#",
    "Work": "frbr:Work",
    "Expression": "frbr:Expression",
    "Manifestation": "frbr:Manifestation",
    "Item": "frbr:Item",
    "title": "dc:title",
    "creator": "dc:creator",
    "isbn": "schema:isbn",
    "publisher": "schema:publisher",
    "exemplarOf": {"@id": "frbrer:exemplarOf", "@type": "@id"},
    "embodimentOf": {"@id": "frbrer:embodimentOf", "@type": "@id"}
  },
  "@graph": [
    {
      "@id": "https://iqoqo.cc/works/1",
      "@type": "Work",
      "title": "The Hobbit",
      "creator": "J.R.R. Tolkien"
    },
    {
      "@id": "https://iqoqo.cc/items/42",
      "@type": "Item",
      "exemplarOf": "https://iqoqo.cc/manifestations/99",
      "status": "available"
    }
  ]
}
```

## 🐢 Step 3: Export as Turtle

Turtle is a human-readable RDF format, ideal for debugging and Semantic Web tools:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  -o my-library.ttl \
  "http://localhost:8000/api/items/export?format=turtle"

# Preview the first 20 lines
head -20 my-library.ttl
```

**Sample Output:**

```turtle
@prefix frbr: <http://purl.org/vocab/frbr/core#> .
@prefix frbrer: <http://iflastandards.info/ns/frbr/frbrer/> .
@prefix schema: <https://schema.org/> .
@prefix dc: <http://purl.org/dc/terms/> .
@prefix iqoqo: <https://iqoqo.org/ontology#> .

<https://iqoqo.cc/works/1> a frbr:Work ;
    dc:title "The Hobbit" ;
    dc:creator "J.R.R. Tolkien" .

<https://iqoqo.cc/expressions/1> a frbr:Expression ;
    frbrer:expressionOf <https://iqoqo.cc/works/1> ;
    dc:language "en" .

<https://iqoqo.cc/manifestations/99> a frbr:Manifestation ;
    frbrer:embodimentOf <https://iqoqo.cc/expressions/1> ;
    schema:isbn "9780547928227" ;
    schema:publisher "Mariner Books" ;
    schema:bookFormat schema:Book .

<https://iqoqo.cc/items/42> a frbr:Item ;
    frbrer:exemplarOf <https://iqoqo.cc/manifestations/99> ;
    frbr:status "available" .
```

## 📋 Step 4: Export as Hierarchical JSON

The JSON format preserves the FRBR hierarchy explicitly:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  -o my-library.json \
  "http://localhost:8000/api/items/export?format=json"

# Preview the structure
python3 -m json.tool my-library.json | head -40
```

**Sample Output:**

```json
{
  "version": "1.0",
  "exported_at": "2026-09-21T14:30:22.000000",
  "items": [
    {
      "id": 42,
      "status": "available",
      "condition": "good",
      "added_at": "2026-01-15T14:22:00",
      "manifestation": {
        "id": 99,
        "isbn13": "9780547928227",
        "publisher": "Mariner Books",
        "format_type": "book",
        "expression": {
          "id": 1,
          "content_type": "text",
          "language": "en",
          "work": {
            "id": 1,
            "title": "The Hobbit",
            "meta": {
              "authors": ["J.R.R. Tolkien"],
              "categories": ["Fantasy"]
            }
          }
        }
      },
      "meta": {
        "notes": "Gift from Mom",
        "location": "Living room bookshelf"
      }
    }
  ]
}
```

## 🔍 Step 5: Compare Formats

| Feature              | JSON-LD          | Turtle           | JSON             |
| -------------------- | ---------------- | ---------------- | ---------------- |
| Human-readable       | ✅               | ✅✅             | ✅✅             |
| Machine-parseable    | ✅✅             | ✅               | ✅✅             |
| FRBR hierarchy       | Via `@graph`     | Via triples      | Explicit nesting |
| Schema.org types     | ✅               | ✅               | ❌               |
| Standard vocabularies| ✅ (JSON-LD ctx) | ✅ (prefixes)    | ❌               |
| Streaming support    | ✅               | ✅               | ✅               |
| File size            | Medium           | Medium           | Smallest         |
| Best for             | Interoperability | Semantic Web tools | Backup/migration |

## 🔄 Step 6: Import to Another Instance

Export from Instance A and import to Instance B:

```bash
# On Instance A — export
curl -H "Authorization: Bearer $TOKEN_A" \
  -o export.json \
  "http://instance-a:8000/api/items/export?format=json"

# On Instance B — import
curl -X POST "http://instance-b:8000/api/admin/import" \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d @export.json
```

> **Note:** The JSON format is designed for iqoqo-to-iqoqo migration. JSON-LD and Turtle are for Semantic Web interoperability.

## 🐍 Step 7: Parse Exports Programmatically

### Python with JSON

```python
import json

with open("my-library.json") as f:
    data = json.load(f)

print(f"Exported at: {data['exported_at']}")
print(f"Items: {len(data['items'])}")

for item in data["items"][:5]:
    work = item["manifestation"]["expression"]["work"]
    print(f"  - {work['title']} ({item['status']})")
```

### Python with JSON-LD (using PyLD)

```python
import json
from pyld import jsonld

with open("my-library.jsonld") as f:
    doc = json.load(f)

# Expand the JSON-LD to normalize terms
expanded = jsonld.expand(doc)
for item in expanded:
    print(item)
```

### Python with Turtle (using RDFlib)

```python
from rdflib import Graph

g = Graph()
g.parse("my-library.ttl", format="turtle")

# Count items
from rdflib import RDF
items = list(g.subjects(RDF.type, g.namespace_manager.expand_curie("frbr:Item")))
print(f"Items in export: {len(items)}")

# List all titles
from rdflib.namespace import DC
for s, p, o in g.triples((None, DC.title, None)):
    print(f"  - {o}")
```

## 💾 Step 8: Automated Backup Script

Create a cron-friendly backup script:

```bash
#!/bin/bash
# backup_iqoqo.sh — Daily library backup

set -euo pipefail

BASE_URL="http://localhost:8000"
BACKUP_DIR="$HOME/iqoqo-backups"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

# Get token
TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$IQOQO_EMAIL\",\"password\":\"$IQOQO_PASSWORD\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])')

# Export in all formats
curl -s -H "Authorization: Bearer $TOKEN" \
  -o "$BACKUP_DIR/iqoqo-$DATE.json" \
  "$BASE_URL/api/items/export?format=json"

curl -s -H "Authorization: Bearer $TOKEN" \
  -o "$BACKUP_DIR/iqoqo-$DATE.jsonld" \
  "$BASE_URL/api/items/export?format=json-ld"

curl -s -H "Authorization: Bearer $TOKEN" \
  -o "$BACKUP_DIR/iqoqo-$DATE.ttl" \
  "$BASE_URL/api/items/export?format=turtle"

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "iqoqo-*.json" -mtime +30 -delete
find "$BACKUP_DIR" -name "iqoqo-*.jsonld" -mtime +30 -delete
find "$BACKUP_DIR" -name "iqoqo-*.ttl" -mtime +30 -delete

echo "Backup complete: $BACKUP_DIR/iqoqo-$DATE.{json,jsonld,ttl}"
```

Make it executable and add to cron:

```bash
chmod +x backup_iqoqo.sh

# Run daily at 02:00
echo "0 2 * * * $HOME/backup_iqoqo.sh" | crontab -
```

## ❓ Troubleshooting

### 401 Unauthorized

- Verify your token is valid and not expired
- Re-authenticate: tokens expire after a configurable period

### Empty Export

- Verify you have items in your collection
- The export only includes the authenticated user's items

### Large Export Hangs

- Exports use streaming, so they shouldn't hang
- Check network connectivity and timeout settings
- For very large collections (10,000+ items), allow extra time

### Invalid JSON Output

- Check that the response wasn't truncated
- Verify the Content-Type header matches the requested format
- Try with a smaller limit first to verify format correctness

### Import Fails

- Ensure the JSON format matches iqoqo's expected schema
- Check for version compatibility between source and target instances
- Review import logs: `docker compose logs web | grep import`

## 📚 Next Steps

- **[Semantic Web Guide](../SEMANTIC_WEB.md)** — Full export documentation
- **[API Reference](../API.md)** — Export endpoint details
- **[SPARQL Tutorial](sparql-queries.md)** — Query your collection
- **[Linked Data Tutorial](linked-data-integration.md)** — Consume Linked Data
- **[Operations Runbook](../OPERATIONS.md)** — Backup and recovery procedures
