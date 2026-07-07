import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';
import jsdoc from 'eslint-plugin-jsdoc';

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    plugins: {
      jsdoc,
    },
    rules: {
      // Enforce JSDoc for top-level function declarations (keep checks reasonable)
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
      'jsdoc/require-param': 'error',
      'jsdoc/require-param-description': 'error',
      'jsdoc/require-returns': 'error',
      'jsdoc/check-param-names': 'error',
      'jsdoc/require-param-type': 'off', // TypeScript already handles types
      'jsdoc/require-returns-type': 'off', // TypeScript already handles return types
      'react-hooks/set-state-in-effect': 'off',
    },
  },
  // Allow `any` in test files for mock return values
  {
    files: ['__tests__/**'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
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
    // Project-specific:
    'android/**',
  ]),
]);

export default eslintConfig;
