import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowDown, ArrowUp, Eye, GripVertical, LayoutTemplate, LogOut, RefreshCcw, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAdminAuth } from "@/contexts/AdminAuthContext";
import {
  getAdminPageProductPlacementState,
  listAdminPagePreviewTargets,
  listProducts,
  saveAdminPageProductOrder,
} from "@/lib/api";
import { notifyError, notifySuccess } from "@/lib/notify";
import type { PagePreviewTarget, PageProductPlacementState, Product } from "@/types/domain";

function formatTargetLabel(target: PagePreviewTarget) {
  if (target.pageType === "event") {
    return `${target.pageTitle} / ${target.pageSlug}`;
  }

  return target.pageTitle;
}

export default function AdminPageProductsPage() {
  const navigate = useNavigate();
  const { logout, isAuthenticated, loading: authLoading } = useAdminAuth();

  const [targets, setTargets] = useState<PagePreviewTarget[]>([]);
  const [allProducts, setAllProducts] = useState<Product[]>([]);
  const [selectedPageKey, setSelectedPageKey] = useState("");
  const [placementState, setPlacementState] = useState<PageProductPlacementState | null>(null);
  const [workingProducts, setWorkingProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [stateLoading, setStateLoading] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/admin/login");
    }
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    const loadInitialState = async () => {
      if (!isAuthenticated) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const [loadedTargets, loadedProducts] = await Promise.all([
          listAdminPagePreviewTargets(),
          listProducts(),
        ]);
        setTargets(loadedTargets);
        setAllProducts(loadedProducts);
        setSelectedPageKey((current) => current || loadedTargets[0]?.pageKey || "");
      } catch (error) {
        notifyError(error instanceof Error ? error.message : "بارگذاری داده‌های چیدمان صفحات انجام نشد.");
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      void loadInitialState();
    }
  }, [authLoading, isAuthenticated]);

  const selectedTarget = useMemo(
    () => targets.find((target) => target.pageKey === selectedPageKey) ?? null,
    [selectedPageKey, targets],
  );

  useEffect(() => {
    const loadState = async () => {
      if (!selectedTarget || !isAuthenticated) return;

      setStateLoading(true);
      try {
        const state = await getAdminPageProductPlacementState(selectedTarget.pageType, selectedTarget.pageSlug);
        setPlacementState(state);
        setWorkingProducts(state.previewProducts);
      } catch (error) {
        notifyError(error instanceof Error ? error.message : "بارگذاری چیدمان صفحه انجام نشد.");
      } finally {
        setStateLoading(false);
      }
    };

    void loadState();
  }, [selectedTarget, isAuthenticated]);

  const availableProducts = useMemo(() => {
    const selectedIds = new Set(workingProducts.map((product) => product.id));
    return allProducts.filter((product) => !selectedIds.has(product.id));
  }, [allProducts, workingProducts]);

  const supportsExplicitSelection = selectedTarget?.pageType !== "shop";
  const isDirty =
    placementState !== null &&
    JSON.stringify(workingProducts.map((product) => product.id)) !==
      JSON.stringify(placementState.previewProducts.map((product) => product.id));

  const moveProduct = (index: number, direction: -1 | 1) => {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= workingProducts.length) return;

    setWorkingProducts((current) => {
      const next = [...current];
      const [moved] = next.splice(index, 1);
      next.splice(targetIndex, 0, moved);
      return next;
    });
  };

  const addProduct = (product: Product) => {
    if (!supportsExplicitSelection) return;
    setWorkingProducts((current) => [...current, product]);
  };

  const removeProduct = (productId: string) => {
    if (!supportsExplicitSelection) return;
    setWorkingProducts((current) => current.filter((product) => product.id !== productId));
  };

  const reloadPlacementState = async () => {
    if (!selectedTarget) return;
    const state = await getAdminPageProductPlacementState(selectedTarget.pageType, selectedTarget.pageSlug);
    setPlacementState(state);
    setWorkingProducts(state.previewProducts);
  };

  const handleSave = async () => {
    if (!selectedTarget) return;

    setSaving(true);
    try {
      const nextState = await saveAdminPageProductOrder(
        selectedTarget.pageType,
        selectedTarget.pageSlug,
        workingProducts.map((product) => product.id),
      );
      setPlacementState(nextState);
      setWorkingProducts(nextState.previewProducts);
      notifySuccess("چیدمان صفحه ذخیره شد و روی وب‌سایت اعمال شد.");
    } catch (error) {
      notifyError(error instanceof Error ? error.message : "ذخیره چیدمان صفحه انجام نشد.");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!selectedTarget) return;

    setSaving(true);
    try {
      const nextState = await saveAdminPageProductOrder(selectedTarget.pageType, selectedTarget.pageSlug, []);
      setPlacementState(nextState);
      setWorkingProducts(nextState.previewProducts);
      notifySuccess("چیدمان سفارشی پاک شد و صفحه به ترتیب پیش‌فرض برگشت.");
    } catch (error) {
      notifyError(error instanceof Error ? error.message : "بازگردانی به ترتیب پیش‌فرض انجام نشد.");
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/admin/login");
  };

  if (authLoading || loading) {
    return <div className="min-h-screen flex items-center justify-center">در حال بارگذاری...</div>;
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="gold-gradient flex h-10 w-10 items-center justify-center rounded-xl">
              <LayoutTemplate className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <div className="font-bold text-foreground">چیدمان محصولات صفحات</div>
              <div className="text-xs text-muted-foreground">مدیریت ترتیب نمایش در سایت و پیش‌نمایش</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/admin/orders">
              <Button variant="ghost" size="sm">بازگشت به سفارش‌ها</Button>
            </Link>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-2">
              <LogOut className="h-4 w-4" />
              خروج
            </Button>
          </div>
        </div>
      </header>

      <main className="container py-8 space-y-6">
        <Card className="border-primary/20 shadow-xl shadow-primary/5">
          <CardHeader className="bg-gradient-to-br from-primary/10 via-card to-secondary/30">
            <CardTitle>مدیریت ترتیب نمایش محصولات روی صفحات</CardTitle>
            <CardDescription>
              صفحه‌ی هدف را انتخاب کنید، محصولات را جابه‌جا کنید و همان لحظه پیش‌نمایش بچینید. ترتیب ذخیره‌شده روی
              وب‌سایت و اپ دسکتاپ یکسان خواهد بود.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid gap-4 lg:grid-cols-[1.2fr_auto_auto_auto]">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-foreground">صفحه / بخش هدف</label>
                <select
                  value={selectedPageKey}
                  onChange={(event) => setSelectedPageKey(event.target.value)}
                  className="h-11 w-full rounded-lg border border-input bg-background px-4"
                >
                  {targets.map((target) => (
                    <option key={target.pageKey} value={target.pageKey}>
                      {formatTargetLabel(target)}
                    </option>
                  ))}
                </select>
              </div>
              <Button variant="secondary" className="mt-7 gap-2" onClick={() => void reloadPlacementState()} disabled={!selectedTarget || stateLoading}>
                <RefreshCcw className="h-4 w-4" />
                تازه‌سازی
              </Button>
              <Button variant="outline" className="mt-7" onClick={handleReset} disabled={!selectedTarget || saving}>
                بازگشت به پیش‌فرض
              </Button>
              <Button variant="gold" className="mt-7 gap-2" onClick={handleSave} disabled={!selectedTarget || !isDirty || saving}>
                <Save className="h-4 w-4" />
                {saving ? "در حال ذخیره..." : "ذخیره چیدمان"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {selectedTarget ? (
          <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <Card className="overflow-hidden">
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle>{selectedTarget.pageTitle}</CardTitle>
                    <CardDescription>{selectedTarget.pageDescription || "این بخش برای مدیریت ترتیب نمایش محصولات استفاده می‌شود."}</CardDescription>
                  </div>
                  <a href={selectedTarget.routePath} target="_blank" rel="noreferrer">
                    <Button variant="ghost" size="sm" className="gap-2">
                      <Eye className="h-4 w-4" />
                      مشاهده صفحه
                    </Button>
                  </a>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="rounded-2xl border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                  {placementState?.usesCustomOrder
                    ? "این صفحه اکنون از چیدمان سفارشی استفاده می‌کند."
                    : "این صفحه هنوز روی ترتیب پیش‌فرض backend است."}
                </div>

                {stateLoading ? (
                  <div className="py-10 text-center text-muted-foreground">در حال بارگذاری چیدمان...</div>
                ) : workingProducts.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border p-8 text-center text-muted-foreground">
                    هنوز محصولی برای این صفحه انتخاب نشده است.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {workingProducts.map((product, index) => (
                      <div key={`${product.id}-${index}`} className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3">
                        <div className="rounded-xl bg-primary/10 p-2 text-primary">
                          <GripVertical className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="font-medium text-foreground">{product.name}</div>
                          <div className="text-xs text-muted-foreground">
                            جایگاه {index + 1} • {product.price ? `${product.price.toLocaleString("fa-IR")} تومان` : "قیمت توافقی"}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button variant="ghost" size="icon" onClick={() => moveProduct(index, -1)} disabled={index === 0}>
                            <ArrowUp className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => moveProduct(index, 1)}
                            disabled={index === workingProducts.length - 1}
                          >
                            <ArrowDown className="h-4 w-4" />
                          </Button>
                          {supportsExplicitSelection ? (
                            <Button variant="outline" size="sm" onClick={() => removeProduct(product.id)}>
                              حذف
                            </Button>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>پیش‌نمایش درون پنل</CardTitle>
                  <CardDescription>
                    این پنل نمای نزدیک‌تری از ترتیبی است که روی سایت نمایش داده می‌شود.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {workingProducts.map((product, index) => (
                      <div key={`preview-${product.id}-${index}`} className="rounded-2xl border border-border bg-muted/30 p-4">
                        <div className="mb-2 text-xs text-primary">ردیف {index + 1}</div>
                        <div className="font-semibold text-foreground">{product.name}</div>
                        <div className="mt-1 line-clamp-2 text-sm text-muted-foreground">{product.description || "بدون توضیح تکمیلی"}</div>
                        <div className="mt-3 text-sm text-foreground">
                          {product.price ? `${product.price.toLocaleString("fa-IR")} تومان` : "قیمت توافقی"}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {supportsExplicitSelection ? (
                <Card>
                  <CardHeader>
                    <CardTitle>افزودن محصول به این صفحه</CardTitle>
                    <CardDescription>
                      محصولات دلخواه را برای صفحه اصلی یا صفحات رویداد انتخاب و به انتهای ترتیب اضافه کنید.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {availableProducts.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-border p-6 text-center text-muted-foreground">
                        همه‌ی محصولات موجود همین حالا در چیدمان این صفحه قرار دارند.
                      </div>
                    ) : (
                      availableProducts.map((product) => (
                        <div key={`available-${product.id}`} className="flex items-center justify-between gap-3 rounded-2xl border border-border px-4 py-3">
                          <div className="min-w-0">
                            <div className="font-medium text-foreground">{product.name}</div>
                            <div className="truncate text-xs text-muted-foreground">{product.urlSlug}</div>
                          </div>
                          <Button variant="secondary" size="sm" onClick={() => addProduct(product)}>
                            افزودن
                          </Button>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>منطق صفحه فروشگاه</CardTitle>
                    <CardDescription>
                      در صفحه فروشگاه همه‌ی محصولات نمایش داده می‌شوند. اینجا فقط اولویت ردیف‌های ابتدایی را جابه‌جا می‌کنیم و backend بقیه‌ی محصولات را بعد از آن‌ها می‌چیند.
                    </CardDescription>
                  </CardHeader>
                </Card>
              )}
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
