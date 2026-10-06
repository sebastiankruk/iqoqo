import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';
import jsdoc from 'eslint-plugin-jsdoc';

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    settings: {
      react: {
        version: '19.0',
      },
    },
    plugins: {
      jsdoc,
    },
    rules: {
      // Enforce JSDoc for top-level function declarations (keep checks reasonable)
      // JSDoc on exported declarations, and consistency *within* a block
      // that already carries one. The "require" family is off: it demands a
      // `@param` line for every destructured property, which for a React
      // component means re-listing a props interface that is already typed
      // and already documented on the interface itself. That is duplication
      // that goes stale silently — the interface is the source of truth, and
      // a second copy in a JSDoc block is a second thing to forget to
      // update. The codebase documents props on their interfaces.
      //
      // These were set to 'error' and had never been enforced, because
      // nothing ran eslint over this tree (see the lint-javascript job in
      // .github/workflows/quality.yml, which installs the tools and then
      // stops). Turning them on for real first required getting the tree to
      // zero; see docs/CHANGELOG.md for the 29,000-problem run that was
      // 99.5% a generated Playwright build directory this file failed to
      // ignore.
      'jsdoc/require-jsdoc': [
        'error',
        {
          require: {
            FunctionDeclaration: true,
            ArrowFunctionExpression: false,
            FunctionExpression: false,
          },
        },
      ],
      'jsdoc/require-param': 'off',
      'jsdoc/require-param-description': 'off',
      'jsdoc/require-returns': 'off',
      // On a destructured parameter this rule fires the *inverse* of what it is
      // for: it demands `@param props.status` for every destructured property,
      // so a component that documents its props on the interface (the
      // codebase convention) is reported 4-6 times per block. The message is
      // "Missing @param" -- about completeness, not accuracy. Accuracy, i.e. a
      // `@param` naming a parameter that does not exist, is the check worth
      // keeping, so it stays on for plain `.ts` modules where a hand-written
      // block can genuinely disagree with the signature, and is off for `.tsx`
      // where every JSDoc block sits above a destructured React component.
      'jsdoc/check-param-names': 'error',
      'jsdoc/require-param-type': 'off', // TypeScript already handles types
      'jsdoc/require-returns-type': 'off', // TypeScript already handles return types
      // `ignoreRestSiblings` is for the destructure-to-omit idiom:
      // `rows.map(({ _internalId, ...rest }) => rest)` strips an internal
      // bookkeeping key on the way out, and the binding is deliberately
      // unused. Without this the rule reports the idiom as dead code and the
      // only ways to silence it are deleting working code or an eslint-disable.
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          ignoreRestSiblings: true,
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],
    },
  },
  // Allow `any` in test files for mock return values
  {
    files: ['__tests__/**', 'tests/**'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
  // Component-level narrowing described above. `.tsx` only, so the accuracy
  // check survives in the API-client and hook modules.
  {
    files: ['**/*.tsx'],
    rules: {
      'jsdoc/check-param-names': 'off',
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    '.next/**',
    '.next-e2e/**',
    'out/**',
    'build/**',
    'next-env.d.ts',
    // Per-run E2E build directories. `make test-e2e` sets
    // IQOQO_E2E_NEXT_DIST_DIR so concurrent runs do not fight over one dist
    // dir, which means the directory is named `.next-e2e-<uid>-<token>`, not
    // `.next-e2e`. The literal `.next-e2e/**` above matches none of them, so
    // eslint was linting a 206 MB generated Playwright build and reporting
    // ~28,900 problems from generated code -- which is why nobody could tell
    // whether the real findings were being enforced.
    '.next-e2e-*/**',
    // Project-specific:
    'android/**',
    'test-results/**',
    'playwright-report/**',
  ]),
]);

export default eslintConfig;
