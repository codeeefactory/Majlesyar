import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ShoppingCart, Eye, Phone } from 'lucide-react';
import type { Product } from '@/types/domain';
import { useCart } from '@/contexts/CartContext';
import { Input } from '@/components/ui/input';
import { ResponsiveProductImage } from '@/components/ResponsiveProductImage';
import { notifyInfo, notifySuccess } from '@/lib/notify';
import { buildProductPath } from '@/lib/productRoutes';
import { useSettings } from '@/contexts/SettingsContext';

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  const { addItem } = useCart();
  const { settings } = useSettings();
  const [quantity, setQuantity] = useState(1);
  const [imageFailed, setImageFailed] = useState(false);

  const handleQuantityChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(event.target.value) || 1;
    setQuantity(Math.min(Math.max(val, 1), 999));
  };

  const handleAddToCart = () => {
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
  const productPath = buildProductPath(product, settings.eventPages);

  return (
    <article className="bg-card rounded-xl border border-border overflow-hidden card-hover">
      <Link
        to={productPath}
        rel={product.isTemporary ? 'nofollow' : undefined}
        className="group block focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
      >
        <div className="aspect-square bg-muted relative overflow-hidden">
          {shouldShowImage ? (
            <ResponsiveProductImage
              product={product}
              alt={product.imageAlt || product.name}
              loading="lazy"
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
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
            <div className="absolute inset-0 bg-background/80 flex items-center justify-center" aria-hidden="true">
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
        </div>
      </Link>

      <div className="px-3 pb-3 md:px-4 md:pb-4">
        <div className="flex flex-col gap-2">
          {product.price !== null && product.available && (
            <div className="flex items-center gap-2">
              <Input
                type="number"
                min={1}
                max={999}
                value={quantity}
                onChange={handleQuantityChange}
                className="w-16 h-10 text-center text-sm"
                aria-label={`تعداد ${product.name}`}
              />
              <Button
                type="button"
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
              asChild
              variant="outline"
              size="sm"
              className="flex-1 text-xs h-10 min-h-[40px] touch-manipulation transition-all duration-150 hover:bg-primary/5 hover:border-primary/50 active:scale-95 active:bg-primary/10"
            >
              <Link
                to={productPath}
                rel={product.isTemporary ? 'nofollow' : undefined}
                aria-label={`مشاهده جزئیات ${product.name}`}
              >
                <Eye className="w-4 h-4 ml-1" aria-hidden="true" />
                مشاهده
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="sm"
              className="h-10 min-h-[40px] px-3 touch-manipulation text-primary border-primary hover:bg-primary/10"
            >
              <a href={`tel:${settings.contactPhone}`} aria-label={`تماس برای سفارش ${product.name}`}>
                <Phone className="w-4 h-4" aria-hidden="true" />
              </a>
            </Button>
          </div>
        </div>
      </div>
    </article>
  );
}
