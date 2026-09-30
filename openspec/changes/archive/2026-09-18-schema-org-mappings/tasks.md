## 1. Centralized Schema.org Utilities

- [x] 1.1 Create `frontend/lib/schema-org.ts` containing `schemaTypeMap`, `resolveSchemaType()`, `resolveInLanguage()`, and `mapCollectionStatusToAvailability()`, verifying with unit tests in `frontend/__tests__/lib/schema-org.test.ts`.
- [x] 1.2 Implement helper functions for building `Offer`, `ItemList`, and `CreativeWork` JSON-LD payloads in `frontend/lib/schema-org.ts`, verifying with unit tests in `frontend/__tests__/lib/schema-org.test.ts`.

## 2. Manifestation Page Structured Data

- [x] 2.1 Update `frontend/app/manifestation/[id]/page.tsx` to replace hardcoded `schemaType` logic with `resolveSchemaType(manifestation.content_type, manifestation.expression_kind, format)`.
- [x] 2.2 Add `inLanguage` to manifestation JSON-LD extracted from manifestation meta and language fields, verifying with tests in `frontend/__tests__/components/manifestation/semantic-markup.test.tsx`.
- [x] 2.3 Add `schema:offers` array to manifestation JSON-LD mapping associated item `collection_status` to `ItemAvailability`, verifying with tests in `frontend/__tests__/components/manifestation/semantic-markup.test.tsx`.

## 3. Collection Page Structured Data

- [x] 3.1 Update `frontend/app/collection/page.tsx` to inject `schema:CollectionPage` JSON-LD containing collection title, description, aggregate count, and catalog item list.
- [x] 3.2 Add component tests in `frontend/__tests__/app/collection/collection-seo.test.tsx` asserting that `CollectionPage` script tag renders with correct schema and item count.

## 4. Work Page CreativeWork Structured Data

- [x] 4.1 Implement `buildWorkJsonLd()` in `frontend/lib/schema-org.ts` producing `schema:CreativeWork` with `workExample` references modeling the full FRBR hierarchy.
- [x] 4.2 Inject Work `CreativeWork` structured data into work and item views, verifying JSON-LD output with tests in `frontend/__tests__/components/work/work-seo.test.tsx`.

## 5. Public XML Sitemap Endpoint

- [x] 5.1 Implement `generate_sitemap_xml()` helper and route `GET /api/public/sitemap.xml` in `app/api/public.py` generating valid Sitemaps XML for public users, shared collections, and public manifestations.
- [x] 5.2 Add rate limiting and HTTP cache headers (`Cache-Control: public, max-age=3600`) to the sitemap endpoint in `app/api/public.py`.
- [x] 5.3 Implement automated tests in `tests/test_public_sitemap.py` verifying XML structure, namespaces, correct URL inclusion, exclusion of private accounts/collections, and HTTP caching headers.
