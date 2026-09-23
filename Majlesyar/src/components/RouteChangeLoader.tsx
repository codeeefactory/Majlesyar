import { useEffect, useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";

export function RouteChangeLoader() {
  const location = useLocation();

  useEffect(() => {
    const previousScrollRestoration = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";
    return () => {
      window.history.scrollRestoration = previousScrollRestoration;
    };
  }, []);

  useLayoutEffect(() => {
    const resetScroll = () => {
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
    };
    resetScroll();

    // Lazy routes can mount after navigation. Reset again when their main content appears.
    const routeContainer = document.getElementById("app-routes");
    const observer = new MutationObserver(() => {
      if (routeContainer?.querySelector("main")) {
        window.requestAnimationFrame(resetScroll);
        observer.disconnect();
      }
    });
    if (routeContainer && !routeContainer.querySelector("main")) {
      observer.observe(routeContainer, { childList: true, subtree: true });
    }
    const frame = window.requestAnimationFrame(resetScroll);
    const stopObserver = window.setTimeout(() => observer.disconnect(), 2000);

    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(stopObserver);
      observer.disconnect();
    };
  }, [location.key, location.pathname, location.search]);

  return null;
}
