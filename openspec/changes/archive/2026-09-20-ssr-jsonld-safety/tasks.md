## 1. Safe serialization boundary

- [x] 1.1 Add a shared HTML-safe JSON-LD serializer/component that preserves valid JSON-LD values while escaping script-breaking characters, and verify its unit tests pass.
- [x] 1.2 Replace raw SSR JSON-LD sinks in Work, Expression, Manifestation, Item, profile, shared-collection, and collection pages, and verify a source scan finds no unsafe JSON-LD sink.
- [x] 1.3 Add a source-level guard/test that flags new raw `JSON.stringify()` + `dangerouslySetInnerHTML` JSON-LD sinks, and verify it fails on a synthetic unsafe fixture.

## 2. Verification

- [x] 2.1 Add tests for `</script>`, `<`, `>`, `&`, quotes, Unicode separators, and multiline profile text, and verify all cases pass.
- [x] 2.2 Verify parsed JSON-LD preserves the original values and existing Schema.org fields through SSR route tests.
- [x] 2.3 Run the relevant Vitest suites, full frontend tests, type-check, lint, and production build, and record successful commands.
