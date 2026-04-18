import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { EventCard } from '@/components/EventCard';
import { HomepageBenefitsSection } from '@/components/HomepageBenefitsSection';
import { ProductCard } from '@/components/ProductCard';
import { SEO } from '@/components/SEO';
import { useSettings } from '@/contexts/SettingsContext';
import { Sparkles, Clock, ArrowLeft, Truck, Shield, Star, Wrench } from 'lucide-react';
import { listProducts } from '@/lib/api';
import type { Product } from '@/types/domain';

export default function HomePage() {
  const [featuredProducts, setFeaturedProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);
  const { settings } = useSettings();

  useEffect(() => {
    let isMounted = true;
    listProducts()
      .then((products) => {
        if (!isMounted) return;
        setFeaturedProducts(products.filter((p) => p.featured).slice(0, 4));
      })
      .catch(() => {
        if (!isMounted) return;
        setFeaturedProducts([]);
      })
      .finally(() => {
        if (!isMounted) return;
        setProductsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <AppShell>
      <SEO pageKey="home" path="/" />
      {/* Combined Hero & Event Types Section */}
      <section className="relative overflow-hidden" aria-labelledby="hero-title">
        <div className="absolute inset-0 cream-gradient" />
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary/5 rounded-full blur-3xl" aria-hidden="true" />
        <div className="absolute bottom-10 right-10 w-96 h-96 bg-secondary/5 rounded-full blur-3xl" aria-hidden="true" />
        
        <div className="container relative py-12 md:py-16">
          {/* Event Types */}
          <div className="mb-10">
            <header className="text-center mb-8">
            <h2 id="events-heading" className="text-2xl md:text-3xl font-bold text-foreground mb-3">
                نوع مراسم خود را انتخاب کنید
              </h2>
              <p className="text-muted-foreground text-base md:text-lg">
                پک‌های متناسب با هر نوع مراسم
              </p>
            </header>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
              {settings.eventPages.map((event) => (
                <div key={event.id}>
                  <EventCard {...event} />
                </div>
              ))}
            </div>
          </div>

          {/* Trust badges below Event Types */}
          <ul className="mb-12 md:mb-16 grid grid-cols-2 md:grid-cols-4 gap-4" aria-label={`مزایای ${settings.siteBranding.siteName}`}>
            {[
              { icon: Truck, label: 'ارسال سریع', desc: 'تهران و البرز' },
              { icon: Shield, label: 'تضمین کیفیت', desc: 'مواد تازه' },
              { icon: Clock, label: 'تحویل به‌موقع', desc: '۴۸ ساعته' },
              { icon: Star, label: 'رضایت مشتری', desc: '+۵۰۰ سفارش' },
            ].map((item, index) => (
              <li 
                key={index}
                className="flex items-center gap-3 bg-card p-4 rounded-xl border border-border hover:scale-[1.02] transition-transform duration-300"
              >
                <div className="w-10 h-10 md:w-12 md:h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <item.icon className="w-5 h-5 md:w-6 md:h-6 text-primary" aria-hidden="true" />
                </div>
                <div>
                  <p className="font-semibold text-foreground text-sm md:text-base">{item.label}</p>
                  <p className="text-xs md:text-sm text-muted-foreground">{item.desc}</p>
                </div>
              </li>
            ))}
          </ul>

          {/* Hero Content */}
          <div className="max-w-2xl mx-auto text-center space-y-6">
            <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium">
              <Sparkles className="w-4 h-4" aria-hidden="true" />
              پک‌های پذیرایی ویژه مراسمات
            </div>
            
            <h1 id="hero-title" className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-foreground leading-tight">
              پذیرایی حرفه‌ای با
              <span className="text-gradient-gold block mt-2">{settings.siteBranding.siteName}</span>
            </h1>
            
            <p className="text-lg md:text-xl text-muted-foreground max-w-lg mx-auto leading-relaxed">
              خدمات آماده و سفارشی برای فینگر فود، ترحیم، گل و حلوا و خرما.
              حداقل سفارش ۴۰ عدد با تحویل سریع در تهران و البرز.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center items-stretch sm:items-center pt-4">
              <Link to="/shop" className="w-full sm:w-auto">
                <Button
                  size="lg"
                  className="w-full sm:min-w-[200px] gap-2 min-h-[48px] touch-manipulation"
                >
                  مشاهده فروشگاه
                  <ArrowLeft className="w-5 h-5" aria-hidden="true" />
                </Button>
              </Link>
              <Link to="/builder" className="w-full sm:w-auto">
                <Button
                  variant="gold"
                  size="lg"
                  className="w-full sm:min-w-[200px] gap-2 min-h-[48px] touch-manipulation"
                >
                  <Wrench className="w-5 h-5" aria-hidden="true" />
                  ساخت پک اختصاصی
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Rule Alert - Hidden */}

      {/* Featured Products */}
      <section className="container py-16" aria-labelledby="products-heading">
        <header className="flex items-center justify-between mb-10">
          <div>
            <h2 id="products-heading" className="text-2xl md:text-3xl font-bold text-foreground mb-2">
              پک‌های پرفروش
            </h2>
            <p className="text-muted-foreground text-base md:text-lg">
              محبوب‌ترین پک‌ها بین مشتریان ما
            </p>
          </div>
          <Link to="/shop">
            <Button variant="ghost" className="gap-2 min-h-[44px] touch-manipulation">
              مشاهده همه
              <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            </Button>
          </Link>
        </header>

        <div className="grid grid-cols-2 gap-px">
          {productsLoading
            ? [1, 2, 3, 4].map((i) => (
                <div key={i} className="bg-card rounded-xl border border-border overflow-hidden animate-pulse">
                  <div className="aspect-[4/3] bg-muted" />
                  <div className="p-3 space-y-2">
                    <div className="h-4 bg-muted rounded" />
                    <div className="h-3 bg-muted rounded w-2/3" />
                  </div>
                </div>
              ))
            : featuredProducts.map((product) => (
                <div key={product.id}>
                  <ProductCard product={product} />
                </div>
              ))}
        </div>
      </section>

      <HomepageBenefitsSection />

      <section className="container py-16" aria-labelledby="cta-heading">
        <article className="bg-card rounded-3xl p-8 md:p-12 border border-border relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-full" aria-hidden="true">
            <div className="absolute top-10 right-10 w-48 h-48 bg-primary/5 rounded-full blur-2xl" />
            <div className="absolute bottom-10 left-10 w-64 h-64 bg-secondary/5 rounded-full blur-2xl" />
          </div>

          <div className="relative z-10 max-w-xl">
            <h2 id="cta-heading" className="text-2xl md:text-3xl font-bold text-foreground mb-4">
              پک اختصاصی خودتان را بسازید
            </h2>
            <p className="text-muted-foreground mb-6 text-base md:text-lg leading-relaxed">
              با انتخاب نوع بسته‌بندی، میوه، نوشیدنی و اسنک مورد نظر، پک منحصر به فرد خود را طراحی کنید.
            </p>
            <Link to="/builder">
              <Button variant="gold" size="lg" className="gap-2 min-h-[48px] touch-manipulation">
                شروع ساخت پک
                <ArrowLeft className="w-5 h-5" aria-hidden="true" />
              </Button>
            </Link>
          </div>
        </article>
      </section>

      {/* FAQ Section - Hidden */}
    </AppShell>
  );
}
