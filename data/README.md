# iqoqo Data Directory

This directory contains seed data and data export/import files for iqoqo.

## Files

- **seed_example.json** - Example seed data with sample books (The Hobbit and 1984) to help you get started with iqoqo.

## Using Seed Data

To initialize your database with the example data:

```bash
python scripts/init_db.py --seed-file data/seed_example.json
```

This will only import data if the database is empty. If you want to clear the database first, use:

```bash
# Via API
curl -X DELETE -H "Content-Type: application/json" \
     -d '{"confirm": true}' \
     http://localhost:5000/api/admin/clear

# Then import
python scripts/init_db.py --seed-file data/seed_example.json
```

## Data Export/Import

### Exporting Your Data

To create a backup of your library:

```bash
# Via API
curl -o my_library_backup.json http://localhost:5000/api/admin/export

# Store it in this directory
mv my_library_backup.json data/
```

### Importing Data

To restore from a backup:

```bash
curl -X POST -F "file=@data/my_library_backup.json" \
     http://localhost:5000/api/admin/import
```

## Data Format

See [docs/INSTALL.md](../docs/INSTALL.md#data-importexport) for detailed information about the data format and migration procedures.

## .gitignore

Note that `*.json` files in this directory (except `seed_example.json`) are ignored by Git to prevent accidental commits of personal library data.
