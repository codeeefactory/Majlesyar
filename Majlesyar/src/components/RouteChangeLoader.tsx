import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { PageLoader } from "@/components/PageLoader";

const ROUTE_LOADER_DURATION_MS = 420;

export function RouteChangeLoader() {
  const location = useLocation();
  const isFirstRender = useRef(true);
  const [isVisible, setIsVisible] = useState(false);

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
