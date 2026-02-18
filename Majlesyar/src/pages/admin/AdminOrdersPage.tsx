import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAdminAuth } from '@/contexts/AdminAuthContext';
import { listOrders } from '@/lib/api';
import type { Order } from '@/types/domain';
import { Package, LogOut, Search, Eye } from 'lucide-react';

export default function AdminOrdersPage() {
  const navigate = useNavigate();
  const { logout, isAuthenticated, loading: authLoading } = useAdminAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/admin/login');
    }
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    const loadOrders = async () => {
      if (!isAuthenticated) {
        setLoading(false);
        return;
      }
      try {
        const data = await listOrders();
        setOrders(data);
      } finally {
        setLoading(false);
      }
    };
    if (!authLoading) {
      loadOrders();
    }
  }, [authLoading, isAuthenticated]);

  const handleLogout = async () => {
    await logout();
    navigate('/admin/login');
  };

  const filteredOrders = orders.filter((order) => {
    const matchesSearch = search === '' || 
      order.id.toLowerCase().includes(search.toLowerCase()) ||
      order.customer.phone.includes(search);
    const matchesStatus = statusFilter === 'all' || order.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusLabels: Record<string, string> = {
    pending: 'در انتظار', confirmed: 'تایید شده', preparing: 'آماده‌سازی', shipped: 'ارسال شده', delivered: 'تحویل شده'
  };

  if (authLoading) return <div className="min-h-screen flex items-center justify-center">در حال بارگذاری...</div>;

  return (
    <div className="min-h-screen bg-background">
      <header className="bg-card border-b border-border sticky top-0 z-50">
        <div className="container flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gold-gradient flex items-center justify-center">
              <Package className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-foreground">پنل مدیریت</span>
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-2">
            <LogOut className="w-4 h-4" />
            خروج
          </Button>
        </div>
      </header>

      <main className="container py-8">
        <h1 className="text-2xl font-bold text-foreground mb-6">سفارش‌ها</h1>

        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input placeholder="جستجو با کد سفارش یا موبایل..." value={search} onChange={(e) => setSearch(e.target.value)} className="pr-10" />
          </div>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="h-11 px-4 rounded-lg border border-input bg-background">
            <option value="all">همه وضعیت‌ها</option>
            {Object.entries(statusLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-8 text-muted-foreground">در حال بارگذاری...</div>
        ) : filteredOrders.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">سفارشی یافت نشد</div>
        ) : (
          <div className="bg-card rounded-xl border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted">
                  <tr>
                    <th className="text-right p-4 font-semibold text-foreground">کد سفارش</th>
                    <th className="text-right p-4 font-semibold text-foreground">مشتری</th>
                    <th className="text-right p-4 font-semibold text-foreground">مبلغ</th>
                    <th className="text-right p-4 font-semibold text-foreground">وضعیت</th>
                    <th className="text-right p-4 font-semibold text-foreground">تاریخ</th>
                    <th className="p-4"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map((order) => (
                    <tr key={order.id} className="border-t border-border hover:bg-muted/50">
                      <td className="p-4 font-mono text-sm">{order.id}</td>
                      <td className="p-4">
                        <div className="text-foreground">{order.customer.name}</div>
                        <div className="text-sm text-muted-foreground" dir="ltr">{order.customer.phone}</div>
                      </td>
                      <td className="p-4 font-semibold text-primary">{order.total.toLocaleString('fa-IR')}</td>
                      <td className="p-4"><span className="px-2 py-1 rounded-full text-xs bg-muted">{statusLabels[order.status]}</span></td>
                      <td className="p-4 text-muted-foreground text-sm">{new Date(order.createdAt).toLocaleDateString('fa-IR')}</td>
                      <td className="p-4">
                        <Link to={`/admin/orders/${order.id}`}>
                          <Button variant="ghost" size="sm"><Eye className="w-4 h-4" /></Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
