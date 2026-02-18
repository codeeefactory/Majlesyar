import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

function nonBlockingStylesheetPlugin() {
  return {
    name: "non-blocking-stylesheet-plugin",
    apply: "build" as const,
    transformIndexHtml(html: string) {
      return html.replace(/<link rel="stylesheet"[^>]*>/g, (tag) => {
        const hrefMatch = tag.match(/href="([^"]+)"/);
        if (!hrefMatch) return tag;

        const href = hrefMatch[1];
        const hasCrossorigin = /\scrossorigin(\s|>)/.test(tag);
        const crossorigin = hasCrossorigin ? " crossorigin" : "";

        return [
          `<link rel="preload" as="style" href="${href}"${crossorigin} onload="this.onload=null;this.rel='stylesheet'">`,
          `<noscript><link rel="stylesheet" href="${href}"${crossorigin}></noscript>`,
        ].join("");
      });
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/media": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  plugins: [react(), mode === "development" && componentTagger(), nonBlockingStylesheetPlugin()].filter(Boolean),
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
