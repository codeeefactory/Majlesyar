import { useEffect } from "react";
import { CONTACT_PHONE } from "@/data/siteConstants";

interface BreadcrumbItem {
  name: string;
  url: string;
}

interface FAQItem {
  question: string;
  answer: string;
}

interface SEOProps {
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

const SITE_NAME = "مجلس یار";
const DEFAULT_DESCRIPTION =
  "سفارش آنلاین پک‌های پذیرایی و پک نذری برای همایش، ترحیم، جشن تولد و دفاع پایان‌نامه. ارسال سریع در تهران و البرز با تضمین کیفیت و تازگی";
const DEFAULT_KEYWORDS = [
  "پک پذیرایی",
  "پک نذری",
  "کترینگ مراسم",
  "همایش",
  "ترحیم",
  "جشن تولد",
  "دفاع پایان‌نامه",
  "مجلس یار",
  "پذیرایی مراسمات",
  "سفارش آنلاین پذیرایی",
  "کترینگ تهران",
  "پذیرایی همایش",
  "پک میوه",
  "پک اسنک",
];
const DEFAULT_OG_IMAGE = "https://lovable.dev/opengraph-image-p98pqg.png";

function getBaseUrl() {
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return "https://majlesyar.runflare.run";
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
  title,
  description = DEFAULT_DESCRIPTION,
  path = "",
  ogImage = DEFAULT_OG_IMAGE,
  product,
  breadcrumbs,
  faq,
  noindex = false,
  keywords = DEFAULT_KEYWORDS,
}: SEOProps) {
  useEffect(() => {
    const baseUrl = getBaseUrl();
    const fullTitle = title ? `${title} | ${SITE_NAME}` : `${SITE_NAME} | پک‌های پذیرایی ویژه مراسمات`;
    const canonicalUrl = `${baseUrl}${path}`;
    const keywordsValue = keywords.join(", ");

    if (typeof document !== "undefined") {
      document.documentElement.lang = "fa";
      document.documentElement.dir = "rtl";
      if (document.title !== fullTitle) {
        document.title = fullTitle;
      }
    }

    upsertMeta("name", "title", fullTitle);
    upsertMeta("name", "description", description);
    upsertMeta("name", "keywords", keywordsValue);
    upsertMeta("name", "robots", noindex ? "noindex, nofollow" : "index, follow");
    upsertCanonical(canonicalUrl);

    upsertMeta("property", "og:type", product ? "product" : "website");
    upsertMeta("property", "og:url", canonicalUrl);
    upsertMeta("property", "og:title", fullTitle);
    upsertMeta("property", "og:description", description);
    upsertMeta("property", "og:image", ogImage);
    upsertMeta("property", "og:locale", "fa_IR");
    upsertMeta("property", "og:site_name", SITE_NAME);

    upsertMeta("name", "twitter:card", "summary_large_image");
    upsertMeta("name", "twitter:url", canonicalUrl);
    upsertMeta("name", "twitter:title", fullTitle);
    upsertMeta("name", "twitter:description", description);
    upsertMeta("name", "twitter:image", ogImage);

    const organizationSchema = {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: SITE_NAME,
      url: baseUrl,
      logo: `${baseUrl}/favicon.ico`,
      description: DEFAULT_DESCRIPTION,
      contactPoint: {
        "@type": "ContactPoint",
        telephone: CONTACT_PHONE,
        contactType: "customer service",
        availableLanguage: "Persian",
      },
      address: {
        "@type": "PostalAddress",
        addressLocality: "تهران",
        addressCountry: "IR",
      },
      areaServed: ["تهران", "البرز"],
      sameAs: ["https://instagram.com/majlesyar", "https://t.me/majlesyar"],
    };

    const localBusinessSchema = {
      "@context": "https://schema.org",
      "@type": "FoodEstablishment",
      "@id": `${baseUrl}/#business`,
      name: SITE_NAME,
      alternateName: "Majlesyar",
      description: DEFAULT_DESCRIPTION,
      url: baseUrl,
      telephone: CONTACT_PHONE,
      priceRange: "$$",
      image: `${baseUrl}/favicon.ico`,
      address: {
        "@type": "PostalAddress",
        streetAddress: "خیابان ولیعصر",
        addressLocality: "تهران",
        addressCountry: "IR",
      },
      geo: {
        "@type": "GeoCoordinates",
        latitude: "35.7219",
        longitude: "51.4066",
      },
      openingHoursSpecification: {
        "@type": "OpeningHoursSpecification",
        dayOfWeek: ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
        opens: "09:00",
        closes: "21:00",
      },
      areaServed: [
        { "@type": "City", name: "تهران" },
        { "@type": "City", name: "کرج" },
        { "@type": "State", name: "البرز" },
      ],
      hasOfferCatalog: {
        "@type": "OfferCatalog",
        name: "پک‌های پذیرایی",
        itemListElement: [
          { "@type": "Offer", itemOffered: { "@type": "Service", name: "پک پذیرایی همایش" } },
          { "@type": "Offer", itemOffered: { "@type": "Service", name: "پک نذری و ترحیم" } },
          { "@type": "Offer", itemOffered: { "@type": "Service", name: "پک جشن تولد" } },
          { "@type": "Offer", itemOffered: { "@type": "Service", name: "پک دفاع پایان‌نامه" } },
        ],
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
      name: SITE_NAME,
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
        brand: { "@type": "Brand", name: SITE_NAME },
        ...(product.price
          ? {
              offers: {
                "@type": "Offer",
                price: product.price,
                priceCurrency: "IRR",
                availability: "https://schema.org/InStock",
                seller: { "@type": "Organization", name: SITE_NAME },
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
  }, [title, description, path, ogImage, product, breadcrumbs, faq, noindex, keywords]);

  return null;
}
