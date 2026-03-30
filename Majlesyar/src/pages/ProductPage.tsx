import { lazy, Suspense, useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { QuantityStepper } from '@/components/QuantityStepper';
import { RuleAlert } from '@/components/RuleAlert';
import { SEO } from '@/components/SEO';
import { getProduct } from '@/lib/api';
import { notifySuccess } from '@/lib/notify';
import { useCart } from '@/contexts/CartContext';
import type { Product } from '@/types/domain';
import { ShoppingCart, ArrowRight, Check, Phone, Package } from 'lucide-react';
import { CONTACT_PHONE } from '@/data/siteConstants';

const LazyProductFeedbackSection = lazy(() =>
  import('@/components/ProductFeedbackSection').then((m) => ({ default: m.ProductFeedbackSection })),
);

export default function ProductPage() {
  const { slug } = useParams<{ slug: string }>();
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
          <Link to="/shop">
            <Button variant="outline" className="gap-2">
              <ArrowRight className="w-4 h-4" />
              بازگشت به فروشگاه
            </Button>
          </Link>
        </div>
      </AppShell>
    );
  }

  const productPath = `/product/${encodeURIComponent(product.urlSlug || product.id)}`;

  // Breadcrumbs for SEO
  const breadcrumbs = [
    { name: 'خانه', url: '/' },
    { name: 'فروشگاه', url: '/shop' },
    { name: product.name, url: productPath },
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
          category: product.categoryIds?.[0],
        }}
        breadcrumbs={breadcrumbs}
        keywords={['پک پذیرایی', product.name, ...product.contents.slice(0, 3)]}
      />
      <div className="container py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-8">
          <Link to="/" className="hover:text-foreground transition-colors">خانه</Link>
          <span>/</span>
          <Link to="/shop" className="hover:text-foreground transition-colors">فروشگاه</Link>
          <span>/</span>
          <span className="text-foreground">{product.name}</span>
        </nav>

        <div className="grid md:grid-cols-2 gap-8 lg:gap-12">
          {/* Image Gallery */}
          <div className="space-y-4">
            <div className="aspect-[4/3] sm:aspect-square bg-muted rounded-2xl border border-border relative overflow-hidden">
              {shouldShowImage ? (
                <img
                  src={product.image}
                  alt={product.imageAlt || product.name}
                  loading="eager"
                  fetchPriority="high"
                  decoding="async"
                  sizes="(max-width: 640px) 100vw, 50vw"
                  className="w-full h-full object-cover object-center"
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

          {/* Product Info */}
          <div className="space-y-6 min-h-[32rem]">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">
                {product.name}
              </h1>
              <p className="text-muted-foreground">{product.description}</p>
            </div>

            {/* Contents */}
            <div className="bg-card rounded-xl border border-border p-4">
              <h2 className="font-semibold text-foreground mb-3">محتویات پک:</h2>
              <ul className="space-y-2">
                {product.contents.map((item, index) => (
                  <li key={index} className="flex items-center gap-2 text-muted-foreground">
                    <Check className="w-4 h-4 text-success" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Price */}
            <div className="py-4 border-t border-b border-border">
              <p className="text-sm text-muted-foreground mb-1">قیمت هر پک:</p>
              <p className={`text-3xl font-bold ${product.price ? 'text-primary' : 'text-secondary'}`}>
                {formatPrice(product.price)}
              </p>
            </div>

            {/* Add to Cart */}
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

                <Button
                  variant="gold"
                  size="xl"
                  className="w-full gap-2"
                  onClick={handleAddToCart}
                >
                  <ShoppingCart className="w-5 h-5" />
                  افزودن به سبد خرید
                </Button>

              </div>
            ) : product.price === null ? (
              <div className="space-y-4">
                <RuleAlert
                  type="info"
                  message="برای اطلاع از قیمت و سفارش این محصول با ما تماس بگیرید"
                />
                <Button variant="teal" size="xl" className="w-full gap-2" asChild>
                  <a href={`tel:${CONTACT_PHONE}`}>
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

        <Suspense
          fallback={
            <section className="mt-12 rounded-2xl border border-border bg-muted/30 min-h-[20rem]" aria-hidden="true" />
          }
        >
          <LazyProductFeedbackSection productName={product.name} />
        </Suspense>
      </div>
    </AppShell>
  );
}
