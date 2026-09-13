import { isHiddenEventRoutePath } from "@/data/siteConstants";
import type { EventPage, Product } from "@/types/domain";

type ProductRouteSource = Pick<Product, "id" | "urlSlug"> & Partial<Pick<Product, "eventTypes" | "publicPath">>;

export function normalizeRoutePath(path?: string) {
  if (!path) return "";
  return path === "/" ? path : path.replace(/\/+$/, "");
}

export function getRouteDepth(path: string) {
  return normalizeRoutePath(path).split("/").filter(Boolean).length;
}

export function getBestProductEvent(product: ProductRouteSource, eventPages: EventPage[]) {
  const productEventSlugs = new Set(product.eventTypes || []);
  const candidates = eventPages
    .filter((event) => {
      const routePath = normalizeRoutePath(event.routePath);
      return (
        productEventSlugs.has(event.slug) &&
        routePath &&
        event.available !== false &&
        !event.hidden &&
        !isHiddenEventRoutePath(routePath)
      );
    })
    .sort((a, b) => getRouteDepth(b.routePath || "") - getRouteDepth(a.routePath || ""));

  return candidates[0];
}

export function buildProductPath(product: ProductRouteSource, eventPages: EventPage[] = []) {
  const configuredPath = normalizeRoutePath(product.publicPath);
  if (configuredPath) return configuredPath;
  const productSlug = encodeURIComponent(product.urlSlug || product.id);
  const parentRoute = normalizeRoutePath(getBestProductEvent(product, eventPages)?.routePath);
  return parentRoute ? `${parentRoute}/${productSlug}` : `/pack/${productSlug}`;
}
