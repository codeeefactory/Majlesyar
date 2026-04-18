import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { RuleAlert } from '@/components/RuleAlert';
import { JalaliDatePicker } from '@/components/JalaliDatePicker';
import { useCart } from '@/contexts/CartContext';
import { useSettings } from '@/contexts/SettingsContext';
import { createOrder } from '@/lib/api';
import { notifyError, notifySuccess } from '@/lib/notify';
import { allProvinces } from '@/data/siteConstants';
import { ArrowRight, Check, Loader2 } from 'lucide-react';

export default function CheckoutPage() {
  const navigate = useNavigate();
  const { items, totalPrice, totalQuantity, isMinQuantityMet, clearCart, minQuantityRequired } = useCart();
  const { settings } = useSettings();
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    name: '',
    phone: '',
    province: '',
    address: '',
    date: '',
    window: settings.deliveryWindows[0] || '',
    notes: '',
    paymentMethod: 'pay-later',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Calculate minimum delivery date (today + leadTimeHours)
  const getMinDeliveryDate = () => {
    const today = new Date();
    const minDate = new Date(today.getTime() + settings.leadTimeHours * 60 * 60 * 1000);
    return minDate.toISOString().split('T')[0];
  };

  const isProvinceAllowed = settings.allowedProvinces.includes(form.province);
  const isDateValid = form.date >= getMinDeliveryDate();

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!form.name.trim()) newErrors.name = 'نام و نام خانوادگی الزامی است';
    if (!form.phone.trim()) newErrors.phone = 'شماره موبایل الزامی است';
    else if (!/^09\d{9}$/.test(form.phone)) newErrors.phone = 'شماره موبایل نامعتبر است';
    if (!form.province) newErrors.province = 'استان را انتخاب کنید';
    else if (!isProvinceAllowed) newErrors.province = `\u062f\u0631 \u062d\u0627\u0644 \u062d\u0627\u0636\u0631 \u0627\u0645\u06a9\u0627\u0646 \u0627\u0631\u0633\u0627\u0644 \u0641\u0642\u0637 \u062f\u0631 ${settings.allowedProvinces.join(' \u0648 ')} \u0641\u0631\u0627\u0647\u0645 \u0627\u0633\u062a`;
    if (!form.address.trim()) newErrors.address = 'آدرس کامل الزامی است';
    if (!form.date) newErrors.date = 'تاریخ تحویل را انتخاب کنید';
    else if (!isDateValid) newErrors.date = `\u062a\u0627\u0631\u06cc\u062e \u062a\u062d\u0648\u06cc\u0644 \u0628\u0627\u06cc\u062f \u062d\u062f\u0627\u0642\u0644 ${settings.leadTimeHours} \u0633\u0627\u0639\u062a \u0628\u0639\u062f \u0628\u0627\u0634\u062f`;
    if (!form.window) newErrors.window = 'بازه زمانی تحویل را انتخاب کنید';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;
    if (!isMinQuantityMet) {
      notifyError('حداقل تعداد سفارش رعایت نشده است');
      return;
    }

    setLoading(true);

    try {
      const order = await createOrder(
        items,
        {
          name: form.name,
          phone: form.phone,
          province: form.province,
          address: form.address,
          notes: form.notes || undefined,
        },
        {
          date: form.date,
          window: form.window,
        },
        form.paymentMethod
      );

      clearCart();
      notifySuccess('سفارش شما با موفقیت ثبت شد');
      navigate(`/order/${order.id}`);
    } catch {
      notifyError('خطا در ثبت سفارش. لطفا دوباره تلاش کنید.');
    } finally {
      setLoading(false);
    }
  };

  if (items.length === 0) {
    return (
      <AppShell>
        <div className="container py-16 text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">سبد خرید خالی است</h1>
          <Link to="/shop">
            <Button variant="gold">رفتن به فروشگاه</Button>
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <SEO
        pageKey="checkout"
        path="/checkout"
        noindex={true}
      />
      <div className="container py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-8">
          <Link to="/cart" className="hover:text-foreground transition-colors flex items-center gap-1">
            <ArrowRight className="w-4 h-4" />
            سبد خرید
          </Link>
          <span>/</span>
          <span className="text-foreground">تکمیل سفارش</span>
        </nav>

        <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-8">تکمیل سفارش</h1>

        <form onSubmit={handleSubmit} className="grid lg:grid-cols-3 gap-8">
          {/* Form Fields */}
          <div className="lg:col-span-2 space-y-6">
            {/* Personal Info */}
            <div className="bg-card rounded-2xl border border-border p-6 space-y-4">
              <h2 className="font-semibold text-foreground text-lg">اطلاعات گیرنده</h2>

              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">نام و نام خانوادگی *</Label>
                  <Input
                    id="name"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="محمد محمدی"
                    className={errors.name ? 'border-destructive' : ''}
                  />
                  {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">شماره موبایل *</Label>
                  <Input
                    id="phone"
                    type="tel"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="09123456789"
                    className={errors.phone ? 'border-destructive' : ''}
                    dir="ltr"
                  />
                  {errors.phone && <p className="text-xs text-destructive">{errors.phone}</p>}
                </div>
              </div>
            </div>

            {/* Address */}
            <div className="bg-card rounded-2xl border border-border p-6 space-y-4">
              <h2 className="font-semibold text-foreground text-lg">آدرس تحویل</h2>

              <div className="space-y-2">
                <Label htmlFor="province">استان *</Label>
                <select
                  id="province"
                  value={form.province}
                  onChange={(e) => setForm({ ...form, province: e.target.value })}
                  className={`w-full h-11 px-4 rounded-lg border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring ${
                    errors.province ? 'border-destructive' : 'border-input'
                  }`}
                >
                  <option value="">انتخاب استان</option>
                  {allProvinces.map((p) => (
                    <option key={p} value={p}>
                      {p} {!settings.allowedProvinces.includes(p) && '(فعلاً پشتیبانی نمی‌شود)'}
                    </option>
                  ))}
                </select>
                {errors.province && <p className="text-xs text-destructive">{errors.province}</p>}
                {form.province && !isProvinceAllowed && (
                  <RuleAlert
                    type="warning"
                    message={`\u062f\u0631 \u062d\u0627\u0644 \u062d\u0627\u0636\u0631 \u0627\u0645\u06a9\u0627\u0646 \u0627\u0631\u0633\u0627\u0644 \u0641\u0642\u0637 \u062f\u0631 ${settings.allowedProvinces.join(' \u0648 ')} \u0641\u0631\u0627\u0647\u0645 \u0627\u0633\u062a`}
                  />
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="address">آدرس کامل *</Label>
                <Textarea
                  id="address"
                  value={form.address}
                  onChange={(e) => setForm({ ...form, address: e.target.value })}
                  placeholder="خیابان، کوچه، پلاک، واحد..."
                  rows={3}
                  className={errors.address ? 'border-destructive' : ''}
                />
                {errors.address && <p className="text-xs text-destructive">{errors.address}</p>}
              </div>
            </div>

            {/* Delivery */}
            <div className="bg-card rounded-2xl border border-border p-6 space-y-4">
              <h2 className="font-semibold text-foreground text-lg">زمان تحویل</h2>

              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="date">تاریخ تحویل *</Label>
                  <JalaliDatePicker
                    value={form.date}
                    onChange={(date) => setForm({ ...form, date })}
                    minDate={getMinDeliveryDate()}
                    placeholder="انتخاب تاریخ تحویل"
                    hasError={!!errors.date}
                  />
                  {errors.date && <p className="text-xs text-destructive">{errors.date}</p>}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="window">بازه زمانی *</Label>
                  <select
                    id="window"
                    value={form.window}
                    onChange={(e) => setForm({ ...form, window: e.target.value })}
                    className={`w-full h-11 px-4 rounded-lg border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring ${
                      errors.window ? 'border-destructive' : 'border-input'
                    }`}
                    dir="ltr"
                  >
                    {settings.deliveryWindows.map((w) => (
                      <option key={w} value={w}>{w}</option>
                    ))}
                  </select>
                  {errors.window && <p className="text-xs text-destructive">{errors.window}</p>}
                </div>
              </div>

              <RuleAlert
                type="info"
                message={`\u062a\u0627\u0631\u06cc\u062e \u062a\u062d\u0648\u06cc\u0644 \u0628\u0627\u06cc\u062f \u062d\u062f\u0627\u0642\u0644 ${settings.leadTimeHours} \u0633\u0627\u0639\u062a \u0628\u0639\u062f \u0627\u0632 \u0632\u0645\u0627\u0646 \u062b\u0628\u062a \u0633\u0641\u0627\u0631\u0634 \u0628\u0627\u0634\u062f`}
              />
            </div>

            {/* Notes & Payment */}
            <div className="bg-card rounded-2xl border border-border p-6 space-y-4">
              <h2 className="font-semibold text-foreground text-lg">توضیحات و پرداخت</h2>

              <div className="space-y-2">
                <Label htmlFor="notes">توضیحات (اختیاری)</Label>
                <Textarea
                  id="notes"
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="توضیحات اضافی برای سفارش..."
                  rows={2}
                />
              </div>

              <div className="space-y-2">
                <Label>روش پرداخت</Label>
                <div className="space-y-2">
                  {settings.paymentMethods.map((method) => (
                    <label
                      key={method.id}
                      className={`flex items-center gap-3 p-4 rounded-xl border-2 cursor-pointer transition-all ${
                        form.paymentMethod === method.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border bg-card'
                      } ${!method.enabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <input
                        type="radio"
                        name="paymentMethod"
                        value={method.id}
                        checked={form.paymentMethod === method.id}
                        onChange={(e) => setForm({ ...form, paymentMethod: e.target.value })}
                        disabled={!method.enabled}
                        className="sr-only"
                      />
                      <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                        form.paymentMethod === method.id
                          ? 'bg-primary border-primary text-primary-foreground'
                          : 'border-muted-foreground'
                      }`}>
                        {form.paymentMethod === method.id && <Check className="w-3 h-3" />}
                      </div>
                      <span className="font-medium text-foreground">{method.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Summary Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-card rounded-2xl border border-border p-6 sticky top-20 space-y-4">
              <h3 className="font-semibold text-foreground text-lg">خلاصه سفارش</h3>

              <div className="space-y-2 max-h-48 overflow-y-auto">
                {items.map((item) => (
                  <div key={item.productId} className="flex items-center justify-between py-2 text-sm">
                    <span className="text-muted-foreground">{item.name} × {item.quantity}</span>
                    <span className="text-foreground">{(item.price * item.quantity).toLocaleString('fa-IR')}</span>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-border space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">تعداد کل پک‌ها:</span>
                  <span className="font-medium text-foreground">{totalQuantity} عدد</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">جمع کل:</span>
                  <span className="font-bold text-xl text-primary">
                    {totalPrice.toLocaleString('fa-IR')} تومان
                  </span>
                </div>
              </div>

              {!isMinQuantityMet && (
                <RuleAlert
                  type="error"
                  message={`\u062d\u062f\u0627\u0642\u0644 \u062a\u0639\u062f\u0627\u062f \u0633\u0641\u0627\u0631\u0634 ${minQuantityRequired.toLocaleString('fa-IR')} \u0639\u062f\u062f \u0627\u0633\u062a`}
                />
              )}

              <Button
                type="submit"
                variant="gold"
                size="lg"
                className="w-full gap-2"
                disabled={loading || !isMinQuantityMet || !isProvinceAllowed || !isDateValid}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    در حال ثبت...
                  </>
                ) : (
                  'ثبت سفارش'
                )}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
