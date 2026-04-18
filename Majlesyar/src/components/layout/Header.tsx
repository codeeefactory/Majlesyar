import { Link, useLocation } from 'react-router-dom';
import { ShoppingCart, Menu, X, Package, Home, Store, Wrench, Search, Info } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useCart } from '@/contexts/CartContext';
import { useSettings } from '@/contexts/SettingsContext';
import { Badge } from '@/components/ui/badge';
import { PaymentNoticeBar } from './PaymentNoticeBar';

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { totalItems, totalQuantity, isMinQuantityMet } = useCart();
  const { settings } = useSettings();
  const location = useLocation();

  const navLinks = [
    { href: '/', label: 'خانه', icon: Home, hidden: false },
    { href: '/shop', label: 'فروشگاه', icon: Store, hidden: false },
    { href: '/about', label: 'درباره ما', icon: Info, hidden: false },
    { href: '/builder', label: 'ساخت پک', icon: Wrench, hidden: false },
    { href: '/track', label: 'پیگیری سفارش', icon: Search, hidden: true },
  ];

  const visibleNavLinks = navLinks.filter(link => !link.hidden);

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="relative sticky top-0 z-50 w-full bg-card shadow-soft" role="banner">
      <PaymentNoticeBar />

      <div className="border-b border-border">
        <nav className="container flex h-16 items-center justify-between" aria-label="منوی اصلی">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group min-w-0" aria-label={`صفحه اصلی ${settings.siteBranding.siteName}`}>
            <div className="w-10 h-10 rounded-xl gold-gradient flex items-center justify-center shadow-soft overflow-hidden group-hover:shadow-glow transition-shadow shrink-0">
              {settings.siteLogoUrl ? (
                <img
                  src={settings.siteLogoUrl}
                  alt={settings.siteBranding.logoAlt}
                  className="w-full h-full object-cover"
                  loading="eager"
                  decoding="async"
                />
              ) : (
                <Package className="w-5 h-5 text-primary-foreground" aria-hidden="true" />
              )}
            </div>
            <span className="text-xl font-bold text-foreground truncate">
              {settings.siteBranding.siteName}
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-1" role="menubar">
            {visibleNavLinks.map((link) => (
              <Link key={link.href} to={link.href} role="menuitem">
                <Button
                  variant={isActive(link.href) ? 'default' : 'ghost'}
                  size="sm"
                  className="gap-2 min-h-[44px] touch-manipulation"
                >
                  <link.icon className="w-4 h-4" aria-hidden="true" />
                  {link.label}
                </Button>
              </Link>
            ))}
          </div>

          {/* Cart & Mobile Menu */}
          <div className="flex items-center gap-2">
            <Link to="/cart" aria-label={`سبد خرید - ${totalQuantity} محصول`}>
              <Button
                variant="outline"
                size="icon"
                className="relative min-h-[44px] min-w-[44px] touch-manipulation"
                aria-label={`سبد خرید${totalItems > 0 ? ` - ${totalQuantity} محصول` : ''}`}
              >
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
              </Button>
            </Link>

            {/* Mobile Menu Toggle */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden min-h-[44px] min-w-[44px] touch-manipulation"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label={mobileMenuOpen ? 'بستن منو' : 'باز کردن منو'}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" aria-hidden="true" /> : <Menu className="w-5 h-5" aria-hidden="true" />}
            </Button>
          </div>
        </nav>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div 
          className="md:hidden absolute top-full inset-x-0 bg-card border-b border-border shadow-medium animate-slide-down"
          role="menu"
          aria-label="منوی موبایل"
        >
          <div className="container py-4 flex flex-col gap-2">
            {visibleNavLinks.map((link) => (
              <Link 
                key={link.href} 
                to={link.href}
                onClick={() => setMobileMenuOpen(false)}
                role="menuitem"
              >
                <Button
                  variant={isActive(link.href) ? 'default' : 'ghost'}
                  className="w-full justify-start gap-3 min-h-[48px] touch-manipulation"
                >
                  <link.icon className="w-5 h-5" aria-hidden="true" />
                  {link.label}
                </Button>
              </Link>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
