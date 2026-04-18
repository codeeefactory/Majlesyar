import { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Button } from '@/components/ui/button';
import { RuleAlert } from '@/components/RuleAlert';
import { getBuilderConfig } from '@/lib/api';
import { notifySuccess } from '@/lib/notify';
import { useCart } from '@/contexts/CartContext';
import type { BuilderItem } from '@/types/domain';
import { ArrowRight, ArrowLeft, Check, Package, ShoppingCart } from 'lucide-react';

type Step = 'packaging' | 'fruit' | 'drink' | 'snack' | 'addons' | 'quantity';

const stepLabels: Record<Step, string> = {
  packaging: 'بسته‌بندی',
  fruit: 'میوه',
  drink: 'نوشیدنی',
  snack: 'کیک/اسنک',
  addons: 'افزودنی‌ها',
  quantity: 'تعداد',
};

const stepOrder: Step[] = ['packaging', 'fruit', 'drink', 'snack', 'addons', 'quantity'];

export default function BuilderPage() {
  const navigate = useNavigate();
  const { addItem, minQuantityRequired } = useCart();
  const [items, setItems] = useState<BuilderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState<Step>('packaging');
  
  const [selections, setSelections] = useState<{
    packaging: string | null;
    fruit: string | null;
    drink: string | null;
    snack: string | null;
    addons: string[];
  }>({
    packaging: null,
    fruit: null,
    drink: null,
    snack: null,
    addons: [],
  });

  const [quantity, setQuantity] = useState(minQuantityRequired);

  useEffect(() => {
    setQuantity((prev) => (prev < minQuantityRequired ? minQuantityRequired : prev));
  }, [minQuantityRequired]);

  useEffect(() => {
    const loadItems = async () => {
      const data = await getBuilderConfig();
      setItems(data);
      setLoading(false);
    };
    loadItems();
  }, []);

  const groupedItems = useMemo(() => {
    return {
      packaging: items.filter((i) => i.group === 'packaging'),
      fruit: items.filter((i) => i.group === 'fruit'),
      drink: items.filter((i) => i.group === 'drink'),
      snack: items.filter((i) => i.group === 'snack'),
      addon: items.filter((i) => i.group === 'addon'),
    };
  }, [items]);

  const currentStepIndex = stepOrder.indexOf(currentStep);
  
  const canProceed = useMemo(() => {
    switch (currentStep) {
      case 'packaging':
        return selections.packaging !== null;
      case 'fruit':
        return selections.fruit !== null;
      case 'drink':
        return selections.drink !== null;
      case 'snack':
        return selections.snack !== null;
      case 'addons':
        return true; // Optional
      case 'quantity':
        return quantity >= 1;
      default:
        return false;
    }
  }, [currentStep, selections, quantity]);

  const totalPrice = useMemo(() => {
    let price = 0;
    
    if (selections.packaging) {
      const pkg = items.find((i) => i.id === selections.packaging);
      if (pkg) price += pkg.price;
    }
    if (selections.fruit) {
      const fruit = items.find((i) => i.id === selections.fruit);
      if (fruit) price += fruit.price;
    }
    if (selections.drink) {
      const drink = items.find((i) => i.id === selections.drink);
      if (drink) price += drink.price;
    }
    if (selections.snack) {
      const snack = items.find((i) => i.id === selections.snack);
      if (snack) price += snack.price;
    }
    selections.addons.forEach((addonId) => {
      const addon = items.find((i) => i.id === addonId);
      if (addon) price += addon.price;
    });

    return price;
  }, [selections, items]);

  const getItemName = (id: string | null) => {
    if (!id) return '-';
    const item = items.find((i) => i.id === id);
    return item?.name || '-';
  };

  const handleSelect = (group: 'packaging' | 'fruit' | 'drink' | 'snack', id: string) => {
    setSelections((prev) => ({ ...prev, [group]: id }));
  };

  const handleAddonToggle = (id: string) => {
    setSelections((prev) => ({
      ...prev,
      addons: prev.addons.includes(id)
        ? prev.addons.filter((a) => a !== id)
        : [...prev.addons, id],
    }));
  };

  const goNext = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < stepOrder.length) {
      setCurrentStep(stepOrder[nextIndex]);
    }
  };

  const goPrev = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(stepOrder[prevIndex]);
    }
  };

  const handleAddToCart = () => {
    addItem({
      productId: `custom-${Date.now()}`,
      name: 'پک سفارشی',
      quantity,
      price: totalPrice,
      isCustomPack: true,
      customConfig: {
        packaging: getItemName(selections.packaging),
        fruit: getItemName(selections.fruit),
        drink: getItemName(selections.drink),
        snack: getItemName(selections.snack),
        addons: selections.addons.map((id) => getItemName(id)),
      },
    });
    
    notifySuccess('پک سفارشی به سبد خرید اضافه شد');
    navigate('/cart');
  };

  if (loading) {
    return (
      <AppShell>
        <div className="container py-8">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-48 bg-muted rounded" />
            <div className="h-4 w-64 bg-muted rounded" />
            <div className="grid grid-cols-2 gap-4 mt-8">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-24 bg-muted rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  const renderStepContent = () => {
    const stepGroups = {
      packaging: groupedItems.packaging,
      fruit: groupedItems.fruit,
      drink: groupedItems.drink,
      snack: groupedItems.snack,
    };

    if (currentStep === 'addons') {
      return (
        <div className="space-y-3 sm:space-y-4">
          <h3 className="text-base sm:text-lg font-semibold text-foreground">
            افزودنی‌ها (اختیاری)
          </h3>
          <div className="grid grid-cols-2 gap-2 sm:gap-3">
            {groupedItems.addon.map((item) => (
              <button
                key={item.id}
                onClick={() => handleAddonToggle(item.id)}
                className={`p-3 sm:p-4 rounded-lg sm:rounded-xl border-2 text-right transition-all touch-manipulation ${
                  selections.addons.includes(item.id)
                    ? 'border-primary bg-primary/5'
                    : 'border-border bg-card hover:border-primary/30'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className={`w-4 h-4 sm:w-5 sm:h-5 rounded border-2 flex items-center justify-center ${
                    selections.addons.includes(item.id)
                      ? 'bg-primary border-primary text-primary-foreground'
                      : 'border-muted-foreground'
                  }`}>
                    {selections.addons.includes(item.id) && <Check className="w-2.5 h-2.5 sm:w-3 sm:h-3" />}
                  </div>
                  <span className="text-[10px] sm:text-xs text-primary font-medium">
                    +{item.price.toLocaleString('fa-IR')}
                  </span>
                </div>
                <p className="mt-1.5 sm:mt-2 text-sm sm:text-base font-medium text-foreground">{item.name}</p>
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (currentStep === 'quantity') {
      return (
        <div className="space-y-4 sm:space-y-6">
          <h3 className="text-base sm:text-lg font-semibold text-foreground">تعداد پک</h3>
          
          <div className="flex items-center gap-3 sm:gap-4">
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-24 sm:w-32 h-12 sm:h-14 text-center text-xl sm:text-2xl font-bold border-2 border-input rounded-lg sm:rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              min={1}
            />
            <span className="text-muted-foreground text-sm sm:text-base">عدد</span>
          </div>

          {quantity < minQuantityRequired && (
            <RuleAlert
              type="warning"
              message={`حداقل تعداد سفارش ${minQuantityRequired} عدد است. می‌توانید در سبد خرید محصولات دیگر اضافه کنید.`}
            />
          )}

          <div className="bg-muted/50 rounded-lg sm:rounded-xl border border-border p-3 sm:p-4">
            <p className="text-muted-foreground text-sm mb-1 sm:mb-2">جمع کل:</p>
            <p className="text-2xl sm:text-3xl font-bold text-primary">
              {(totalPrice * quantity).toLocaleString('fa-IR')} تومان
            </p>
          </div>
        </div>
      );
    }

    const currentItems = stepGroups[currentStep as keyof typeof stepGroups] || [];
    const selectedId = selections[currentStep as keyof typeof selections] as string | null;

    return (
      <div className="space-y-3 sm:space-y-4">
        <h3 className="text-base sm:text-lg font-semibold text-foreground">
          {stepLabels[currentStep]} را انتخاب کنید
        </h3>
        <div className="grid grid-cols-2 gap-2 sm:gap-3">
          {currentItems.map((item) => (
            <button
              key={item.id}
              onClick={() => handleSelect(currentStep as 'packaging' | 'fruit' | 'drink' | 'snack', item.id)}
              className={`p-3 sm:p-4 rounded-lg sm:rounded-xl border-2 text-right transition-all touch-manipulation ${
                selectedId === item.id
                  ? 'border-primary bg-primary/5 shadow-soft'
                  : 'border-border bg-card hover:border-primary/30'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5 sm:mb-2">
                <div className={`w-4 h-4 sm:w-5 sm:h-5 rounded-full border-2 flex items-center justify-center ${
                  selectedId === item.id
                    ? 'bg-primary border-primary text-primary-foreground'
                    : 'border-muted-foreground'
                }`}>
                  {selectedId === item.id && <Check className="w-2.5 h-2.5 sm:w-3 sm:h-3" />}
                </div>
                <span className="text-[10px] sm:text-sm text-primary font-medium">
                  {item.price.toLocaleString('fa-IR')} تومان
                </span>
              </div>
              <p className="text-sm sm:text-base font-medium text-foreground">{item.name}</p>
            </button>
          ))}
        </div>
      </div>
    );
  };

  return (
    <AppShell>
      <SEO
        pageKey="builder"
        path="/builder"
        breadcrumbs={[
          { name: 'خانه', url: '/' },
          { name: 'ساخت پک اختصاصی', url: '/builder' },
        ]}
      />
      <div className="container py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">
            ساخت پک اختصاصی
          </h1>
          <p className="text-muted-foreground">
            پک مورد نظر خود را مرحله به مرحله بسازید
          </p>
        </div>

        {/* Mobile Preview - Show at top on mobile */}
        <div className="block lg:hidden mb-6">
          <div className="bg-card rounded-xl border border-border p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-primary" />
                <span className="font-medium text-foreground text-sm">محتویات پک</span>
              </div>
              <span className="font-bold text-primary text-sm">
                {totalPrice.toLocaleString('fa-IR')} تومان
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row-reverse gap-6 lg:gap-8">
          {/* Sidebar - Preview (desktop only) */}
          <aside className="hidden lg:block lg:w-80 xl:w-96 flex-shrink-0">
            <div className="bg-card rounded-2xl border border-border p-6 sticky top-20">
              <div className="flex items-center gap-2 mb-4">
                <Package className="w-5 h-5 text-primary" />
                <h3 className="font-semibold text-foreground">محتویات پک شما</h3>
              </div>

              <div className="space-y-3 mb-6">
                {[
                  { label: 'بسته‌بندی', value: selections.packaging },
                  { label: 'میوه', value: selections.fruit },
                  { label: 'نوشیدنی', value: selections.drink },
                  { label: 'کیک/اسنک', value: selections.snack },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                    <span className="text-muted-foreground text-sm">{label}</span>
                    <span className={`text-sm font-medium ${value ? 'text-foreground' : 'text-muted-foreground'}`}>
                      {getItemName(value)}
                    </span>
                  </div>
                ))}

                {selections.addons.length > 0 && (
                  <div className="py-2">
                    <span className="text-muted-foreground text-sm block mb-2">افزودنی‌ها:</span>
                    <div className="flex flex-wrap gap-1">
                      {selections.addons.map((id) => (
                        <span key={id} className="text-xs bg-accent text-accent-foreground px-2 py-1 rounded-full">
                          {getItemName(id)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-muted-foreground">قیمت هر پک:</span>
                  <span className="font-bold text-primary">
                    {totalPrice.toLocaleString('fa-IR')} تومان
                  </span>
                </div>
                {currentStep === 'quantity' && (
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">جمع کل:</span>
                    <span className="font-bold text-lg text-primary">
                      {(totalPrice * quantity).toLocaleString('fa-IR')} تومان
                    </span>
                  </div>
                )}
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <div className="flex-1 min-w-0 space-y-4 lg:space-y-6">
            {/* Progress */}
            <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-2 -mx-4 px-4 sm:mx-0 sm:px-0">
              {stepOrder.map((step, index) => (
                <button
                  key={step}
                  onClick={() => {
                    if (index <= currentStepIndex || canProceed) {
                      setCurrentStep(step);
                    }
                  }}
                  className={`flex items-center gap-1 sm:gap-2 px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-full text-xs sm:text-sm font-medium whitespace-nowrap transition-all touch-manipulation ${
                    step === currentStep
                      ? 'bg-primary text-primary-foreground'
                      : index < currentStepIndex
                      ? 'bg-success/10 text-success'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {index < currentStepIndex && <Check className="w-3 h-3 sm:w-4 sm:h-4" />}
                  <span className="hidden sm:inline">{index + 1}. </span>
                  <span>{stepLabels[step]}</span>
                </button>
              ))}
            </div>

            {/* Step Content */}
            <div className="bg-card rounded-xl sm:rounded-2xl border border-border p-4 sm:p-6 min-h-[280px] sm:min-h-[300px]">
              {renderStepContent()}
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between gap-3">
              <Button
                variant="outline"
                onClick={goPrev}
                disabled={currentStepIndex === 0}
                className="gap-1.5 sm:gap-2 min-h-[44px] text-sm"
              >
                <ArrowRight className="w-4 h-4" />
                <span className="hidden sm:inline">قبلی</span>
              </Button>

              {currentStep === 'quantity' ? (
                <Button
                  variant="gold"
                  size="lg"
                  onClick={handleAddToCart}
                  className="gap-2 flex-1 sm:flex-none min-h-[48px]"
                >
                  <ShoppingCart className="w-5 h-5" />
                  <span>افزودن به سبد</span>
                </Button>
              ) : (
                <Button
                  variant="default"
                  onClick={goNext}
                  disabled={!canProceed}
                  className="gap-1.5 sm:gap-2 min-h-[44px] text-sm"
                >
                  <span className="hidden sm:inline">بعدی</span>
                  <span className="sm:hidden">بعدی</span>
                  <ArrowLeft className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
