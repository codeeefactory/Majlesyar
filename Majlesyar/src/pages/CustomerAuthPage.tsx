import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useCustomerAuth } from '@/contexts/CustomerAuthContext';
import { notifyError, notifySuccess } from '@/lib/notify';
import { LockKeyhole, LogIn, Mail, UserPlus } from 'lucide-react';

export default function CustomerAuthPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login, signup, isAuthenticated } = useCustomerAuth();
  const initialMode = location.pathname.includes('signup') ? 'signup' : 'login';
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    fullName: '',
    username: '',
    email: '',
    identifier: '',
    password: '',
  });

  const pageTitle = mode === 'login' ? 'ورود مشتریان' : 'ثبت نام مشتریان';
  const helperText = useMemo(
    () =>
      mode === 'login'
        ? 'با ایمیل یا نام کاربری وارد حساب خود شوید'
        : 'حساب مشتری بسازید و سفارش‌ها و اطلاعات تحویل را یکجا نگه دارید',
    [mode],
  );

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleModeChange = (value: string) => {
    const nextMode = value === 'signup' ? 'signup' : 'login';
    setMode(nextMode);
    navigate(nextMode === 'signup' ? '/signup' : '/login', { replace: true });
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    const result =
      mode === 'login'
        ? await login(form.identifier, form.password)
        : await signup({
            fullName: form.fullName,
            username: form.username,
            email: form.email,
            password: form.password,
          });
    setLoading(false);

    if (!result.ok) {
      notifyError(result.message || 'خطا در ورود به حساب');
      return;
    }

    notifySuccess(mode === 'login' ? 'خوش آمدید' : 'حساب شما ساخته شد');
    navigate('/dashboard');
  };

  return (
    <AppShell>
      <SEO pageKey="customer-auth" path={mode === 'signup' ? '/signup' : '/login'} noindex={true} />
      <div className="container py-8 md:py-12">
        <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1fr_0.9fr] lg:items-center">
          <section className="rounded-2xl border border-primary/20 bg-card p-6 shadow-soft md:p-8">
            <div className="mb-8 flex h-14 w-14 items-center justify-center rounded-2xl gold-gradient shadow-glow">
              {mode === 'login' ? (
                <LogIn className="h-7 w-7 text-primary-foreground" />
              ) : (
                <UserPlus className="h-7 w-7 text-primary-foreground" />
              )}
            </div>
            <h1 className="mb-3 text-2xl font-bold text-foreground md:text-4xl">{pageTitle}</h1>
            <p className="max-w-xl text-muted-foreground">{helperText}</p>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {[
                ['پروفایل سریع', 'اطلاعات تماس و آدرس آماده ثبت سفارش می‌شود'],
                ['پیگیری راحت', 'کدهای سفارش نزدیک دست شما می‌ماند'],
                ['تجربه شخصی', 'پیشنهادها و مسیر خرید شفاف‌تر می‌شود'],
              ].map(([title, description]) => (
                <div key={title} className="rounded-xl border border-border bg-background p-4">
                  <p className="font-semibold text-foreground">{title}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{description}</p>
                </div>
              ))}
            </div>
          </section>

          <Card className="rounded-2xl shadow-medium">
            <CardContent className="p-6">
              <Tabs value={mode} onValueChange={handleModeChange} dir="rtl">
                <TabsList className="mb-6 grid h-11 w-full grid-cols-2">
                  <TabsTrigger value="login">ورود</TabsTrigger>
                  <TabsTrigger value="signup">ثبت نام</TabsTrigger>
                </TabsList>
              </Tabs>

              <form onSubmit={handleSubmit} className="space-y-4">
                {mode === 'signup' && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="fullName">نام و نام خانوادگی</Label>
                      <Input
                        id="fullName"
                        value={form.fullName}
                        onChange={(event) => setForm({ ...form, fullName: event.target.value })}
                        placeholder="مثال: سارا احمدی"
                        autoComplete="name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="username">نام کاربری</Label>
                      <Input
                        id="username"
                        value={form.username}
                        onChange={(event) => setForm({ ...form, username: event.target.value })}
                        placeholder="sara_ahmadi"
                        autoComplete="username"
                        dir="ltr"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email">ایمیل</Label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                          id="email"
                          type="email"
                          value={form.email}
                          onChange={(event) => setForm({ ...form, email: event.target.value })}
                          placeholder="name@example.com"
                          autoComplete="email"
                          className="pl-10"
                          dir="ltr"
                        />
                      </div>
                    </div>
                  </>
                )}

                {mode === 'login' && (
                  <div className="space-y-2">
                    <Label htmlFor="identifier">ایمیل یا نام کاربری</Label>
                    <Input
                      id="identifier"
                      value={form.identifier}
                      onChange={(event) => setForm({ ...form, identifier: event.target.value })}
                      placeholder="name@example.com"
                      autoComplete="username"
                      dir="ltr"
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="password">رمز عبور</Label>
                  <div className="relative">
                    <LockKeyhole className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="password"
                      type="password"
                      value={form.password}
                      onChange={(event) => setForm({ ...form, password: event.target.value })}
                      placeholder="حداقل ۶ کاراکتر"
                      autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                      className="pl-10"
                      dir="ltr"
                    />
                  </div>
                </div>

                <Button type="submit" variant="gold" size="lg" className="w-full gap-2" disabled={loading}>
                  {loading ? 'در حال انجام...' : pageTitle}
                </Button>
              </form>

              <p className="mt-6 text-center text-sm text-muted-foreground">
                {mode === 'login' ? 'حساب ندارید؟ ' : 'قبلا ثبت نام کرده‌اید؟ '}
                <Link to={mode === 'login' ? '/signup' : '/login'} className="font-semibold text-primary">
                  {mode === 'login' ? 'ثبت نام کنید' : 'وارد شوید'}
                </Link>
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
