import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useCart } from '@/contexts/CartContext';
import { useCustomerAuth } from '@/contexts/CustomerAuthContext';
import { storage } from '@/lib/storage';
import { notifySuccess } from '@/lib/notify';
import type { Order } from '@/types/domain';
import { CalendarDays, LogOut, MapPin, PackageCheck, ShoppingBag, UserRound } from 'lucide-react';

const statusLabels: Record<Order['status'], string> = {
  pending: 'در انتظار تایید',
  confirmed: 'تایید شده',
  preparing: 'در حال آماده سازی',
  shipped: 'ارسال شده',
  delivered: 'تحویل شده',
};

export default function CustomerDashboardPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { customer, isAuthenticated, logout, updateProfile } = useCustomerAuth();
  const { totalItems, totalQuantity, totalPrice } = useCart();
  const [orders, setOrders] = useState<Order[]>([]);
  const [form, setForm] = useState({
    fullName: '',
    username: '',
    email: '',
    phone: '',
    province: '',
    address: '',
  });

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (!customer) return;
    setForm({
      fullName: customer.fullName,
      username: customer.username,
      email: customer.email,
      phone: customer.phone,
      province: customer.province,
      address: customer.address,
    });
  }, [customer]);

  useEffect(() => {
    const savedOrders = storage.getOrders();
    setOrders(Array.isArray(savedOrders) ? (savedOrders as Order[]) : []);
  }, []);

  const matchedOrders = useMemo(() => {
    if (!customer) return [];
    return orders.filter((order) => {
      const phoneMatch = customer.phone && order.customer.phone === customer.phone;
      const nameMatch = customer.fullName && order.customer.name === customer.fullName;
      return phoneMatch || nameMatch;
    });
  }, [customer, orders]);

  if (!customer) return null;

  const activeTab = location.pathname.includes('profile') ? 'profile' : 'dashboard';
  const initials = customer.fullName.trim().slice(0, 1) || customer.username.slice(0, 1).toUpperCase();

  const handleSave = (event: React.FormEvent) => {
    event.preventDefault();
    updateProfile(form);
    notifySuccess('پروفایل ذخیره شد');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <AppShell>
      <SEO pageKey="customer-dashboard" path={activeTab === 'profile' ? '/profile' : '/dashboard'} noindex={true} />
      <div className="container py-8">
        <section className="mb-8 rounded-2xl border border-primary/20 bg-card p-6 shadow-soft">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16 border-2 border-primary/20">
                <AvatarFallback className="gold-gradient text-xl font-bold text-primary-foreground">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div>
                <p className="text-sm text-muted-foreground">حساب مشتری</p>
                <h1 className="text-2xl font-bold text-foreground md:text-3xl">{customer.fullName}</h1>
                <p className="mt-1 text-sm text-muted-foreground" dir="ltr">
                  @{customer.username} · {customer.email}
                </p>
              </div>
            </div>
            <Button variant="outline" className="gap-2" onClick={handleLogout}>
              <LogOut className="h-4 w-4" />
              خروج
            </Button>
          </div>
        </section>

        <Tabs value={activeTab} onValueChange={(value) => navigate(value === 'profile' ? '/profile' : '/dashboard')} dir="rtl">
          <TabsList className="mb-6 grid h-11 w-full max-w-md grid-cols-2">
            <TabsTrigger value="dashboard">داشبورد</TabsTrigger>
            <TabsTrigger value="profile">پروفایل</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              {[
                { label: 'سفارش‌های من', value: matchedOrders.length.toLocaleString('fa-IR'), icon: PackageCheck },
                { label: 'محصول در سبد', value: totalQuantity.toLocaleString('fa-IR'), icon: ShoppingBag },
                { label: 'مبلغ سبد', value: `${totalPrice.toLocaleString('fa-IR')} تومان`, icon: CalendarDays },
              ].map((item) => (
                <Card key={item.label} className="rounded-2xl">
                  <CardContent className="flex items-center justify-between p-5">
                    <div>
                      <p className="text-sm text-muted-foreground">{item.label}</p>
                      <p className="mt-2 text-2xl font-bold text-foreground">{item.value}</p>
                    </div>
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <item.icon className="h-6 w-6" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              <Card className="rounded-2xl">
                <CardHeader>
                  <CardTitle className="text-xl">آخرین سفارش‌ها</CardTitle>
                </CardHeader>
                <CardContent>
                  {matchedOrders.length ? (
                    <div className="space-y-3">
                      {matchedOrders.slice(0, 4).map((order) => (
                        <Link
                          key={order.id}
                          to={`/order/${order.id}`}
                          className="flex items-center justify-between rounded-xl border border-border bg-background p-4 transition-colors hover:border-primary/40"
                        >
                          <div>
                            <p className="font-semibold text-foreground" dir="ltr">
                              {order.id}
                            </p>
                            <p className="mt-1 text-sm text-muted-foreground">
                              {order.items.length.toLocaleString('fa-IR')} آیتم · {order.total.toLocaleString('fa-IR')} تومان
                            </p>
                          </div>
                          <Badge variant="secondary">{statusLabels[order.status]}</Badge>
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-dashed border-border bg-background p-6 text-center">
                      <PackageCheck className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
                      <p className="font-semibold text-foreground">هنوز سفارشی برای این پروفایل ندارید</p>
                      <p className="mt-2 text-sm text-muted-foreground">پس از ثبت سفارش با همین نام یا شماره، اینجا نمایش داده می‌شود</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="rounded-2xl">
                <CardHeader>
                  <CardTitle className="text-xl">میانبرهای سریع</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Link to="/pack">
                    <Button variant="gold" className="w-full justify-start gap-2">
                      <ShoppingBag className="h-4 w-4" />
                      خرید محصولات
                    </Button>
                  </Link>
                  <Link to={totalItems ? '/cart' : '/builder'}>
                    <Button variant="outline" className="w-full justify-start gap-2">
                      <PackageCheck className="h-4 w-4" />
                      {totalItems ? 'مشاهده سبد خرید' : 'ساخت پک اختصاصی'}
                    </Button>
                  </Link>
                  <Link to="/track">
                    <Button variant="outline" className="w-full justify-start gap-2">
                      <CalendarDays className="h-4 w-4" />
                      پیگیری سفارش با کد
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="profile">
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl">
                  <UserRound className="h-5 w-5 text-primary" />
                  اطلاعات پروفایل
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSave} className="grid gap-5 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="fullName">نام و نام خانوادگی</Label>
                    <Input id="fullName" value={form.fullName} onChange={(event) => setForm({ ...form, fullName: event.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="username">نام کاربری</Label>
                    <Input id="username" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} dir="ltr" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">ایمیل</Label>
                    <Input id="email" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} dir="ltr" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">شماره موبایل</Label>
                    <Input id="phone" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} placeholder="09123456789" dir="ltr" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="province">استان</Label>
                    <Input id="province" value={form.province} onChange={(event) => setForm({ ...form, province: event.target.value })} />
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="address" className="flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-primary" />
                      آدرس پیش فرض
                    </Label>
                    <Input id="address" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
                  </div>
                  <div className="md:col-span-2">
                    <Button type="submit" variant="gold" size="lg">
                      ذخیره پروفایل
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  );
}
