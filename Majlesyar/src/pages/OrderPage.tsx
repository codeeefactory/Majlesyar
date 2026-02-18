import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Button } from '@/components/ui/button';
import { OrderTimeline } from '@/components/OrderTimeline';
import { getOrder, isAdminLoggedIn, updateOrderStatus } from '@/lib/api';
import type { Order } from '@/types/domain';
import { Package, MapPin, Calendar, Clock, Phone, ArrowRight, ChevronDown } from 'lucide-react';

export default function OrderPage() {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [canSimulateStatus, setCanSimulateStatus] = useState(false);

  useEffect(() => {
    const loadOrder = async () => {
      if (!id) return;
      const data = await getOrder(id);
      setOrder(data);
      setLoading(false);
    };
    loadOrder();
  }, [id]);

  useEffect(() => {
    const loadSimulationPermission = async () => {
      if (!import.meta.env.DEV) {
        setCanSimulateStatus(false);
        return;
      }
      const isAdmin = await isAdminLoggedIn();
      setCanSimulateStatus(isAdmin);
    };
    loadSimulationPermission();
  }, []);

  const simulateNextStatus = async () => {
    if (!order) return;

    const statusOrder: Order['status'][] = ['pending', 'confirmed', 'preparing', 'shipped', 'delivered'];
    const currentIndex = statusOrder.indexOf(order.status);
    
    if (currentIndex < statusOrder.length - 1) {
      setSimulating(true);
      const nextStatus = statusOrder[currentIndex + 1];
      const updated = await updateOrderStatus(order.id, nextStatus);
      if (updated) {
        setOrder(updated);
      }
      setSimulating(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="container py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 w-64 bg-muted rounded" />
            <div className="h-20 bg-muted rounded-xl" />
            <div className="grid md:grid-cols-2 gap-6">
              <div className="h-40 bg-muted rounded-xl" />
              <div className="h-40 bg-muted rounded-xl" />
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  if (!order) {
    return (
      <AppShell>
        <div className="container py-16 text-center">
          <div className="text-6xl mb-4">🔍</div>
          <h1 className="text-2xl font-bold text-foreground mb-4">سفارش یافت نشد</h1>
          <p className="text-muted-foreground mb-6">
            کد سفارش وارد شده معتبر نیست
          </p>
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

  const statusLabels: Record<Order['status'], string> = {
    pending: 'در انتظار تایید',
    confirmed: 'تایید شده',
    preparing: 'در حال آماده‌سازی',
    shipped: 'ارسال شده',
    delivered: 'تحویل داده شده',
  };

  return (
    <AppShell>
      <SEO
        title={`سفارش ${order.id}`}
        description="مشاهده جزئیات و وضعیت سفارش"
        path={`/order/${order.id}`}
        noindex={true}
      />
      <div className="container py-8">
        {/* Header */}
        <div className="mb-8">
          <Link to="/" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 mb-4">
            <ArrowRight className="w-4 h-4" />
            بازگشت به خانه
          </Link>
          
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-1">
                سفارش {order.id}
              </h1>
              <p className="text-muted-foreground">
                ثبت شده در {new Date(order.createdAt).toLocaleDateString('fa-IR')}
              </p>
            </div>
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold ${
              order.status === 'delivered' ? 'bg-success/10 text-success' :
              order.status === 'shipped' ? 'bg-primary/10 text-primary' :
              'bg-muted text-muted-foreground'
            }`}>
              <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
              {statusLabels[order.status]}
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="bg-card rounded-2xl border border-border p-6 mb-8">
          <h2 className="font-semibold text-foreground mb-6">وضعیت سفارش</h2>
          <OrderTimeline currentStatus={order.status} />
          
          {/* Dev mode: Simulate status change */}
          {canSimulateStatus && order.status !== 'delivered' && (
            <div className="mt-6 pt-4 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={simulateNextStatus}
                disabled={simulating}
                className="gap-2"
              >
                <ChevronDown className="w-4 h-4" />
                {simulating ? 'در حال به‌روزرسانی...' : 'شبیه‌سازی مرحله بعد (حالت توسعه)'}
              </Button>
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Order Items */}
          <div className="bg-card rounded-2xl border border-border p-6">
            <h2 className="font-semibold text-foreground mb-4 flex items-center gap-2">
              <Package className="w-5 h-5 text-primary" />
              اقلام سفارش
            </h2>
            
            <div className="space-y-3">
              {order.items.map((item, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                  <div>
                    <p className="font-medium text-foreground">{item.name}</p>
                    {item.isCustomPack && item.customConfig && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {Object.values(item.customConfig).flat().filter(Boolean).slice(0, 3).map((c, i) => (
                          <span key={i} className="text-xs bg-muted text-muted-foreground px-1.5 py-0.5 rounded">
                            {c}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="text-left">
                    <p className="font-medium text-foreground">{item.quantity} عدد</p>
                    <p className="text-sm text-muted-foreground">
                      {(item.price * item.quantity).toLocaleString('fa-IR')} تومان
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
              <span className="font-semibold text-foreground">جمع کل:</span>
              <span className="font-bold text-xl text-primary">
                {order.total.toLocaleString('fa-IR')} تومان
              </span>
            </div>
          </div>

          {/* Delivery Info */}
          <div className="bg-card rounded-2xl border border-border p-6">
            <h2 className="font-semibold text-foreground mb-4 flex items-center gap-2">
              <MapPin className="w-5 h-5 text-primary" />
              اطلاعات تحویل
            </h2>

            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
                  <Phone className="w-5 h-5 text-muted-foreground" />
                </div>
                <div>
                  <p className="font-medium text-foreground">{order.customer.name}</p>
                  <p className="text-sm text-muted-foreground" dir="ltr">{order.customer.phone}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
                  <MapPin className="w-5 h-5 text-muted-foreground" />
                </div>
                <div>
                  <p className="font-medium text-foreground">{order.customer.province}</p>
                  <p className="text-sm text-muted-foreground">{order.customer.address}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
                  <Calendar className="w-5 h-5 text-muted-foreground" />
                </div>
                <div>
                  <p className="font-medium text-foreground">
                    {new Date(order.delivery.date).toLocaleDateString('fa-IR')}
                  </p>
                  <p className="text-sm text-muted-foreground flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    بازه {order.delivery.window}
                  </p>
                </div>
              </div>

              {order.customer.notes && (
                <div className="bg-muted p-3 rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium">توضیحات: </span>
                    {order.customer.notes}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
