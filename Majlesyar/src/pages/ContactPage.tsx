import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Phone, MapPin, Clock, Instagram, MessageCircle, Mail } from 'lucide-react';

const CONTACT_PHONE = '09123456789';
const CONTACT_ADDRESS = 'تهران، خیابان ولیعصر، پلاک ۱۲۳';
const INSTAGRAM_URL = 'https://instagram.com/majlesyar';
const WORKING_HOURS = 'شنبه تا پنجشنبه ۹ صبح تا ۹ شب';

export default function ContactPage() {
  const contactMethods = [
    {
      icon: Phone,
      title: 'تماس تلفنی',
      description: 'سریع‌ترین راه برای سفارش',
      value: CONTACT_PHONE,
      action: () => window.location.href = `tel:${CONTACT_PHONE}`,
      buttonText: 'تماس بگیرید',
      highlight: true,
    },
    {
      icon: MessageCircle,
      title: 'واتساپ',
      description: 'پیام‌رسان محبوب',
      value: CONTACT_PHONE,
      action: () => window.open(`https://wa.me/98${CONTACT_PHONE.slice(1)}`, '_blank'),
      buttonText: 'پیام در واتساپ',
    },
    {
      icon: Instagram,
      title: 'اینستاگرام',
      description: 'دایرکت مسیج',
      value: '@majlesyar',
      action: () => window.open(INSTAGRAM_URL, '_blank'),
      buttonText: 'پیام در اینستاگرام',
    },
  ];

  return (
    <AppShell>
      <SEO
        title="تماس با ما - مجلس یار"
        description="تماس با مجلس یار برای سفارش پک‌های پذیرایی. تماس تلفنی، واتساپ و اینستاگرام. تهران و البرز"
        path="/contact"
        keywords={['تماس', 'سفارش', 'مجلس یار', 'شماره تماس', 'واتساپ']}
        breadcrumbs={[
          { name: 'خانه', url: '/' },
          { name: 'تماس با ما', url: '/contact' },
        ]}
      />

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 cream-gradient" />
        <div className="absolute top-10 right-10 w-64 h-64 bg-primary/10 rounded-full blur-3xl" />
        
        <div className="container relative py-12 md:py-16">
          <div className="text-center max-w-xl mx-auto">
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              تماس با ما
            </h1>
            <p className="text-muted-foreground text-lg">
              آماده پاسخگویی به سوالات و ثبت سفارش شما هستیم
            </p>
          </div>
        </div>
      </section>

      {/* Quick Call CTA */}
      <section className="container -mt-6 relative z-10">
        <Card className="bg-primary text-primary-foreground border-0 overflow-hidden">
          <CardContent className="p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-center md:text-right">
              <h2 className="text-xl md:text-2xl font-bold mb-1">
                همین الان تماس بگیرید
              </h2>
              <p className="opacity-90">
                برای مشاوره رایگان و ثبت سفارش
              </p>
            </div>
            <Button
              variant="secondary"
              size="xl"
              className="gap-2 min-h-[48px] touch-manipulation"
              onClick={() => window.location.href = `tel:${CONTACT_PHONE}`}
            >
              <Phone className="w-5 h-5" />
              {CONTACT_PHONE}
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Contact Methods */}
      <section className="container py-12">
        <h2 className="text-2xl font-bold text-foreground mb-6 text-center">
          راه‌های ارتباطی
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {contactMethods.map((method, index) => (
            <Card
              key={index}
              className={`overflow-hidden transition-all duration-200 hover:shadow-lg ${
                method.highlight ? 'ring-2 ring-primary' : ''
              }`}
            >
              <CardContent className="p-6 text-center">
                <div className={`w-14 h-14 rounded-full mx-auto mb-4 flex items-center justify-center ${
                  method.highlight ? 'bg-primary text-primary-foreground' : 'bg-muted'
                }`}>
                  <method.icon className="w-7 h-7" />
                </div>
                <h3 className="font-bold text-foreground text-lg mb-1">
                  {method.title}
                </h3>
                <p className="text-muted-foreground text-sm mb-3">
                  {method.description}
                </p>
                <p className="font-semibold text-foreground mb-4 dir-ltr">
                  {method.value}
                </p>
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

      {/* Info Section */}
      <section className="container pb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardContent className="p-6 flex items-start gap-4">
              <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
                <MapPin className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h3 className="font-bold text-foreground mb-1">آدرس</h3>
                <p className="text-muted-foreground">{CONTACT_ADDRESS}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  ارسال به تهران و البرز
                </p>
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
                <p className="text-muted-foreground">{WORKING_HOURS}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  پاسخگویی آنلاین ۲۴ ساعته
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </AppShell>
  );
}
