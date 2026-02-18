import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getOrder } from '@/lib/api';
import { notifyError } from '@/lib/notify';
import { Search, Package } from 'lucide-react';

export default function TrackOrderPage() {
  const navigate = useNavigate();
  const [orderId, setOrderId] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!orderId.trim()) {
      notifyError('لطفا کد سفارش را وارد کنید');
      return;
    }

    setLoading(true);
    
    try {
      const order = await getOrder(orderId.trim());
      
      if (order) {
        navigate(`/order/${order.id}`);
      } else {
        notifyError('سفارشی با این کد یافت نشد');
      }
    } catch {
      notifyError('خطا در جستجوی سفارش');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <SEO
        title="پیگیری سفارش"
        description="پیگیری وضعیت سفارش پک‌های پذیرایی با کد سفارش"
        path="/track"
        breadcrumbs={[
          { name: 'خانه', url: '/' },
          { name: 'پیگیری سفارش', url: '/track' },
        ]}
      />
      <div className="container py-16">
        <div className="max-w-md mx-auto text-center">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl gold-gradient flex items-center justify-center shadow-glow">
            <Package className="w-10 h-10 text-primary-foreground" />
          </div>
          
          <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">
            پیگیری سفارش
          </h1>
          <p className="text-muted-foreground mb-8">
            کد سفارش خود را وارد کنید
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2 text-right">
              <Label htmlFor="orderId">کد سفارش</Label>
              <Input
                id="orderId"
                value={orderId}
                onChange={(e) => setOrderId(e.target.value)}
                placeholder="مثال: ORD-ABC123"
                className="text-center"
                dir="ltr"
              />
            </div>

            <Button
              type="submit"
              variant="gold"
              size="lg"
              className="w-full gap-2"
              disabled={loading}
            >
              {loading ? (
                'در حال جستجو...'
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  پیگیری سفارش
                </>
              )}
            </Button>
          </form>

          <p className="mt-8 text-sm text-muted-foreground">
            کد سفارش پس از ثبت سفارش به شما نمایش داده می‌شود
          </p>
        </div>
      </div>
    </AppShell>
  );
}
