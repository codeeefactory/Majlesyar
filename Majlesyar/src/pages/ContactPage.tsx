import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Phone, MapPin, Clock, Instagram, MessageCircle } from 'lucide-react';
import { useSettings } from '@/contexts/SettingsContext';
import { getInstagramHandle } from '@/lib/contact';

export default function ContactPage() {
  const { settings } = useSettings();

  const contactMethods = [
    {
      icon: Phone,
      title: 'تماس تلفنی',
      description: 'سریع‌ترین راه برای سفارش',
      value: settings.contactPhone,
      action: () => window.location.href = `tel:${settings.contactPhone}`,
      buttonText: 'تماس بگیرید',
      highlight: true,
    },
    {
      icon: MessageCircle,
      title: 'واتساپ',
      description: 'پیام‌رسان محبوب',
      value: settings.contactPhone,
      action: () => window.open(settings.whatsappUrl, '_blank'),
      buttonText: 'پیام در واتساپ',
    },
    {
      icon: Instagram,
      title: 'اینستاگرام',
      description: 'دایرکت مسیج',
      value: getInstagramHandle(settings.instagramUrl),
      action: () => window.open(settings.instagramUrl, '_blank'),
      buttonText: 'پیام در اینستاگرام',
    },
  ];

  return (
    <AppShell>
      <SEO
        pageKey="contact"
        path="/contact"
        breadcrumbs={[
          { name: 'خانه', url: '/' },
          { name: 'تماس با ما', url: '/contact' },
        ]}
      />

      <section className="relative overflow-hidden">
        <div className="absolute inset-0 cream-gradient" />
        <div className="absolute top-10 right-10 w-64 h-64 bg-primary/10 rounded-full blur-3xl" />

        <div className="container relative py-12 md:py-16">
          <div className="text-center max-w-xl mx-auto">
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-4">تماس با ما</h1>
            <p className="text-muted-foreground text-lg">آماده پاسخگویی به سوالات و ثبت سفارش شما هستیم</p>
          </div>
        </div>
      </section>

      <section className="container -mt-6 relative z-10">
        <Card className="bg-primary text-primary-foreground border-0 overflow-hidden">
          <CardContent className="p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-center md:text-right">
              <h2 className="text-xl md:text-2xl font-bold mb-1">همین الان تماس بگیرید</h2>
              <p className="opacity-90">برای مشاوره رایگان و ثبت سفارش</p>
            </div>
            <Button
              variant="secondary"
              size="xl"
              className="gap-2 min-h-[48px] touch-manipulation"
              onClick={() => window.location.href = `tel:${settings.contactPhone}`}
            >
              <Phone className="w-5 h-5" />
              {settings.contactPhone}
            </Button>
          </CardContent>
        </Card>
      </section>

      <section className="container py-12">
        <h2 className="text-2xl font-bold text-foreground mb-6 text-center">راه‌های ارتباطی</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {contactMethods.map((method) => (
            <Card
              key={method.title}
              className={`overflow-hidden transition-all duration-200 hover:shadow-lg ${method.highlight ? 'ring-2 ring-primary' : ''}`}
            >
              <CardContent className="p-6 text-center">
                <div className={`w-14 h-14 rounded-full mx-auto mb-4 flex items-center justify-center ${method.highlight ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
                  <method.icon className="w-7 h-7" />
                </div>
                <h3 className="font-bold text-foreground text-lg mb-1">{method.title}</h3>
                <p className="text-muted-foreground text-sm mb-3">{method.description}</p>
                <p className="font-semibold text-foreground mb-4 dir-ltr">{method.value}</p>
                <Button
                  variant={method.highlight ? 'gold' : 'outline'}
                  className="w-full min-h-[44px] touch-manipulation"
                  onClick={method.action}
                >
                  {method.buttonText}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="container pb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardContent className="p-6 flex items-start gap-4">
              <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
                <MapPin className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h3 className="font-bold text-foreground mb-1">آدرس</h3>
                <p className="text-muted-foreground">{settings.contactAddress}</p>
                <p className="text-sm text-muted-foreground mt-1">ارسال به تهران و البرز</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6 flex items-start gap-4">
              <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
                <Clock className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h3 className="font-bold text-foreground mb-1">ساعات کاری</h3>
                <p className="text-muted-foreground">{settings.workingHours}</p>
                <p className="text-sm text-muted-foreground mt-1">پاسخگویی آنلاین ۲۴ ساعته</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </AppShell>
  );
}
