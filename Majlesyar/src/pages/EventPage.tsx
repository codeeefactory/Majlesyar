import { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { ProductCard } from '@/components/ProductCard';
import { Button } from '@/components/ui/button';
import { listProducts } from '@/lib/api';
import { eventTypes } from '@/data/siteConstants';
import { ArrowRight, Package, Wrench } from 'lucide-react';
import type { Product } from '@/types/domain';

export default function EventPage() {
  const { slug } = useParams<{ slug: string }>();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  const event = eventTypes.find((e) => e.slug === slug);
  const isEventAvailable = event?.available !== false;

  useEffect(() => {
    if (!event || !isEventAvailable) {
      setProducts([]);
      setLoading(false);
      return;
    }

    const loadProducts = async () => {
      const allProducts = await listProducts();
      const filtered = allProducts.filter((p) => 
        p.eventTypes.includes(slug || '')
      );
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
          path={`/events/${event.slug}`}
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
        path={`/events/${event.slug}`}
        breadcrumbs={[
          { name: 'خانه', url: '/' },
          { name: event.name, url: `/events/${event.slug}` },
        ]}
        keywords={event.seoKeywords}
        faq={event.faqs}
      />
      {/* Hero */}
      <section className={`${event.color} relative overflow-hidden`}>
        <div className="absolute -bottom-10 -left-10 text-[200px] opacity-10">
          {event.icon}
        </div>
        <div className="container py-12 md:py-16 relative z-10">
          <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
            <Link to="/" className="hover:text-foreground transition-colors">خانه</Link>
            <span>/</span>
            <span className="text-foreground">{event.name}</span>
          </nav>

          <div className="flex items-center gap-4 mb-4">
            <span className="text-5xl">{event.icon}</span>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground">
              {event.seoTitle || event.name}
            </h1>
          </div>
          
          <p className="text-muted-foreground text-lg max-w-lg mb-8">
            {event.seoDescription || event.description}
          </p>

          <div className="flex flex-wrap gap-4">
            <Link to="/shop">
              <Button variant="gold" size="lg" className="gap-2">
                <Package className="w-5 h-5" />
                سفارش سریع
              </Button>
            </Link>
            {/* Hidden for now: ساخت پک اختصاصی button */}
          </div>
        </div>
      </section>

      {/* Products */}
      <section className="container py-12">
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
      </section>
    </AppShell>
  );
}
