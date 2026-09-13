import { Link, useLocation } from "react-router-dom";
import { Home, PackageSearch, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SEO } from "@/components/SEO";

const NotFound = () => {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background">
      <SEO
        title="صفحه پیدا نشد"
        description="صفحه مورد نظر در مجلس یار پیدا نشد."
        path={location.pathname}
        noindex
      />
      <div className="container flex min-h-screen items-center justify-center py-12">
        <section className="w-full max-w-3xl rounded-2xl border border-border bg-card p-6 text-center shadow-medium md:p-10">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10 text-4xl font-black text-primary">
            404
          </div>
          <h1 className="mt-8 text-3xl font-bold leading-relaxed text-foreground md:text-5xl">
            این دسته گل در مسیر نیست
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-8 text-muted-foreground md:text-lg">
            صفحه‌ای که دنبال آن بودید پیدا نشد. شاید لینک قدیمی شده، شاید هم محصول به قفسه دیگری منتقل شده است.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button asChild variant="gold" size="lg" className="gap-2">
              <Link to="/">
                <Home className="h-5 w-5" aria-hidden="true" />
                صفحه اصلی
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="gap-2">
              <Link to="/pack">
                <PackageSearch className="h-5 w-5" aria-hidden="true" />
                محصولات
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="gap-2">
              <Link to="/builder">
                <Wrench className="h-5 w-5" aria-hidden="true" />
                ساخت پک اختصاصی
              </Link>
            </Button>
          </div>
          <nav className="mt-6 flex flex-wrap justify-center gap-2 text-sm" aria-label="بخش‌های پیشنهادی">
            <Link className="rounded-full bg-muted px-4 py-2 hover:text-primary" to="/pack/memorial">پک‌های ترحیم و ختم</Link>
            <Link className="rounded-full bg-muted px-4 py-2 hover:text-primary" to="/halva-khorma">حلوا خرما و خرما گردو</Link>
            <Link className="rounded-full bg-muted px-4 py-2 hover:text-primary" to="/flower">گل و گل‌آرایی</Link>
            <Link className="rounded-full bg-muted px-4 py-2 hover:text-primary" to="/food/finger_food">فینگر فود</Link>
            <Link className="rounded-full bg-muted px-4 py-2 hover:text-primary" to="/contact">تماس با ما</Link>
          </nav>
          <p className="mt-8 rounded-xl bg-muted p-4 text-sm leading-7 text-muted-foreground">
            اگر از لینک پیامک یا سفارش وارد شده‌اید، شماره سفارش را دوباره بررسی کنید.
          </p>
        </section>
      </div>
    </div>
  );
};

export default NotFound;
