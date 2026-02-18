import { Link } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Button } from '@/components/ui/button';
import { QuantityStepper } from '@/components/QuantityStepper';
import { RuleAlert } from '@/components/RuleAlert';
import { useCart } from '@/contexts/CartContext';
import { Trash2, ShoppingBag, ArrowLeft, Package } from 'lucide-react';

export default function CartPage() {
  const {
    items,
    removeItem,
    updateQuantity,
    totalQuantity,
    totalPrice,
    isMinQuantityMet,
    minQuantityRequired,
  } = useCart();

  if (items.length === 0) {
    return (
      <AppShell>
        <div className="container py-16 text-center">
          <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-muted flex items-center justify-center">
            <ShoppingBag className="w-12 h-12 text-muted-foreground" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">سبد خرید خالی است</h1>
          <p className="text-muted-foreground mb-6">
            محصولات مورد نظر خود را به سبد خرید اضافه کنید
          </p>
          <Link to="/shop">
            <Button variant="gold" size="lg" className="gap-2">
              <Package className="w-5 h-5" />
              مشاهده محصولات
            </Button>
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <SEO
        title="سبد خرید"
        description="مشاهده و مدیریت سبد خرید پک‌های پذیرایی"
        path="/cart"
        noindex={true}
      />
      <div className="container py-8">
        <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-8">سبد خرید</h1>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2 space-y-4">
            {items.map((item) => (
              <div
                key={item.productId}
                className="bg-card rounded-2xl border border-border p-4 md:p-6"
              >
                <div className="flex items-start gap-4">
                  {/* Image placeholder */}
                  <div className="w-20 h-20 bg-muted rounded-xl flex items-center justify-center text-3xl shrink-0">
                    {item.isCustomPack ? '🎨' : '📦'}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="font-semibold text-foreground">{item.name}</h3>
                        {item.isCustomPack && item.customConfig && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">
                              {item.customConfig.packaging}
                            </span>
                            <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">
                              {item.customConfig.fruit}
                            </span>
                            <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">
                              {item.customConfig.drink}
                            </span>
                            <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">
                              {item.customConfig.snack}
                            </span>
                          </div>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:bg-destructive/10"
                        onClick={() => removeItem(item.productId)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>

                    <div className="mt-4 flex items-center justify-between gap-4 flex-wrap">
                      <QuantityStepper
                        value={item.quantity}
                        onChange={(qty) => updateQuantity(item.productId, qty)}
                        size="sm"
                      />
                      <div className="text-left">
                        <p className="text-sm text-muted-foreground">
                          {item.price.toLocaleString('fa-IR')} × {item.quantity}
                        </p>
                        <p className="font-bold text-primary">
                          {(item.price * item.quantity).toLocaleString('fa-IR')} تومان
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="lg:col-span-1">
            <div className="bg-card rounded-2xl border border-border p-6 sticky top-20 space-y-4">
              <h3 className="font-semibold text-foreground text-lg">خلاصه سفارش</h3>

              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <span className="text-muted-foreground">تعداد اقلام:</span>
                  <span className="font-medium text-foreground">{items.length} مورد</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <span className="text-muted-foreground">تعداد کل پک‌ها:</span>
                  <span className={`font-medium ${isMinQuantityMet ? 'text-success' : 'text-warning'}`}>
                    {totalQuantity} عدد
                  </span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-muted-foreground">جمع کل:</span>
                  <span className="font-bold text-xl text-primary">
                    {totalPrice.toLocaleString('fa-IR')} تومان
                  </span>
                </div>
              </div>

              {!isMinQuantityMet && (
                <RuleAlert
                  type="error"
                  message={`حداقل تعداد سفارش ${minQuantityRequired} عدد است. ${minQuantityRequired - totalQuantity} عدد دیگر اضافه کنید.`}
                />
              )}

              <Link to={isMinQuantityMet ? '/checkout' : '#'}>
                <Button
                  variant="gold"
                  size="lg"
                  className="w-full gap-2"
                  disabled={!isMinQuantityMet}
                >
                  ادامه خرید
                  <ArrowLeft className="w-5 h-5" />
                </Button>
              </Link>

              <Link to="/shop">
                <Button variant="outline" className="w-full">
                  ادامه خرید از فروشگاه
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
