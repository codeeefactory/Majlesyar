import { Link, useLocation } from 'react-router-dom';
import { ShoppingCart, Menu, X, Home, Wrench, Search, Info, UserRound, BookOpen, Moon, Sun } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { useCart } from '@/contexts/CartContext';
import { useCustomerAuth } from '@/contexts/CustomerAuthContext';
import { useSettings } from '@/contexts/SettingsContext';
import { Badge } from '@/components/ui/badge';
import { useTheme } from '@/hooks/useTheme';
import majlesyarLogo from '@/assets/branding/majlesyar-logo.png';

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);
  const { totalItems, totalQuantity, isMinQuantityMet } = useCart();
  const { customer, isAuthenticated } = useCustomerAuth();
  const { settings } = useSettings();
  const { isNight, toggleTheme } = useTheme();
  const location = useLocation();

  const navLinks = [
    { href: '/', label: 'خانه', icon: Home, hidden: false },
    { href: '/blog', label: 'مجله', icon: BookOpen, hidden: false },
    { href: '/about', label: 'درباره ما', icon: Info, hidden: false },
    { href: '/builder', label: 'ساخت پک', icon: Wrench, hidden: false },
    { href: '/track', label: 'پیگیری سفارش', icon: Search, hidden: true },
  ];

  const visibleNavLinks = navLinks.filter((link) => !link.hidden);
  const accountHref = isAuthenticated ? '/dashboard' : '/login';
  const accountLabel = isAuthenticated ? customer?.fullName || 'حساب من' : 'ورود';

  const isActive = (path: string) => location.pathname === path;

  useEffect(() => {
    if (!mobileMenuOpen) return;

    const firstLink = mobileMenuRef.current?.querySelector<HTMLElement>('a[href]');
    firstLink?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobileMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [mobileMenuOpen]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  return (
    <header className="relative sticky top-0 z-50 w-full bg-card shadow-soft" role="banner">
      <div className="border-b border-border">
        <nav className="container flex h-20 items-center justify-between" aria-label="منوی اصلی">
          <Link
            to="/"
            className="flex items-center gap-3 group min-w-0 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded-xl"
            aria-label={`صفحه اصلی ${settings.siteBranding.siteName}`}
          >
            <div className="h-16 w-16 shrink-0 overflow-hidden rounded-2xl bg-[#211b14] shadow-soft transition-shadow group-hover:shadow-glow">
              {settings.siteLogoUrl ? (
                <img
                  src={settings.siteLogoUrl}
                  alt={settings.siteBranding.logoAlt}
                  className="h-full w-full object-contain p-0.5"
                  loading="eager"
                  decoding="async"
                />
              ) : (
                <img
                  src={majlesyarLogo}
                  alt={settings.siteBranding.logoAlt}
                  className="h-full w-full object-contain p-0.5"
                  loading="eager"
                  decoding="async"
                />
              )}
            </div>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {visibleNavLinks.map((link) => (
              <Button
                key={link.href}
                asChild
                variant={isActive(link.href) ? 'default' : 'ghost'}
                size="sm"
                className="gap-2 min-h-[44px] touch-manipulation"
              >
                <Link to={link.href} aria-current={isActive(link.href) ? 'page' : undefined}>
                  <link.icon className="w-4 h-4" aria-hidden="true" />
                  {link.label}
                </Link>
              </Button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="hidden sm:inline-flex min-h-[44px] min-w-[44px] touch-manipulation"
              onClick={toggleTheme}
              aria-label={isNight ? 'فعال کردن حالت روشن' : 'فعال کردن حالت شب'}
              title={isNight ? 'حالت روشن' : 'حالت شب'}
            >
              {isNight ? <Sun className="w-5 h-5" aria-hidden="true" /> : <Moon className="w-5 h-5" aria-hidden="true" />}
            </Button>

            <Button
              asChild
              variant={isActive('/dashboard') || isActive('/profile') || isActive('/login') || isActive('/signup') ? 'default' : 'ghost'}
              size="sm"
              className="hidden md:inline-flex gap-2 min-h-[44px]"
            >
              <Link to={accountHref} aria-label={accountLabel}>
                <UserRound className="w-4 h-4" aria-hidden="true" />
                <span className="max-w-24 truncate">{accountLabel}</span>
              </Link>
            </Button>

            <Button
              asChild
              variant="outline"
              size="icon"
              className="md:hidden min-h-[44px] min-w-[44px] touch-manipulation"
            >
              <Link to={accountHref} aria-label={accountLabel}>
                <UserRound className="w-5 h-5" aria-hidden="true" />
              </Link>
            </Button>

            <Button
              asChild
              variant="outline"
              size="icon"
              className="relative min-h-[44px] min-w-[44px] touch-manipulation"
            >
              <Link to="/cart" aria-label={`سبد خرید${totalItems > 0 ? ` - ${totalQuantity} محصول` : ''}`}>
                <ShoppingCart className="w-5 h-5" aria-hidden="true" />
                {totalItems > 0 && (
                  <Badge
                    className={`absolute -top-2 -right-2 w-5 h-5 p-0 flex items-center justify-center text-xs ${
                      isMinQuantityMet ? 'bg-success' : 'bg-warning text-warning-foreground'
                    }`}
                    aria-hidden="true"
                  >
                    {totalQuantity}
                  </Badge>
                )}
              </Link>
            </Button>

            <Button
              ref={menuButtonRef}
              variant="ghost"
              size="icon"
              className="md:hidden min-h-[44px] min-w-[44px] touch-manipulation"
              onClick={() => setMobileMenuOpen((open) => !open)}
              aria-label={mobileMenuOpen ? 'بستن منو' : 'باز کردن منو'}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-navigation"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" aria-hidden="true" /> : <Menu className="w-5 h-5" aria-hidden="true" />}
            </Button>
          </div>
        </nav>
      </div>

      {mobileMenuOpen && (
        <div
          id="mobile-navigation"
          ref={mobileMenuRef}
          className="md:hidden absolute top-full inset-x-0 bg-card border-b border-border shadow-medium animate-slide-down"
          aria-label="منوی موبایل"
        >
          <div className="container py-4 flex flex-col gap-2">
            <Button
              type="button"
              variant="outline"
              className="sm:hidden w-full justify-start gap-3 min-h-[48px] touch-manipulation"
              onClick={toggleTheme}
            >
              {isNight ? <Sun className="w-5 h-5" aria-hidden="true" /> : <Moon className="w-5 h-5" aria-hidden="true" />}
              {isNight ? 'حالت روشن' : 'حالت شب'}
            </Button>
            {visibleNavLinks.map((link) => (
              <Button
                key={link.href}
                asChild
                variant={isActive(link.href) ? 'default' : 'ghost'}
                className="w-full justify-start gap-3 min-h-[48px] touch-manipulation"
              >
                <Link
                  to={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive(link.href) ? 'page' : undefined}
                >
                  <link.icon className="w-5 h-5" aria-hidden="true" />
                  {link.label}
                </Link>
              </Button>
            ))}
            <Button
              asChild
              variant={isActive(accountHref) ? 'default' : 'ghost'}
              className="w-full justify-start gap-3 min-h-[48px] touch-manipulation"
            >
              <Link
                to={accountHref}
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive(accountHref) ? 'page' : undefined}
              >
                <UserRound className="w-5 h-5" aria-hidden="true" />
                {accountLabel}
              </Link>
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}
