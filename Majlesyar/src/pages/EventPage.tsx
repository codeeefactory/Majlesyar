import { useState, useEffect, useMemo } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { ProductCard } from '@/components/ProductCard';
import { InternalLinkCards } from '@/components/InternalLinkCards';
import { Button } from '@/components/ui/button';
import { getPageProductPreview, listProducts } from '@/lib/api';
import { normalizePersianDisplayText } from '@/lib/persianText';
import { useSettings } from '@/contexts/SettingsContext';
import { isHiddenEventRoutePath } from '@/data/siteConstants';
import { ArrowRight, Package, Wrench } from 'lucide-react';
import type { EventPage as EventPageConfig, Product } from '@/types/domain';

function normalizeRoutePath(path?: string) {
  if (!path) return '';
  return path === '/' ? path : path.replace(/\/+$/, '');
}

function getRouteDepth(path: string) {
  return normalizeRoutePath(path).split('/').filter(Boolean).length;
}

function buildEventBreadcrumbs(event: EventPageConfig, eventPages: EventPageConfig[]) {
  const targetPath = normalizeRoutePath(event.routePath);
  const routeCrumbs = event.routePath
    ? eventPages
        .filter((item) => {
          const routePath = normalizeRoutePath(item.routePath);
          return (
            routePath &&
            item.available !== false &&
            !item.hidden &&
            !isHiddenEventRoutePath(item.routePath) &&
            (targetPath === routePath || targetPath.startsWith(`${routePath}/`))
          );
        })
        .sort((a, b) => getRouteDepth(a.routePath || '') - getRouteDepth(b.routePath || ''))
        .map((item) => ({
          name: item.name,
          url: normalizeRoutePath(item.routePath) || `/events/${item.slug}`,
        }))
    : [{ name: event.name, url: `/events/${event.slug}` }];

  return [{ name: 'خانه', url: '/' }, ...routeCrumbs];
}

const QUESTION_LABEL = "\u0633\u0648\u0627\u0644:";
const ANSWER_LABEL = "\u067e\u0627\u0633\u062e:";
const FAQ_HEADING_LABEL = "\u0633\u0648\u0627\u0644\u0627\u062a \u0645\u062a\u062f\u0627\u0648\u0644";

function isFaqContentBlock(block: NonNullable<EventPageConfig["contentBlocks"]>[number]) {
  const text = block.text.trim();
  return text.includes(FAQ_HEADING_LABEL) || text.startsWith(QUESTION_LABEL) || text.startsWith(ANSWER_LABEL);
}

function isEditorialContentBlock(block: NonNullable<EventPageConfig["contentBlocks"]>[number]) {
  const text = block.text.trim();
  const normalized = normalizePersianDisplayText(text);
  return (
    text.includes("پایین تر از h1") ||
    /آدرس\s*(اول|دوم|سوم|چهارم|پنجم|اصلی)?:/.test(text) ||
    /^[0-9۰-۹]+\s*آدرس\./.test(text) ||
    /^[()]\s*[^()]{1,28}$/.test(normalized) ||
    /^[^()]{1,28}\s*[()]$/.test(normalized) ||
    (/^\(.+\)$/.test(normalized) && normalized.length < 28)
  );
}

function getHeroNoteFromContentBlocks(contentBlocks?: EventPageConfig["contentBlocks"]) {
  const instruction = contentBlocks?.find((block) => block.text.includes("پایین تر از h1"));
  if (!instruction) return "";

  const [, note] = instruction.text.split("نوشته بشه");
  return normalizePersianDisplayText(note || instruction.text.replace("پایین تر از h1 در گل بایدdiv نوشته بشه", ""));
}

