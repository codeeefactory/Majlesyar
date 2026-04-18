import { useEffect } from "react";
import { useSettings } from "@/contexts/SettingsContext";
import { getSameAsLinks } from "@/lib/contact";

interface BreadcrumbItem {
  name: string;
  url: string;
}

interface FAQItem {
  question: string;
  answer: string;
}

interface SEOProps {
  pageKey?: string;
  title?: string;
  description?: string;
  path?: string;
  ogImage?: string;
  product?: {
    name: string;
    description: string;
    price?: number | null;
    image?: string;
    category?: string;
  };
  breadcrumbs?: BreadcrumbItem[];
  faq?: FAQItem[];
  noindex?: boolean;
  keywords?: string[];
}

const PRODUCTION_SITE_URL = "https://majlesyar.com";
const DEFAULT_OG_IMAGE = "https://lovable.dev/opengraph-image-p98pqg.png";

function getBaseUrl() {
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return PRODUCTION_SITE_URL;
}

function buildDocumentTitle(pageTitle: string, siteName: string, siteTagline: string) {
  const trimmedTitle = pageTitle.trim();
  if (!trimmedTitle) {
    return `${siteName} | ${siteTagline}`;
  }
  if (trimmedTitle.includes(siteName)) {
    return trimmedTitle;
  }
  return `${trimmedTitle} | ${siteName}`;
}

function upsertMeta(attr: "name" | "property", key: string, content: string) {
  if (typeof document === "undefined") return;

  const selector = `meta[${attr}="${key}"]`;
  let el = document.head.querySelector(selector) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  if (el.getAttribute("content") !== content) {
    el.setAttribute("content", content);
  }
}

function removeMeta(attr: "name" | "property", key: string) {
  if (typeof document === "undefined") return;
  const el = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (el) el.remove();
}

function upsertCanonical(href: string) {
  if (typeof document === "undefined") return;

  let el = document.head.querySelector('link[rel="canonical"]') as HTMLLinkElement | null;
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", "canonical");
    document.head.appendChild(el);
  }
  if (el.href !== href) {
    el.href = href;
  }
}

function upsertJsonLd(key: string, data: Record<string, unknown>) {
  if (typeof document === "undefined") return;

  const id = `seo-jsonld-${key}`;
  let script = document.getElementById(id) as HTMLScriptElement | null;
  if (!script) {
    script = document.createElement("script");
    script.id = id;
    script.type = "application/ld+json";
    script.setAttribute("data-seo", "true");
    document.head.appendChild(script);
  }
  const content = JSON.stringify(data);
  if (script.textContent !== content) {
    script.textContent = content;
  }
}

function removeJsonLd(key: string) {
  if (typeof document === "undefined") return;
  const script = document.getElementById(`seo-jsonld-${key}`);
  if (script) script.remove();
}

