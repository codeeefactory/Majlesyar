import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { QuantityStepper } from '@/components/QuantityStepper';
import { CustomerFeedbackSection } from '@/components/CustomerFeedbackSection';
import { InternalLinkCards } from '@/components/InternalLinkCards';
import { RuleAlert } from '@/components/RuleAlert';
import { ResponsiveProductImage } from '@/components/ResponsiveProductImage';
import { SEO } from '@/components/SEO';
import { getProduct } from '@/lib/api';
import { isHiddenEventRoutePath } from '@/data/siteConstants';
import { notifySuccess } from '@/lib/notify';
import { useCart } from '@/contexts/CartContext';
import { useSettings } from '@/contexts/SettingsContext';
import type { Product } from '@/types/domain';
import { ShoppingCart, ArrowRight, Check, Phone, Package } from 'lucide-react';
import type { EventPage } from '@/types/domain';

const relatedProductLinks = [
  {
    patterns: ['شله زرد', 'شله‌زرد'],
    links: [
      { label: 'حلوا خرما', url: '/halva-khorma' },
      { label: 'خرما گردو', url: '/halva-khorma' },
      { label: 'خانه', url: '/' },
    ],
  },
  {
    patterns: ['پک میوه', 'پک پذیرایی'],
    links: [
      { label: 'پک ترحیم', url: '/pack/memorial' },
      { label: 'حلوا خرما', url: '/halva-khorma' },
      { label: 'خرما گردو', url: '/halva-khorma' },
      { label: 'گل ترحیم و تسلیت', url: '/flower/memorial-wreaths' },
      { label: 'خانه', url: '/' },
    ],
  },
  {
    patterns: ['پک ترحیم'],
    links: [
      { label: 'حلوا خرما', url: '/halva-khorma' },
      { label: 'شله زرد', url: '/food/shaleh-zard' },
      { label: 'گل ترحیم', url: '/flower/memorial-wreaths' },
      { label: 'فینگر فود', url: '/food/finger_food' },
      { label: 'خانه', url: '/' },
    ],
  },
  {
    patterns: ['تاج گل ترحیم', 'گل ترحیم', 'گل تسلیت'],
    links: [
      { label: 'خانه', url: '/' },
      { label: 'حلوا خرما', url: '/halva-khorma' },
    ],
  },
  {
    patterns: ['دسته گل'],
    links: [
      { label: 'گل ترحیم', url: '/flower/memorial-wreaths' },
      { label: 'فینگر فود', url: '/food/finger_food' },
      { label: 'خانه', url: '/' },
    ],
  },
  {
    patterns: ['باکس گل'],
    links: [
      { label: 'دسته گل', url: '/flower/bouquets' },
      { label: 'فینگر فود', url: '/food/finger_food' },
      { label: 'خانه', url: '/' },
    ],
  },
  {
    patterns: ['تاج گل تبریک', 'افتتاحیه'],
    links: [
      { label: 'فینگر فود', url: '/food/finger_food' },
      { label: 'خانه', url: '/' },
    ],
  },
  {
    patterns: ['حلوا', 'خرما'],
    links: [
      { label: 'شله زرد', url: '/food/shaleh-zard' },
      { label: 'دسته گل تسلیت', url: '/flower/bouquets' },
      { label: 'خانه', url: '/' },
    ],
  },
];

function normalizeRoutePath(path?: string) {
  if (!path) return '';
  return path === '/' ? path : path.replace(/\/+$/, '');
}

function getRouteDepth(path: string) {
  return normalizeRoutePath(path).split('/').filter(Boolean).length;
}

function getBestProductEvent(product: Product, eventPages: EventPage[]) {
  const productEventSlugs = new Set(product.eventTypes);
  const candidates = eventPages
    .filter(
      (event) =>
        productEventSlugs.has(event.slug) &&
        event.routePath &&
        event.available !== false &&
        !event.hidden &&
        !isHiddenEventRoutePath(event.routePath),
    )
    .sort((a, b) => getRouteDepth(b.routePath || '') - getRouteDepth(a.routePath || ''));

  return candidates[0];
}