export default function EventPage() {
  const { slug } = useParams<{ slug: string }>();
  const { pathname } = useLocation();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const { settings } = useSettings();

  const event = settings.eventPages.find((e) => e.slug === slug || e.routePath === pathname);
  const isEventAvailable = event?.available !== false;
  const visibleInternalLinks = event?.internalLinks?.filter((link) => {
    const linkedEvent = settings.eventPages.find((page) => page.routePath === link.url);
    return !linkedEvent?.hidden && !isHiddenEventRoutePath(link.url);
  });
  const breadcrumbs = event ? buildEventBreadcrumbs(event, settings.eventPages) : [];
  const heroNote = event?.routePath === "/flower" ? getHeroNoteFromContentBlocks(event.contentBlocks) : "";
  const articleContentBlocks =
    event?.contentBlocks?.filter((block) => !isFaqContentBlock(block) && !isEditorialContentBlock(block)) || [];
  const hasContentBlocks = articleContentBlocks.length > 0;
  const hasFaqs = Boolean(event?.faqs?.length);

  useEffect(() => {
    if (!event || !isEventAvailable) {
      setProducts([]);
      setLoading(false);
      return;
    }

    const loadProducts = async () => {
      const preview = await getPageProductPreview('event', event.slug || slug || '');
      if (preview?.products?.length) {
        setProducts(preview.products);
        setLoading(false);
        return;
      }

      const allProducts = await listProducts();
      const filtered = allProducts.filter((p) => p.eventTypes.includes(event.slug || slug || ''));
      setProducts(filtered);
      setLoading(false);
    };
    loadProducts();
  }, [event, isEventAvailable, slug]);

  if (!event) {
    return (
      <AppShell>
        <div className="container py-16 text-center">
          <div className="text-6xl mb-4">🔍</div>
          <h1 className="text-2xl font-bold text-foreground mb-4">مراسم یافت نشد</h1>
          <Link to="/">
            <Button variant="outline" className="gap-2">
              <ArrowRight className="w-4 h-4" />
              بازگشت به خانه
            </Button>
          </Link>
        </div>
      </AppShell>
    );
  }

  if (!isEventAvailable) {
    return (
      <AppShell>
        <SEO
          title={`${event.name} (به‌زودی)`}
          description={event.description}
          path={event.routePath || `/events/${event.slug}`}
          noindex={true}
        />
        <section className={`${event.color} relative overflow-hidden`}>
          <div className="container py-16 text-center">
            <div className="text-6xl mb-4">{event.icon}</div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-3">{event.name}</h1>
            <p className="text-muted-foreground text-lg mb-8">این بخش به‌زودی فعال می‌شود.</p>
            <Link to="/">
              <Button variant="outline" className="gap-2">
                <ArrowRight className="w-4 h-4" />
                بازگشت به خانه
              </Button>
            </Link>
          </div>
        </section>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <SEO
        title={event.seoTitle || event.name}
        description={event.seoDescription || event.description}
        path={event.routePath || `/events/${event.slug}`}
        noindex={event.hidden}
        collection={
          !loading
            ? {
                name: event.seoTitle || event.name,
                description: event.seoDescription || event.description,
                products,
              }
            : undefined
        }
        breadcrumbs={breadcrumbs}
        keywords={event.seoKeywords}
        faq={event.faqs}
      />
      {/* Hero */}
      <section className={`${event.color} relative overflow-hidden`}>
        <div className="absolute -bottom-10 -left-10 text-[200px] opacity-10">
          {event.icon}
        </div>
        <div className="container py-12 md:py-16 relative z-10">
          <nav className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground mb-6">
            {breadcrumbs.map((item, index) => (
              <span key={`${item.url}-${item.name}`} className="inline-flex items-center gap-2">
                {index > 0 ? <span>/</span> : null}
                {index < breadcrumbs.length - 1 ? (
                  <Link to={item.url} className="hover:text-foreground transition-colors">
                    {item.name}
                  </Link>
                ) : (
                  <span className="text-foreground">{item.name}</span>
                )}
              </span>
            ))}
          </nav>

          <div className="flex items-center gap-4 mb-4">
            <span className="text-5xl">{event.icon}</span>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground">
              {event.seoTitle || event.name}
            </h1>
          </div>

          {heroNote ? (
            <div className="mb-5 max-w-2xl rounded-lg border border-primary/15 bg-background/75 px-4 py-3 text-base font-semibold leading-8 text-foreground shadow-soft">
              {heroNote}
            </div>
          ) : null}
          
          <p className="text-muted-foreground text-lg max-w-lg mb-8">
            {event.seoDescription || event.description}
          </p>

          <div className="flex flex-wrap gap-4">
            <Button variant="gold" size="lg" className="gap-2" asChild>
              <a href="#event-products">
                <Package className="w-5 h-5" />
                سفارش سریع
              </a>
            </Button>
            {/* Hidden for now: ساخت پک اختصاصی button */}
          </div>
        </div>
      </section>

      {/* Products */}
      <section id="event-products" className="container py-12">
        <h2 className="text-2xl font-bold text-foreground mb-6">
          محصولات مناسب برای {event.name}
        </h2>

        {loading ? (
          <div className="grid grid-cols-2 gap-px">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-card rounded-xl border border-border overflow-hidden animate-pulse">
                <div className="aspect-[4/3] bg-muted" />
                <div className="p-3 space-y-2">
                  <div className="h-4 bg-muted rounded" />
                  <div className="h-3 bg-muted rounded w-2/3" />
                </div>
              </div>
            ))}
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-16 bg-card rounded-2xl border border-border">
            <div className="text-6xl mb-4">📦</div>
            <h3 className="text-xl font-semibold text-foreground mb-2">
              محصولی در این دسته موجود نیست
            </h3>
            <p className="text-muted-foreground mb-4">
              برای سفارش با ما تماس بگیرید
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-px">
            {products.map((product, index) => (
              <div
                key={product.id}
                className="animate-fade-in"
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <ProductCard product={product} />
              </div>
            ))}
          </div>
        )}

        <InternalLinkCards
          links={visibleInternalLinks || []}
          imageProduct={products[0]}
          className="mt-10"
          withContainer={false}
        />

        {hasContentBlocks ? (
          <div className="mx-auto mt-10 max-w-4xl space-y-4 text-right" dir="rtl">
            {articleContentBlocks.map((block, index) => {
              const key = `${block.tag || "p"}-${index}-${block.text.slice(0, 24)}`;
              const displayText = normalizePersianDisplayText(block.text);
              if (block.tag === "h2") {
                return (
                  <h2 key={key} className="pt-4 text-2xl font-bold leading-10 text-foreground">
                    {displayText}
                  </h2>
                );
              }
              if (block.tag === "h3") {
                return (
                  <h3 key={key} className="pt-2 text-lg font-semibold leading-8 text-foreground">
                    {displayText}
                  </h3>
                );
              }
              return (
                <p key={key} className="text-base leading-8 text-muted-foreground">
                  {displayText}
                </p>
              );
            })}
          </div>
        ) : null}

        {!hasContentBlocks && event.benefits?.length ? (
          <div className="mt-10">
            <h2 className="mb-6 text-2xl font-bold text-foreground">
              مزایای خرید {event.name} از مجلس
            </h2>
            <div className="grid gap-3 md:grid-cols-2">
              {event.benefits.map((benefit) => (
                <article key={benefit.title} className="rounded-lg border border-border bg-card p-4">
                  <h3 className="mb-2 text-base font-semibold text-foreground">{benefit.title}</h3>
                  <p className="text-sm leading-7 text-muted-foreground">{benefit.description}</p>
                </article>
              ))}
            </div>
          </div>
        ) : null}

        {!hasContentBlocks && (event.introTitle || event.introDescription) ? (
          <div className="mt-10">
            {event.introTitle ? (
              <h2 className="mb-4 text-2xl font-bold text-foreground">{event.introTitle}</h2>
            ) : null}
            {event.introDescription ? (
              <p className="max-w-3xl text-base leading-8 text-muted-foreground">{event.introDescription}</p>
            ) : null}
          </div>
        ) : null}

        {hasFaqs ? (
          <div className="mt-10 text-right" dir="rtl">
            <h2 className="mb-6 text-2xl font-bold text-foreground">
              سوالات متداول سفارش {event.name}
            </h2>
            <div className="space-y-3">
              {event.faqs.map((faq) => (
                <article key={faq.question} className="rounded-lg border border-border bg-card p-4">
                  <h3 className="mb-2 text-base font-semibold text-foreground">
                    {normalizePersianDisplayText(faq.question)}
                  </h3>
                  <p className="text-sm leading-7 text-muted-foreground">
                    {normalizePersianDisplayText(faq.answer)}
                  </p>
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </AppShell>
  );
}
