import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ShoppingCart, Eye, Phone } from 'lucide-react';
import type { Product } from '@/types/domain';
import { useCart } from '@/contexts/CartContext';
import { Input } from '@/components/ui/input';
import { notifyInfo, notifySuccess } from '@/lib/notify';
import { useSettings } from '@/contexts/SettingsContext';

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  const { addItem } = useCart();
  const { settings } = useSettings();
  const [quantity, setQuantity] = useState(1);
  const [imageFailed, setImageFailed] = useState(false);

  const handleQuantityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    e.stopPropagation();
    const val = parseInt(e.target.value) || 1;
    setQuantity(Math.min(Math.max(val, 1), 999));
  };

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault();
    if (product.price === null) {
      notifyInfo('برای این محصول با ما تماس بگیرید');
      return;
    }
    addItem({
      productId: product.id,
      name: product.name,
      quantity,
      price: product.price,
    });
    notifySuccess(`${quantity} عدد ${product.name} به سبد خرید اضافه شد`);
    setQuantity(1);
  };

  const formatPrice = (price: number | null) => {
    if (price === null) return 'تماس بگیرید';
    return `${price.toLocaleString('fa-IR')} تومان`;
  };

  const shouldShowImage = product.image && product.image !== '/placeholder.svg' && !imageFailed;
  const productPath = `/product/${encodeURIComponent(product.urlSlug || product.id)}`;

  return (
    <article>
      <Link
        to={productPath}
        className="group block bg-card rounded-xl border border-border overflow-hidden card-hover focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        aria-label={`مشاهده ${product.name}`}
      >
        <div className="aspect-[16/11] sm:aspect-[4/3] bg-muted relative overflow-hidden">
          {shouldShowImage ? (
            <img
              src={product.image}
              alt={product.imageAlt || product.name}
              loading="lazy"
              decoding="async"
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
              className="w-full h-full object-cover object-center"
              onError={() => setImageFailed(true)}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-4xl opacity-30" aria-hidden="true">
              📦
            </div>
          )}
          {product.featured && (
            <span className="absolute top-2 right-2 bg-primary text-primary-foreground text-xs font-semibold px-2 py-1 rounded-full">
              ویژه
            </span>
          )}
          {!product.available && (
            <div className="absolute inset-0 bg-background/80 flex items-center justify-center">
              <span className="text-muted-foreground text-sm font-semibold">ناموجود</span>
            </div>
          )}
        </div>

        <div className="p-3 md:p-4 space-y-2">
          <h3 className="font-semibold text-sm md:text-base text-foreground group-hover:text-primary transition-colors line-clamp-1">
            {product.name}
          </h3>

          <p className="text-xs md:text-sm text-muted-foreground line-clamp-2">
            {product.description}
          </p>

          <div className="pt-1.5 border-t border-border">
            <p className={`text-sm md:text-base font-bold ${product.price ? 'text-foreground' : 'text-foreground/80'}`}>
              {formatPrice(product.price)}
            </p>
          </div>

          <div className="flex flex-col gap-2">
            {product.price !== null && product.available && (
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={1}
                  max={999}
                  value={quantity}
                  onChange={handleQuantityChange}
                  onClick={(e) => e.preventDefault()}
                  className="w-16 h-10 text-center text-sm"
                  aria-label="تعداد"
                />
                <Button
                  variant="gold"
                  size="sm"
                  className="flex-1 h-10 min-h-[40px] touch-manipulation"
                  onClick={handleAddToCart}
                  aria-label={`افزودن ${quantity} عدد ${product.name} به سبد خرید`}
                >
                  <ShoppingCart className="w-4 h-4 ml-1" aria-hidden="true" />
                  افزودن
                </Button>
              </div>
            )}
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1 text-xs h-10 min-h-[40px] touch-manipulation transition-all duration-150 hover:bg-primary/5 hover:border-primary/50 active:scale-95 active:bg-primary/10"
              >
                <Eye className="w-4 h-4 ml-1" aria-hidden="true" />
                مشاهده
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-10 min-h-[40px] px-3 touch-manipulation text-primary border-primary hover:bg-primary/10"
                onClick={(e) => {
                  e.preventDefault();
                  window.location.href = `tel:${settings.contactPhone}`;
                }}
                aria-label="تماس برای سفارش"
              >
                <Phone className="w-4 h-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </div>
      </Link>
    </article>
  );
}
