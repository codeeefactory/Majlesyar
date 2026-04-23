import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Package, LogOut, Search, Eye, Upload, Sparkles, DatabaseZap, CheckCircle2, LayoutTemplate } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAdminAuth } from "@/contexts/AdminAuthContext";
import { listOrders, type OfflineSessionImportResult, uploadOfflineSessionBundle } from "@/lib/api";
import { notifyError, notifySuccess } from "@/lib/notify";
import type { Order } from "@/types/domain";

export default function AdminOrdersPage() {
  const navigate = useNavigate();
  const { logout, isAuthenticated, loading: authLoading } = useAdminAuth();

  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sessionFile, setSessionFile] = useState<File | null>(null);
  const [uploadingSession, setUploadingSession] = useState(false);
  const [sessionImportResult, setSessionImportResult] = useState<OfflineSessionImportResult | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/admin/login");
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
      void loadOrders();
    }
  }, [authLoading, isAuthenticated]);

  const handleLogout = async () => {
    await logout();
    navigate("/admin/login");
  };

  const handleSessionUpload = async () => {
    if (!sessionFile) {
      notifyError("ابتدا فایل نشست آفلاین را انتخاب کنید.");
      return;
    }

    setUploadingSession(true);
    try {
      const result = await uploadOfflineSessionBundle(sessionFile);
      setSessionImportResult(result);
      notifySuccess("تغییرات نشست آفلاین با موفقیت روی وب‌سایت اعمال شد.");
      setOrders(await listOrders());
    } catch (error) {
      notifyError(error instanceof Error ? error.message : "بارگذاری نشست آفلاین انجام نشد.");
    } finally {
      setUploadingSession(false);
    }
  };

  const filteredOrders = orders.filter((order) => {
    const matchesSearch =
      search === "" ||
      order.id.toLowerCase().includes(search.toLowerCase()) ||
      order.customer.phone.includes(search);
    const matchesStatus = statusFilter === "all" || order.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusLabels: Record<string, string> = {
    pending: "در انتظار",
    confirmed: "تایید شده",
    preparing: "آماده‌سازی",
    shipped: "ارسال شده",
    delivered: "تحویل شده",
  };

  const sessionSummary = useMemo(() => {
    if (!sessionImportResult) return [];
    return [
      { label: "اکشن‌های اعمال‌شده", value: sessionImportResult.applied_actions },
      { label: "مشتری جدید", value: sessionImportResult.clients_created },
      { label: "مشتری به‌روزشده", value: sessionImportResult.clients_updated },
      { label: "فاکتور جدید", value: sessionImportResult.invoices_created },
      { label: "فاکتور به‌روزشده", value: sessionImportResult.invoices_updated },
    ];
  }, [sessionImportResult]);

  if (authLoading) {
    return <div className="min-h-screen flex items-center justify-center">در حال بارگذاری...</div>;
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="gold-gradient flex h-10 w-10 items-center justify-center rounded-xl">
              <Package className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-foreground">پنل مدیریت مجلس‌یار</span>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/admin/page-products">
              <Button variant="ghost" size="sm" className="gap-2">
                <LayoutTemplate className="h-4 w-4" />
                چیدمان صفحات
              </Button>
            </Link>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-2">
              <LogOut className="h-4 w-4" />
              خروج
            </Button>
          </div>
        </div>
      </header>

      <main className="container py-8">
        <h1 className="mb-6 text-2xl font-bold text-foreground">سفارش‌ها و همگام‌سازی آفلاین</h1>

        <Card className="mb-6 overflow-hidden border-primary/20 shadow-xl shadow-primary/5">
          <CardHeader className="bg-gradient-to-br from-primary/15 via-card to-secondary/40">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 rounded-full bg-background/80 px-3 py-1 text-sm text-primary">
                  <Sparkles className="h-4 w-4" />
                  درگاه نشست آفلاین اپلیکیشن دسکتاپ
                </div>
                <CardTitle className="text-xl">اعمال تغییرات ذخیره‌شده از اپلیکیشن دسکتاپ روی وب‌سایت</CardTitle>
                <CardDescription className="max-w-2xl leading-7">
                  فایل نشست آفلاین ساخته‌شده در اپلیکیشن MajlesYar Desktop را بارگذاری کنید تا تغییرات صف آفلاین
                  روی بک‌اند و پنل وب اعمال شود. این بخش برای انتقال کار از سیستم‌های بدون اینترنت یا سیستم‌های دیگر
                  طراحی شده است.
                </CardDescription>
              </div>
              <div className="rounded-2xl bg-primary/10 p-4 text-primary">
                <DatabaseZap className="h-8 w-8" />
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-5 pt-6">
            <div className="grid gap-4 lg:grid-cols-[1.5fr_auto] lg:items-end">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-foreground">فایل نشست آفلاین</label>
                <Input
                  type="file"
                  accept=".majlesyar-session,.json,application/json"
                  onChange={(event) => setSessionFile(event.target.files?.[0] ?? null)}
                  className="h-12 cursor-pointer border-dashed border-primary/30 bg-primary/5 file:ml-4 file:rounded-lg file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary-foreground hover:bg-primary/10"
                />
                <p className="text-sm text-muted-foreground">
                  فرمت‌های مجاز: <span className="font-mono">.majlesyar-session</span> و{" "}
                  <span className="font-mono">.json</span>
                </p>
              </div>

              <Button
                onClick={handleSessionUpload}
                disabled={!sessionFile || uploadingSession}
                className="h-12 min-w-56 gap-2"
              >
                <Upload className="h-4 w-4" />
                {uploadingSession ? "در حال اعمال..." : "اعمال تغییرات روی وب‌سایت"}
              </Button>
            </div>

            {sessionFile ? (
              <div className="rounded-2xl border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                فایل انتخاب‌شده: <span className="font-medium text-foreground">{sessionFile.name}</span>
              </div>
            ) : null}

            {sessionSummary.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                {sessionSummary.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4">
                    <div className="mb-2 inline-flex rounded-full bg-emerald-100 p-2 text-emerald-700">
                      <CheckCircle2 className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-bold text-emerald-800">
                      {item.value.toLocaleString("fa-IR")}
                    </div>
                    <div className="mt-1 text-sm text-emerald-700">{item.label}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="mb-6 flex flex-col gap-4 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute right-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="جستجو با کد سفارش یا موبایل..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="pr-10"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="h-11 rounded-lg border border-input bg-background px-4"
          >
            <option value="all">همه وضعیت‌ها</option>
            {Object.entries(statusLabels).map(([key, value]) => (
              <option key={key} value={key}>
                {value}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="py-8 text-center text-muted-foreground">در حال بارگذاری...</div>
        ) : filteredOrders.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">سفارشی یافت نشد</div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted">
                  <tr>
                    <th className="p-4 text-right font-semibold text-foreground">کد سفارش</th>
                    <th className="p-4 text-right font-semibold text-foreground">مشتری</th>
                    <th className="p-4 text-right font-semibold text-foreground">مبلغ</th>
                    <th className="p-4 text-right font-semibold text-foreground">وضعیت</th>
                    <th className="p-4 text-right font-semibold text-foreground">تاریخ</th>
                    <th className="p-4" />
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map((order) => (
                    <tr key={order.id} className="border-t border-border hover:bg-muted/50">
                      <td className="p-4 font-mono text-sm">{order.id}</td>
                      <td className="p-4">
                        <div className="text-foreground">{order.customer.name}</div>
                        <div className="text-sm text-muted-foreground" dir="ltr">
                          {order.customer.phone}
                        </div>
                      </td>
                      <td className="p-4 font-semibold text-primary">
                        {order.total.toLocaleString("fa-IR")}
                      </td>
                      <td className="p-4">
                        <span className="rounded-full bg-muted px-2 py-1 text-xs">{statusLabels[order.status]}</span>
                      </td>
                      <td className="p-4 text-sm text-muted-foreground">
                        {new Date(order.createdAt).toLocaleDateString("fa-IR")}
                      </td>
                      <td className="p-4">
                        <Link to={`/admin/orders/${order.id}`}>
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
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
