import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/media": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      react: "preact/compat",
      "react-dom": "preact/compat",
      "react-dom/test-utils": "preact/test-utils",
      "react-dom/client": "preact/compat",
      "react/jsx-runtime": "preact/jsx-runtime",
      "react/jsx-dev-runtime": "preact/jsx-dev-runtime",
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'framework-vendor': ['preact', 'preact/compat', 'preact/hooks', 'preact/jsx-runtime'],
          'router': ['react-router-dom'],
          'ui-core': ['@radix-ui/react-dialog', '@radix-ui/react-popover', '@radix-ui/react-tooltip'],
          'ui-extra': ['@radix-ui/react-accordion', '@radix-ui/react-tabs', '@radix-ui/react-select', '@radix-ui/react-checkbox'],
          'forms': ['react-hook-form', '@hookform/resolvers', 'zod'],
        },
      },
    },
  },
}));
