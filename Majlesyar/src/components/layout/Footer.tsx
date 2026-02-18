import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Phone, MapPin, Instagram, Store, Home, Calendar, MessageCircle, Send } from 'lucide-react';

const CONTACT_PHONE = '09123456789';
const WHATSAPP_URL = `https://wa.me/98${CONTACT_PHONE.slice(1)}`;
const TELEGRAM_URL = 'https://t.me/majlesyar';
const EITAA_URL = 'https://eitaa.com/majlesyar';
const BALE_URL = 'https://ble.ir/majlesyar';
const LOCATION_URL = 'https://maps.google.com/?q=Tehran,Valiasr';
const MAPS_EMBED_URL = 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3239.9627430068!2d51.4066!3d35.7219!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zMzXCsDQzJzE4LjgiTiA1McKwMjQnMjMuOCJF!5e0!3m2!1sen!2s!4v1699999999999!5m2!1sen!2s';

// Custom icons for Iranian apps
const EitaaIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-6h2v6zm0-8h-2V7h2v2zm5 8h-2v-4h2v4zm0-6h-2v-2h2v2z"/>
  </svg>
);

const BaleIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm3.5 14.5l-3.5-2-3.5 2 1-4-3-2.5h4L12 6l1.5 4h4l-3 2.5 1 4z"/>
  </svg>
);

export function Footer() {
  const [mapLoaded, setMapLoaded] = useState(false);
  const currentYear = new Date().getFullYear();
  const persianYear = currentYear - 621;

  const socialLinks = [
    {
      name: 'اینستاگرام',
      icon: Instagram,
      url: 'https://instagram.com/majlesyar',
      bgColor: 'bg-gradient-to-br from-[#833AB4] via-[#E1306C] to-[#F77737]',
      hoverColor: 'hover:opacity-90',
    },
    {
      name: 'واتساپ',
      icon: MessageCircle,
      url: WHATSAPP_URL,
      bgColor: 'bg-[#25D366]',
      hoverColor: 'hover:bg-[#128C7E]',
    },
    {
      name: 'تلگرام',
      icon: Send,
      url: TELEGRAM_URL,
      bgColor: 'bg-[#0088cc]',
      hoverColor: 'hover:bg-[#006699]',
    },
    {
      name: 'ایتا',
      icon: EitaaIcon,
      url: EITAA_URL,
      bgColor: 'bg-[#B85A08]',
      hoverColor: 'hover:bg-[#9A4A06]',
      textColor: 'text-white',
    },
    {
      name: 'بله',
      icon: BaleIcon,
      url: BALE_URL,
      bgColor: 'bg-[#00A884]',
      hoverColor: 'hover:bg-[#008866]',
    },
  ];

  return (
    <footer className="bg-card border-t border-border mt-auto" role="contentinfo">
      <div className="container py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* About Us */}
          <div className="space-y-4 md:col-span-1">
            <h3 className="font-semibold text-foreground">مجلس یار</h3>
            <p className="text-muted-foreground text-sm leading-relaxed">
              ارائه‌دهنده پک‌های پذیرایی و پک نذری برای انواع مراسمات.
              همایش، ترحیم، جشن تولد و دفاع پایان‌نامه.
            </p>
            <Link 
              to="/about" 
              className="inline-flex items-center gap-2 text-foreground hover:text-primary transition-colors text-sm font-medium"
            >
              درباره ما ←
            </Link>
          </div>

          {/* Quick Links */}
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

          {/* Event Types */}
          <nav className="space-y-4" aria-label="انواع مراسمات">
            <h3 className="font-semibold text-foreground">انواع مراسمات</h3>
            <ul className="flex flex-col gap-2">
              <li>
                <Link to="/events/conference" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Calendar className="w-4 h-4" aria-hidden="true" />
                  پک همایش و سمینار
                </Link>
              </li>
              <li>
                <Link to="/events/memorial" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Calendar className="w-4 h-4" aria-hidden="true" />
                  پک نذری و ترحیم
                </Link>
              </li>
              <li>
                <Link to="/events/birthday" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Calendar className="w-4 h-4" aria-hidden="true" />
                  پک جشن تولد
                </Link>
              </li>
              <li>
                <Link to="/events/thesis" className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm">
                  <Calendar className="w-4 h-4" aria-hidden="true" />
                  پک دفاع پایان‌نامه
                </Link>
              </li>
            </ul>
          </nav>

          {/* Contact */}
          <address className="space-y-4 not-italic">
            <h3 className="font-semibold text-foreground">تماس با ما</h3>
            <div className="space-y-3">
              <a 
                href="tel:02112345678" 
                className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm"
              >
                <Phone className="w-4 h-4" aria-hidden="true" />
                ۰۲۱-۱۲۳۴۵۶۷۸
              </a>
              <div className="flex items-start gap-2 text-muted-foreground text-sm">
                <MapPin className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
                <span>تهران، خیابان ولیعصر</span>
              </div>
              <a 
                href="https://instagram.com/majlesyar" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors text-sm"
                aria-label="پیج اینستاگرام مجلس یار"
              >
                <Instagram className="w-4 h-4" aria-hidden="true" />
                @majlesyar
              </a>
            </div>
          </address>
        </div>

        {/* Location Map Widget - Lazy loaded */}
        <div className="mt-10 pt-8 border-t border-border">
          <h3 className="font-semibold text-foreground text-center mb-6">موقعیت ما روی نقشه</h3>
          <div className="rounded-2xl overflow-hidden shadow-lg border border-border/50 max-w-2xl mx-auto">
            {mapLoaded ? (
              <iframe
                src={MAPS_EMBED_URL}
                width="100%"
                height="250"
                style={{ border: 0 }}
                allowFullScreen
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                title="موقعیت مجلس یار روی نقشه"
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
                <span className="text-sm text-muted-foreground">تهران، خیابان ولیعصر</span>
              </button>
            )}
            <a
              href={LOCATION_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 bg-primary text-black py-3 hover:bg-primary/90 transition-colors font-semibold"
            >
              <MapPin className="w-5 h-5" aria-hidden="true" />
              مشاهده در گوگل مپ
            </a>
          </div>
        </div>

        {/* Social Contact Icons */}
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
                  <span className="text-sm md:text-xs font-medium">{link.name}</span>
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-border text-center text-sm text-muted-foreground">
          <p>© {persianYear} مجلس یار. تمامی حقوق محفوظ است.</p>
          <p className="mt-2 text-xs">حداقل سفارش: ۴۰ عدد | ارسال: تهران و البرز | کیفیت تضمینی</p>
        </div>
      </div>
    </footer>
  );
}