export function SEO({
  pageKey,
  title,
  description,
  path = "",
  ogImage,
  product,
  breadcrumbs,
  faq,
  noindex = false,
  keywords,
}: SEOProps) {
  const { settings } = useSettings();

  useEffect(() => {
    const branding = settings.siteBranding;
    const pageSeo = pageKey ? settings.pageSeo[pageKey] : undefined;
    const resolvedTitle = title || pageSeo?.title || branding.defaultMetaTitle;
    const resolvedDescription =
      description || pageSeo?.description || branding.defaultMetaDescription;
    const resolvedKeywords = keywords || pageSeo?.keywords || branding.defaultMetaKeywords;
    const resolvedOgImage =
      ogImage ||
      product?.image ||
      settings.siteOgImageUrl ||
      settings.siteLogoUrl ||
      settings.siteFaviconUrl ||
      DEFAULT_OG_IMAGE;

    const baseUrl = getBaseUrl();
    const fullTitle = buildDocumentTitle(resolvedTitle, branding.siteName, branding.siteTagline);
    const canonicalUrl = `${baseUrl}${path}`;
    const keywordsValue = resolvedKeywords.join(", ");
    const sameAs = getSameAsLinks([
      settings.instagramUrl,
      settings.telegramUrl,
      settings.whatsappUrl,
      settings.baleUrl,
    ]);
    const logoUrl = settings.siteLogoUrl || settings.siteFaviconUrl || `${baseUrl}/favicon.ico`;

    if (typeof document !== "undefined") {
      document.documentElement.lang = "fa";
      document.documentElement.dir = "rtl";
      if (document.title !== fullTitle) {
        document.title = fullTitle;
      }
    }

    upsertMeta("name", "title", fullTitle);
    upsertMeta("name", "description", resolvedDescription);
    upsertMeta("name", "keywords", keywordsValue);
    upsertMeta("name", "author", branding.metaAuthor);
    upsertMeta("name", "application-name", branding.siteName);
    upsertMeta("name", "apple-mobile-web-app-title", branding.siteName);
    upsertMeta("name", "robots", noindex ? "noindex, nofollow" : "index, follow");
    upsertCanonical(canonicalUrl);

    upsertMeta("property", "og:type", product ? "product" : "website");
    upsertMeta("property", "og:url", canonicalUrl);
    upsertMeta("property", "og:title", fullTitle);
    upsertMeta("property", "og:description", resolvedDescription);
    upsertMeta("property", "og:image", resolvedOgImage);
    upsertMeta("property", "og:locale", "fa_IR");
    upsertMeta("property", "og:site_name", branding.siteName);

    upsertMeta("name", "twitter:card", "summary_large_image");
    upsertMeta("name", "twitter:url", canonicalUrl);
    upsertMeta("name", "twitter:title", fullTitle);
    upsertMeta("name", "twitter:description", resolvedDescription);
    upsertMeta("name", "twitter:image", resolvedOgImage);

    const organizationSchema = {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: branding.siteName,
      alternateName: branding.siteAlternateName,
      url: baseUrl,
      logo: logoUrl,
      description: resolvedDescription,
      contactPoint: {
        "@type": "ContactPoint",
        telephone: settings.contactPhone,
        contactType: "customer service",
        availableLanguage: "Persian",
      },
      address: {
        "@type": "PostalAddress",
        streetAddress: settings.contactAddress,
        addressCountry: "IR",
      },
      areaServed: ["تهران", "البرز"],
      sameAs,
    };

    const localBusinessSchema = {
      "@context": "https://schema.org",
      "@type": "FoodEstablishment",
      "@id": `${baseUrl}/#business`,
      name: branding.siteName,
      alternateName: branding.siteAlternateName,
      description: resolvedDescription,
      url: baseUrl,
      telephone: settings.contactPhone,
      priceRange: "$$",
      image: settings.siteOgImageUrl || logoUrl,
      address: {
        "@type": "PostalAddress",
        streetAddress: settings.contactAddress,
        addressCountry: "IR",
      },
      geo: {
        "@type": "GeoCoordinates",
        latitude: "35.7219",
        longitude: "51.4066",
      },
      openingHours: settings.workingHours,
      areaServed: [
        { "@type": "City", name: "تهران" },
        { "@type": "State", name: "البرز" },
      ],
      hasOfferCatalog: {
        "@type": "OfferCatalog",
        name: branding.siteTagline,
        itemListElement: settings.eventPages.map((eventPage) => ({
          "@type": "Offer",
          itemOffered: {
            "@type": "Service",
            name: eventPage.name,
          },
        })),
      },
      aggregateRating: {
        "@type": "AggregateRating",
        ratingValue: "4.8",
        reviewCount: "500",
      },
    };

    const websiteSchema = {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: branding.siteName,
      alternateName: [branding.siteAlternateName, "majlesyar.com"],
      url: baseUrl,
      potentialAction: {
        "@type": "SearchAction",
        target: `${baseUrl}/shop?q={search_term_string}`,
        "query-input": "required name=search_term_string",
      },
    };

    upsertJsonLd("organization", organizationSchema);
    upsertJsonLd("local-business", localBusinessSchema);
    upsertJsonLd("website", websiteSchema);

    if (product) {
      upsertJsonLd("product", {
        "@context": "https://schema.org",
        "@type": "Product",
        name: product.name,
        description: product.description,
        category: product.category || "پک پذیرایی",
        brand: { "@type": "Brand", name: branding.siteName },
        image: product.image || resolvedOgImage,
        ...(product.price
          ? {
              offers: {
                "@type": "Offer",
                price: product.price,
                priceCurrency: "IRR",
                availability: "https://schema.org/InStock",
                seller: { "@type": "Organization", name: branding.siteName },
              },
            }
          : {}),
      });
    } else {
      removeJsonLd("product");
    }

    if (breadcrumbs && breadcrumbs.length > 0) {
      upsertJsonLd("breadcrumb", {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: breadcrumbs.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item.name,
          item: `${baseUrl}${item.url}`,
        })),
      });
    } else {
      removeJsonLd("breadcrumb");
    }

    if (faq && faq.length > 0) {
      upsertJsonLd("faq", {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: faq.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: item.answer,
          },
        })),
      });
    } else {
      removeJsonLd("faq");
    }

    return () => {
      if (!noindex) {
        removeMeta("name", "robots");
      }
    };
  }, [
    pageKey,
    title,
    description,
    path,
    ogImage,
    product,
    breadcrumbs,
    faq,
    noindex,
    keywords,
    settings,
  ]);

  return null;
}
