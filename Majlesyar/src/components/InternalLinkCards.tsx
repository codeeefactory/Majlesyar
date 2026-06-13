import { Link } from "react-router-dom";
import { ArrowLeft, Home, Package } from "lucide-react";
import { ResponsiveProductImage } from "@/components/ResponsiveProductImage";
import type { InternalLink, Product } from "@/types/domain";

interface InternalLinkCardsProps {
  links: InternalLink[];
  imageProduct?: Product | null;
  title?: string;
  className?: string;
  withContainer?: boolean;
}

function getLinkLabel(link: InternalLink) {
  return link.url === "/" ? "مشاهده صفحه اصلی" : `مشاهده ${link.label}`;
}

export function InternalLinkCards({
  links,
  imageProduct,
  title = "صفحات مرتبط",
  className = "",
  withContainer = true,
}: InternalLinkCardsProps) {
  const uniqueLinks = links.filter(
    (link, index, allLinks) => link.url && index === allLinks.findIndex((item) => item.url === link.url),
  );

  if (!uniqueLinks.length) return null;

  const shouldShowImage = imageProduct?.image && imageProduct.image !== "/placeholder.svg";

  const sectionClassName = [withContainer ? "container pb-12" : "", className].filter(Boolean).join(" ");

  return (
    <section className={sectionClassName} aria-labelledby="internal-links-heading">
      <h2 id="internal-links-heading" className="mb-6 text-2xl font-bold text-foreground">
        {title}
      </h2>
      <nav className="grid grid-cols-2 gap-px md:grid-cols-3 lg:grid-cols-4" aria-label="لینک‌های مرتبط">
        {uniqueLinks.map((link) => (
          <Link
            key={`${link.url}-${link.label}`}
            to={link.url}
            className="group block overflow-hidden rounded-xl border border-border bg-card transition-colors hover:border-primary focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            aria-label={getLinkLabel(link)}
          >
            <div className="relative aspect-[16/11] bg-muted">
              {link.url === "/" ? (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Home className="h-14 w-14 text-primary/70" aria-hidden="true" />
                </div>
              ) : shouldShowImage && imageProduct ? (
                <ResponsiveProductImage
                  product={imageProduct}
                  alt={imageProduct.imageAlt || imageProduct.name}
                  loading="lazy"
                  sizes="(max-width: 768px) 50vw, 25vw"
                  className="h-full w-full object-cover object-center"
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Package className="h-14 w-14 text-muted-foreground/40" aria-hidden="true" />
                </div>
              )}
            </div>
            <div className="flex min-h-[3.5rem] items-center justify-between gap-2 p-3">
              <span className="text-sm font-semibold leading-6 text-foreground transition-colors group-hover:text-primary">
                {getLinkLabel(link)}
              </span>
              <ArrowLeft className="h-4 w-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" aria-hidden="true" />
            </div>
          </Link>
        ))}
      </nav>
    </section>
  );
}
