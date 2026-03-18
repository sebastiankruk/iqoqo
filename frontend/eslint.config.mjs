import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import jsdoc from "eslint-plugin-jsdoc";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    plugins: {
      jsdoc,
    },
    rules: {
      // Strictly enforce JSDoc comments with prop specifications for React components
      "jsdoc/require-jsdoc": ["error", {
        "require": {
          "FunctionDeclaration": true,
          "ArrowFunctionExpression": true,
          "FunctionExpression": true
        },
        "contexts": [
          "VariableDeclarator > ArrowFunctionExpression",
          "TSInterfaceDeclaration",
          "TSTypeAliasDeclaration"
        ]
      }],
      "jsdoc/require-param": "error",
      "jsdoc/require-param-description": "error",
      "jsdoc/require-returns": "error",
      "jsdoc/check-param-names": "error",
      "jsdoc/require-param-type": "off", // TypeScript already handles types
      "jsdoc/require-returns-type": "off" // TypeScript already handles return types
    }
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
