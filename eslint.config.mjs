// ESLint 9+ flat config format
export default [
    {
        files: ["app/web/static/js/**/*.js"],
        ignores: [
            "**/*.min.js",          // Ignore minified files
            "**/bootstrap*.js",     // Ignore Bootstrap
            "**/jquery*.js",        // Ignore jQuery
            "**/html5-qrcode*.js"   // Ignore html5-qrcode library
        ],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "script",
            globals: {
                // Browser globals
                window: "readonly",
                document: "readonly",
                console: "readonly",
                fetch: "readonly",
                // jQuery
                $: "readonly",
                jQuery: "readonly",
                // html5-qrcode
                Html5QrcodeScanner: "readonly",
                Html5Qrcode: "readonly",
                // Bootstrap
                bootstrap: "readonly",
                Toast: "readonly"
            }
        },
        rules: {
            // Possible errors
            "no-console": "off",
            "no-debugger": "warn",
            "no-unused-vars": ["warn", { args: "none" }],

            // Best practices
            "eqeqeq": "off",  // Allow == instead of === (legacy prototype code)
            "no-eval": "error",
            "no-implied-eval": "error",
            "no-var": "off",  // Allow var (legacy prototype code)
            "prefer-const": "off",  // Allow let (legacy prototype code)

            // Style
            "indent": "off",  // Don't enforce indentation (prototype uses mixed styles)
            "quotes": "off",  // Don't enforce quote style (prototype uses mixed styles)
            "semi": ["error", "always"],
            "comma-dangle": "off",  // Allow trailing commas
            "no-trailing-spaces": "warn"
        }
    }
];
