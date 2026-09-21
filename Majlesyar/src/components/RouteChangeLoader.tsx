import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { PageLoader } from "@/components/PageLoader";

const ROUTE_LOADER_DURATION_MS = 420;

export function RouteChangeLoader() {
  const location = useLocation();
  const isFirstRender = useRef(true);
  const [isVisible, setIsVisible] = useState(false);

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

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    setIsVisible(true);
    const timerId = window.setTimeout(() => {
      setIsVisible(false);
    }, ROUTE_LOADER_DURATION_MS);

    return () => window.clearTimeout(timerId);
  }, [location.pathname, location.search]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed inset-0 z-[120] flex items-center justify-center bg-background/54 backdrop-blur-[2px]">
      <div className="w-full max-w-md px-4">
        <PageLoader fullscreen={false} />
      </div>
    </div>
  );
}