function buildProductBreadcrumbs(product: Product, eventPages: EventPage[]) {
  const productPath = `/product/${encodeURIComponent(product.urlSlug || product.id)}`;
  const bestEvent = getBestProductEvent(product, eventPages);

  if (!bestEvent?.routePath) {
    return [
      { name: 'خانه', url: '/' },
      { name: 'پک میوه و پذیرایی', url: '/pack' },
      { name: product.name, url: productPath },
    ];
  }

  const targetPath = normalizeRoutePath(bestEvent.routePath);
  const routeCrumbs = eventPages
    .filter((event) => {
      const routePath = normalizeRoutePath(event.routePath);
      return (
        routePath &&
        event.available !== false &&
        !event.hidden &&
        !isHiddenEventRoutePath(event.routePath) &&
        (targetPath === routePath || targetPath.startsWith(`${routePath}/`))
      );
    })
    .sort((a, b) => getRouteDepth(a.routePath || '') - getRouteDepth(b.routePath || ''))
    .map((event) => ({
      name: event.name,
      url: normalizeRoutePath(event.routePath) || `/events/${event.slug}`,
    }));

  return [
    { name: 'خانه', url: '/' },
    ...routeCrumbs,
    { name: product.name, url: productPath },
  ];
}

export default function ProductPage() {
  const { slug } = useParams<{ slug: string }>();
  const { settings } = useSettings();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);
  const [imageFailed, setImageFailed] = useState(false);
  const { addItem } = useCart();

  useEffect(() => {
    const loadProduct = async () => {
      if (!slug) {
        setLoading(false);
        return;
      }
      const data = await getProduct(slug);
      setProduct(data);
      setLoading(false);
    };
    loadProduct();
  }, [slug]);

  const handleAddToCart = () => {
    if (!product || product.price === null) return;

    addItem({
      productId: product.id,
      name: product.name,
      quantity,
      price: product.price,
    });

    notifySuccess(`${quantity} عدد ${product.name} به سبد خرید اضافه شد`);
  };

  const formatPrice = (price: number | null) => {
    if (price === null) return 'تماس بگیرید';
    return `${price.toLocaleString('fa-IR')} تومان`;
  };
  const getContentName = (item: Product['contents'][number]) =>
    typeof item === 'string' ? item : item.name;
  const getContentPrice = (item: Product['contents'][number]) =>
    typeof item === 'string' ? null : item.price;

  const shouldShowImage = product?.image && product.image !== '/placeholder.svg' && !imageFailed;

  if (loading) {
    return (
      <AppShell>
        <div className="container py-8">
          <div className="animate-pulse space-y-8">
            <div className="h-5 w-56 bg-muted rounded" />
            <div className="grid md:grid-cols-2 gap-8 lg:gap-12">
              <div className="space-y-4">
                <div className="aspect-[4/3] sm:aspect-square bg-muted rounded-2xl border border-border" />
              </div>
              <div className="space-y-6 min-h-[32rem]">
                <div className="space-y-3">
                  <div className="h-9 bg-muted rounded w-3/4" />
                  <div className="h-4 bg-muted rounded w-full" />
                  <div className="h-4 bg-muted rounded w-5/6" />
                </div>
                <div className="bg-card rounded-xl border border-border p-4 space-y-3">
                  <div className="h-5 bg-muted rounded w-40" />
                  <div className="h-4 bg-muted rounded w-11/12" />
                  <div className="h-4 bg-muted rounded w-10/12" />
                  <div className="h-4 bg-muted rounded w-9/12" />
                  <div className="h-4 bg-muted rounded w-10/12" />
                </div>
                <div className="py-4 border-t border-b border-border space-y-3">
                  <div className="h-4 bg-muted rounded w-24" />
                  <div className="h-9 bg-muted rounded w-48" />
                </div>
                <div className="space-y-4">
                  <div className="h-10 bg-muted rounded w-44" />
                  <div className="h-4 bg-muted rounded w-32" />
                  <div className="h-12 bg-muted rounded-xl w-full" />
                </div>
              </div>
            </div>
            <div className="rounded-2xl border border-border bg-muted/30 min-h-[20rem]" />
          </div>
        </div>
      </AppShell>
    );
  }

  if (!product) {
    return (
      <AppShell>
        <div className="container py-16 text-center">
          <div className="text-6xl mb-4">😕</div>
          <h1 className="text-2xl font-bold text-foreground mb-4">محصول یافت نشد</h1>
          <Link to="/pack">
            <Button variant="outline" className="gap-2">
              <ArrowRight className="w-4 h-4" />
              بازگشت به محصولات
            </Button>
          </Link>
        </div>
      </AppShell>
    );
  }

  const productPath = `/product/${encodeURIComponent(product.urlSlug || product.id)}`;
  const breadcrumbs = buildProductBreadcrumbs(product, settings.eventPages);
  const productSearchText = [
    product.name,
    product.description,
    ...product.contents.map(getContentName),
  ].join(' ');
  const productInternalLinks = relatedProductLinks.find((group) =>
    group.patterns.some((pattern) => productSearchText.includes(pattern)),
  )?.links || [];
  const productInternalLinkCards = [
    ...productInternalLinks.filter((link) => link.url !== '/'),
    { label: 'صفحه اصلی', url: '/' },
  ];

  return (
    <AppShell>
      <SEO
        title={product.name}
        description={product.description}
        path={productPath}
        product={{
          name: product.name,
          description: product.description,
          price: product.price,
          image: product.image,
          category: product.categoryIds?.[0],
          reviews: product.customerReviews || [],
        }}
        breadcrumbs={breadcrumbs}
        keywords={['پک پذیرایی', product.name, ...product.contents.slice(0, 3).map(getContentName)]}
      />
      <div className="container py-8">
        <nav className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground mb-8">
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

        <div className="grid md:grid-cols-2 gap-8 lg:gap-12">
          <div className="space-y-4">
            <div className="aspect-[4/3] sm:aspect-square bg-muted rounded-2xl border border-border relative overflow-hidden">
              {shouldShowImage ? (
                <ResponsiveProductImage
                  product={product}
                  alt={product.imageAlt || product.name}
                  loading="eager"
                  fetchPriority="high"
                  sizesKey="detail"
                  sizes="(max-width: 640px) 100vw, 50vw"
                  className="w-full h-full object-contain object-center"
                  onError={() => setImageFailed(true)}
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Package className="w-24 h-24 text-muted-foreground/40" aria-hidden="true" />
                </div>
              )}
              {product.featured && (
                <div className="absolute top-4 right-4 bg-primary text-primary-foreground text-sm font-semibold px-3 py-1.5 rounded-full">
                  پیشنهاد ویژه
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6 min-h-[32rem]">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">{product.name}</h1>
              <p className="text-muted-foreground">{product.description}</p>
            </div>

            <div className="bg-card rounded-xl border border-border p-4">
              <h2 className="font-semibold text-foreground mb-3">محتویات پک:</h2>
              <ul className="space-y-2">
                {product.contents.map((item, index) => (
                  <li key={index} className="flex items-center justify-between gap-3 text-muted-foreground">
                    <span className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-success" />
                      {getContentName(item)}
                    </span>
                    {getContentPrice(item) !== null && (
                      <span className="text-sm text-foreground whitespace-nowrap">
                        {formatPrice(getContentPrice(item))}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            <div className="py-4 border-t border-b border-border">
              <p className="text-sm text-muted-foreground mb-1">قیمت هر پک:</p>
              <p className={`text-3xl font-bold ${product.price ? 'text-primary' : 'text-secondary'}`}>
                {formatPrice(product.price)}
              </p>
            </div>

            {product.price !== null && product.available ? (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <span className="text-foreground font-medium">تعداد:</span>
                  <QuantityStepper value={quantity} onChange={setQuantity} />
                </div>

                {product.price && (
                  <p className="text-sm text-muted-foreground">
                    جمع: <span className="font-semibold text-foreground">{(product.price * quantity).toLocaleString('fa-IR')} تومان</span>
                  </p>
                )}

                <Button variant="gold" size="xl" className="w-full gap-2" onClick={handleAddToCart}>
                  <ShoppingCart className="w-5 h-5" />
                  افزودن به سبد خرید
                </Button>
              </div>
            ) : product.price === null ? (
              <div className="space-y-4">
                <RuleAlert type="info" message="برای اطلاع از قیمت و سفارش این محصول با ما تماس بگیرید" />
                <Button variant="teal" size="xl" className="w-full gap-2" asChild>
                  <a href={`tel:${settings.contactPhone}`}>
                    <Phone className="w-5 h-5" />
                    تماس با ما
                  </a>
                </Button>
              </div>
            ) : (
              <RuleAlert type="warning" message="این محصول در حال حاضر موجود نیست" />
            )}
          </div>
        </div>
      </div>
      <CustomerFeedbackSection
        reviews={product.customerReviews || []}
        title="نظر مشتریان درباره این محصول"
        description="تجربه مشتریانی که این محصول را برای مراسم خود سفارش داده‌اند"
      />
      <InternalLinkCards
        links={productInternalLinkCards}
        imageProduct={product}
        title="صفحات مرتبط"
      />
    </AppShell>
  );
}
