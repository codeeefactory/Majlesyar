import { useState, type ComponentProps } from 'react';
import { Link } from 'react-router-dom';
import { Phone, MapPin, Instagram, Store, Home, Calendar, Send } from 'lucide-react';
import baleLogo from '@/assets/social/bale.webp';
import { useSettings } from '@/contexts/SettingsContext';
import { getInstagramHandle } from '@/lib/contact';

type SocialLogoProps = Omit<ComponentProps<'img'>, 'src' | 'alt'>;
type SocialIconProps = ComponentProps<'svg'>;

const WhatsAppIcon = ({ className, ...props }: SocialIconProps) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className} {...props}>
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z" />
  </svg>
);

const BaleIcon = ({ className, ...props }: SocialLogoProps) => (
  <img
    src={baleLogo}
    alt=""
    width={96}
    height={96}
    loading="lazy"
    decoding="async"
    draggable={false}
    className={`object-contain rounded-md ${className ?? ''}`}
    {...props}
  />
);

export function Footer() {
  const { settings } = useSettings();
  const [mapLoaded, setMapLoaded] = useState(false);
  const currentYear = new Date().getFullYear();
  const persianYear = currentYear - 621;

  const socialLinks = [
    {
      name: 'اینستاگرام',
      label: getInstagramHandle(settings.instagramUrl),
      icon: Instagram,
      url: settings.instagramUrl,
      bgColor: 'bg-gradient-to-br from-[#833AB4] via-[#E1306C] to-[#F77737]',
      hoverColor: 'hover:opacity-90',
    },
    {
      name: 'واتساپ',
      label: 'واتساپ',
      icon: WhatsAppIcon,
      url: settings.whatsappUrl,
      bgColor: 'bg-[#25D366]',
      hoverColor: 'hover:bg-[#128C7E]',
    },
    {
      name: 'تلگرام',
      label: 'تلگرام',
      icon: Send,
      url: settings.telegramUrl,
      bgColor: 'bg-[#0088cc]',
      hoverColor: 'hover:bg-[#006699]',
    },
    {
      name: 'بله',
      label: 'بله',
      icon: BaleIcon,
      url: settings.baleUrl,
      bgColor: 'bg-[#00A884]',
      hoverColor: 'hover:bg-[#008866]',
    },
  ].filter((link) => Boolean(link.url));

  return (
    <footer
      className="bg-card border-t border-border mt-auto"
      role="contentinfo"
      style={{ contentVisibility: 'auto', containIntrinsicSize: '1px 1200px' }}
    >
      <div className="container py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="space-y-4 md:col-span-1">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl gold-gradient overflow-hidden flex items-center justify-center shadow-soft shrink-0">
                {settings.siteLogoUrl ? (
                  <img
                    src={settings.siteLogoUrl}
                    alt={settings.siteBranding.logoAlt}
                    className="w-full h-full object-cover"
                    loading="lazy"
                    decoding="async"
                  />
                ) : (
                  <Store className="w-6 h-6 text-primary-foreground" aria-hidden="true" />
                )}
              </div>
              <div>
                <h3 className="font-semibold text-foreground">{settings.siteBranding.siteName}</h3>
                <p className="text-xs text-muted-foreground">{settings.siteBranding.siteTagline}</p>
              </div>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed">
              {settings.siteBranding.defaultMetaDescription}
            </p>
            <Link
              to="/about"
              className="inline-flex items-center gap-2 text-foreground hover:text-primary transition-colors text-sm font-medium"
            >
              درباره ما ←
            </Link>
          </div>

          <nav className="space-y-4" aria-label="لینک‌های سریع">
            <h3 className="font-semibold text-foreground">دسترسی سریع</h3>
            <ul className="flex flex-col gap-2">
              <li>
                <Link to="/" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Home className="w-4 h-4" aria-hidden="true" />
                  خانه
                </Link>
              </li>
              <li>
                <Link to="/shop" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Store className="w-4 h-4" aria-hidden="true" />
                  فروشگاه پک‌ها
                </Link>
              </li>
              <li>
                <Link to="/contact" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Phone className="w-4 h-4" aria-hidden="true" />
                  تماس با ما
                </Link>
              </li>
            </ul>
          </nav>

          <nav className="space-y-4" aria-label="انواع مراسمات">
            <h3 className="font-semibold text-foreground">انواع مراسمات</h3>
            <ul className="flex flex-col gap-2">
              <li>
                <Link to="/events/conference" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Calendar className="w-4 h-4" aria-hidden="true" />
                  فینگر فود
                </Link>
              </li>
              <li>
                <Link to="/events/party" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Calendar className="w-4 h-4" aria-hidden="true" />
                  گل
                </Link>
              </li>
              <li>
                <Link to="/events/memorial" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Calendar className="w-4 h-4" aria-hidden="true" />
                  پک نذری و ترحیم
                </Link>
              </li>
            </ul>
          </nav>

          <address className="space-y-4 not-italic">
            <h3 className="font-semibold text-foreground">تماس با ما</h3>
            <div className="space-y-3">
              <a
                href={`tel:${settings.contactPhone}`}
                className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm"
              >
                <Phone className="w-4 h-4" aria-hidden="true" />
                {settings.contactPhone}
              </a>
              <div className="flex items-start gap-2 text-muted-foreground text-sm">
                <MapPin className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
                <span>{settings.contactAddress}</span>
              </div>
              {settings.instagramUrl ? (
                <a
                  href={settings.instagramUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm"
                  aria-label={`پیج اینستاگرام ${settings.siteBranding.siteName}`}
                >
                  <Instagram className="w-4 h-4" aria-hidden="true" />
                  {getInstagramHandle(settings.instagramUrl)}
                </a>
              ) : null}
            </div>
          </address>
        </div>

        <div className="mt-10 pt-8 border-t border-border">
          <h3 className="font-semibold text-foreground text-center mb-6">موقعیت ما روی نقشه</h3>
          <div className="rounded-2xl overflow-hidden shadow-lg border border-border/50 max-w-2xl mx-auto">
            {mapLoaded ? (
              <iframe
                src={settings.mapsEmbedUrl}
                width="100%"
                height="250"
                style={{ border: 0 }}
                allowFullScreen
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                title={`موقعیت ${settings.siteBranding.siteName} روی نقشه`}
                className="w-full"
              />
            ) : (
              <button
                onClick={() => setMapLoaded(true)}
                className="w-full h-[250px] bg-muted flex flex-col items-center justify-center gap-3 cursor-pointer hover:bg-muted/80 transition-colors"
                aria-label="بارگذاری نقشه گوگل"
              >
                <MapPin className="w-12 h-12 text-primary" aria-hidden="true" />
                <span className="text-foreground font-medium">برای مشاهده نقشه کلیک کنید</span>
                <span className="text-sm text-muted-foreground">{settings.contactAddress}</span>
              </button>
            )}
            <a
              href={settings.mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 bg-primary text-black py-3 hover:bg-primary/90 transition-colors font-semibold"
            >
              <MapPin className="w-5 h-5" aria-hidden="true" />
              مشاهده در گوگل مپ
            </a>
          </div>
        </div>

        <div className="mt-10 pt-8 border-t border-border">
          <div className="bg-gradient-to-br from-primary/5 via-accent/10 to-secondary/5 rounded-2xl p-6 md:p-8">
            <h3 className="font-semibold text-foreground text-center mb-6">ارتباط سریع با ما</h3>
            <div className="flex justify-center items-center gap-3 md:gap-4 flex-wrap">
              {socialLinks.map((link) => (
                <a
                  key={link.name}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={link.name}
                  className={`w-28 h-24 md:w-24 md:h-20 rounded-xl ${link.bgColor} ${link.hoverColor} text-white flex flex-col items-center justify-center gap-2 md:gap-1 transition-all duration-200 active:scale-95 shadow-md hover:shadow-lg`}
                >
                  <link.icon className="w-12 h-12 md:w-10 md:h-10" aria-hidden="true" />
                  <span className="text-sm md:text-xs font-medium">{link.label}</span>
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-border text-center text-sm text-muted-foreground">
          <p>© {persianYear} {settings.siteBranding.siteName}. تمامی حقوق محفوظ است.</p>
          <p className="mt-2 text-xs">
            حداقل سفارش: {settings.minOrderQty.toLocaleString('fa-IR')} عدد | ارسال: {settings.allowedProvinces.join(' و ')} | کیفیت تضمینی
          </p>
        </div>
      </div>
    </footer>
  );
}
