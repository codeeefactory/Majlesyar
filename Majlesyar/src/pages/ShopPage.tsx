import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { ProductCard } from '@/components/ProductCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { SEO } from '@/components/SEO';
import { listProducts, listCategories } from '@/lib/api';
import type { Category, Product } from '@/types/domain';
import { Search, SlidersHorizontal, X, ChevronLeft, Home, Loader2 } from 'lucide-react';

type SortOption = 'featured' | 'price-asc' | 'price-desc';

const ITEMS_PER_PAGE = 4;

const breadcrumbs = [
  { name: 'خانه', url: '/' },
  { name: 'فروشگاه', url: '/shop' },
];

export default function ShopPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(
    searchParams.get('category') || null
  );
  const [sortBy, setSortBy] = useState<SortOption>('featured');
  const [showFilters, setShowFilters] = useState(false);
  
  // Pagination state
  const [visibleCount, setVisibleCount] = useState(ITEMS_PER_PAGE);
  const [loadingMore, setLoadingMore] = useState(false);
  const loaderRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadData = async () => {
      const [productsData, categoriesData] = await Promise.all([
        listProducts(),
        listCategories(),
      ]);
      setProducts(productsData);
      setCategories(categoriesData);
      setLoading(false);
    };
    loadData();
  }, []);

  // Update URL params
  useEffect(() => {
    const params = new URLSearchParams();
    if (searchQuery) params.set('q', searchQuery);
    if (selectedCategory) params.set('category', selectedCategory);
    setSearchParams(params, { replace: true });
  }, [searchQuery, selectedCategory, setSearchParams]);

  // Filter and sort products
  const filteredProducts = useMemo(() => {
    let result = [...products];

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(query) ||
          p.description.toLowerCase().includes(query) ||
          p.contents.some((c) => c.toLowerCase().includes(query))
      );
    }

    // Filter by category
    if (selectedCategory) {
      result = result.filter((p) => p.categoryIds.includes(selectedCategory));
    }

    // Sort
    switch (sortBy) {
      case 'price-asc':
        result.sort((a, b) => (a.price || 999999) - (b.price || 999999));
        break;
      case 'price-desc':
        result.sort((a, b) => (b.price || 0) - (a.price || 0));
        break;
      case 'featured':
      default:
        result.sort((a, b) => (b.featured ? 1 : 0) - (a.featured ? 1 : 0));
    }

    return result;
  }, [products, searchQuery, selectedCategory, sortBy]);

  // Reset visible count when filters change
  useEffect(() => {
    setVisibleCount(ITEMS_PER_PAGE);
  }, [searchQuery, selectedCategory, sortBy]);

  // Paginated products
  const paginatedProducts = useMemo(() => {
    return filteredProducts.slice(0, visibleCount);
  }, [filteredProducts, visibleCount]);

  const hasMore = visibleCount < filteredProducts.length;

  // Load more function
  const loadMore = useCallback(() => {
    if (loadingMore || !hasMore) return;
    
    setLoadingMore(true);
    // Simulate loading delay for smooth UX
    setTimeout(() => {
      setVisibleCount(prev => Math.min(prev + ITEMS_PER_PAGE, filteredProducts.length));
      setLoadingMore(false);
    }, 300);
  }, [loadingMore, hasMore, filteredProducts.length]);

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore) {
          loadMore();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    if (loaderRef.current) {
      observer.observe(loaderRef.current);
    }

    return () => observer.disconnect();
  }, [hasMore, loadingMore, loadMore]);

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory(null);
    setSortBy('featured');
  };

  const hasActiveFilters = searchQuery || selectedCategory || sortBy !== 'featured';

  return (
    <AppShell>
      <SEO
        title="فروشگاه حلوا، ترحیم و گل مراسم"
        description="خرید و سفارش انواع حلوا، پک ترحیم، گل مراسم و دیگر محصولات پذیرایی با بهترین کیفیت و تحویل سریع در تهران و البرز."
        path="/shop"
        breadcrumbs={breadcrumbs}
        keywords={['حلوا', 'پک ترحیم', 'گل مراسم', 'گل ترحیم', 'سفارش حلوا', 'پذیرایی ترحیم']}
      />
      <div className="container py-8">
        {/* Breadcrumb Navigation */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6" aria-label="Breadcrumb">
          <Link 
            to="/" 
            className="flex items-center gap-1 hover:text-primary transition-colors"
          >
            <Home className="w-4 h-4" />
            <span>خانه</span>
          </Link>
          <ChevronLeft className="w-4 h-4" />
          <span className="text-foreground font-medium">فروشگاه</span>
        </nav>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">فروشگاه</h1>
          <p className="text-muted-foreground">
            انتخاب از بین {products.length} پک پذیرایی
          </p>
        </div>

        {/* Search & Filters Bar */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              placeholder="جستجوی پک..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pr-10"
            />
          </div>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="h-11 px-4 rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="featured">پربازدید</option>
            <option value="price-asc">ارزان‌ترین</option>
            <option value="price-desc">گران‌ترین</option>
          </select>

          {/* Filter Toggle (Mobile) */}
          <Button
            variant="outline"
            className="md:hidden gap-2"
            onClick={() => setShowFilters(!showFilters)}
          >
            <SlidersHorizontal className="w-4 h-4" />
            فیلترها
          </Button>
        </div>

        <div className="flex flex-col md:flex-row gap-8">
          {/* Sidebar Filters */}
          <aside className={`md:w-64 shrink-0 ${showFilters ? 'block' : 'hidden md:block'}`}>
            <div className="bg-card rounded-2xl border border-border p-4 space-y-4 sticky top-20">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-foreground">دسته‌بندی</h3>
                {hasActiveFilters && (
                  <Button variant="ghost" size="sm" onClick={clearFilters} className="gap-1 text-xs">
                    <X className="w-3 h-3" />
                    پاک کردن
                  </Button>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  variant={selectedCategory === null ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedCategory(null)}
                >
                  همه
                </Button>
                {categories.map((cat) => (
                  <Button
                    key={cat.id}
                    variant={selectedCategory === cat.id ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedCategory(cat.id)}
                    className="gap-1"
                  >
                    <span>{cat.icon}</span>
                    {cat.name}
                  </Button>
                ))}
              </div>

              {/* Close on mobile */}
              <Button
                variant="ghost"
                className="w-full md:hidden"
                onClick={() => setShowFilters(false)}
              >
                بستن فیلترها
              </Button>
            </div>
          </aside>

          {/* Products Grid */}
          <div className="flex-1">
            {loading ? (
              <div className="grid grid-cols-2 gap-px">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="bg-card rounded-xl border border-border overflow-hidden animate-pulse">
                    <div className="aspect-[4/3] bg-muted" />
                    <div className="p-3 space-y-2">
                      <div className="h-4 bg-muted rounded" />
                      <div className="h-3 bg-muted rounded w-2/3" />
                      <div className="h-6 bg-muted rounded" />
                    </div>
                  </div>
                ))}
              </div>
            ) : filteredProducts.length === 0 ? (
              <div className="text-center py-16">
                <div className="text-6xl mb-4">📦</div>
                <h3 className="text-xl font-semibold text-foreground mb-2">
                  محصولی یافت نشد
                </h3>
                <p className="text-muted-foreground mb-4">
                  فیلترها را تغییر دهید یا عبارت دیگری جستجو کنید
                </p>
                <Button variant="outline" onClick={clearFilters}>
                  پاک کردن فیلترها
                </Button>
              </div>
            ) : (
              <>
                <p className="text-sm text-muted-foreground mb-4">
                  نمایش {paginatedProducts.length} از {filteredProducts.length} محصول
                </p>
                <div className="grid grid-cols-2 gap-px">
                  {paginatedProducts.map((product, index) => (
                    <div
                      key={product.id}
                      className="animate-fade-in"
                      style={{ animationDelay: `${Math.min(index, 5) * 0.05}s` }}
                    >
                      <ProductCard product={product} />
                    </div>
                  ))}
                </div>
                
                {/* Infinite scroll loader */}
                {hasMore && (
                  <div 
                    ref={loaderRef} 
                    className="flex items-center justify-center py-8"
                  >
                    {loadingMore ? (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>در حال بارگذاری...</span>
                      </div>
                    ) : (
                      <Button variant="outline" onClick={loadMore}>
                        نمایش بیشتر
                      </Button>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
