import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "@fontsource/vazirmatn/400.css";
import "@fontsource/vazirmatn/600.css";
import "@fontsource/vazirmatn/700.css";
import "./index.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found.");
}

createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

function removeCriticalHomeFallback() {
  document.documentElement.classList.remove("home-critical-ready");
  const fallback = document.getElementById("home-critical-fallback");
  fallback?.remove();
}

window.requestAnimationFrame(() => {
  window.requestAnimationFrame(removeCriticalHomeFallback);
});
