import { AppShell } from '@/components/layout/AppShell';
import { SEO } from '@/components/SEO';
import { Package, Users, Award, Truck, Heart, Star } from 'lucide-react';

export default function AboutPage() {
  return (
    <AppShell>
      <SEO 
        title="درباره ما"
        description="آشنایی با مجلس یار، ارائه‌دهنده پک‌های پذیرایی و نذری برای انواع مراسمات با بیش از ۵۰۰ سفارش موفق."
        path="/about"
      />
      
      <div className="container py-8 md:py-12">
        {/* Hero Section */}
        <section className="text-center mb-12">
          <div className="w-20 h-20 rounded-2xl gold-gradient flex items-center justify-center mx-auto mb-6 shadow-medium">
            <Package className="w-10 h-10 text-primary-foreground" aria-hidden="true" />
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            درباره مجلس یار
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            ما در مجلس یار با هدف ارائه بهترین پک‌های پذیرایی و نذری برای مراسمات مختلف فعالیت می‌کنیم.
            تجربه و تخصص ما در این زمینه، تضمینی برای رضایت شماست.
          </p>
        </section>

        {/* Stats */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          {[
            { number: '+۵۰۰', label: 'سفارش موفق', icon: Award },
            { number: '+۱۰۰۰', label: 'مشتری راضی', icon: Users },
            { number: '۴۸', label: 'ساعت تحویل', icon: Truck },
            { number: '۱۰۰٪', label: 'رضایت مشتری', icon: Heart },
          ].map((stat, index) => (
            <div 
              key={index}
              className="bg-card rounded-xl border border-border p-6 text-center"
            >
              <stat.icon className="w-8 h-8 text-primary mx-auto mb-3" aria-hidden="true" />
              <p className="text-2xl md:text-3xl font-bold text-foreground">{stat.number}</p>
              <p className="text-sm text-muted-foreground mt-1">{stat.label}</p>
            </div>
          ))}
        </section>

        {/* Our Story */}
        <section className="bg-card rounded-2xl border border-border p-8 mb-12">
          <h2 className="text-2xl font-bold text-foreground mb-6 flex items-center gap-3">
            <Star className="w-6 h-6 text-primary" aria-hidden="true" />
            داستان ما
          </h2>
          <div className="space-y-4 text-muted-foreground leading-relaxed">
            <p>
              مجلس یار در سال ۱۴۰۰ با هدف ارائه پک‌های پذیرایی باکیفیت و استاندارد برای انواع مراسمات تأسیس شد.
              ما از ابتدا بر این باور بودیم که هر مراسم، چه همایش علمی باشد چه مراسم ترحیم، شایسته بهترین پذیرایی است.
            </p>
            <p>
              با تمرکز بر کیفیت مواد اولیه، بسته‌بندی حرفه‌ای و تحویل به‌موقع، توانستیم اعتماد بیش از ۱۰۰۰ مشتری را جلب کنیم.
              امروز افتخار می‌کنیم که به یکی از معتبرترین ارائه‌دهندگان پک‌های پذیرایی در تهران و البرز تبدیل شده‌ایم.
            </p>
          </div>
        </section>

        {/* Values */}
        <section>
          <h2 className="text-2xl font-bold text-foreground mb-6 text-center">ارزش‌های ما</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'کیفیت تضمینی',
                description: 'استفاده از مواد اولیه تازه و باکیفیت در تمامی پک‌ها',
                icon: Award,
              },
              {
                title: 'تحویل به‌موقع',
                description: 'تعهد به تحویل در زمان مقرر با حداکثر ۴۸ ساعت',
                icon: Truck,
              },
              {
                title: 'رضایت مشتری',
                description: 'اولویت ما جلب رضایت کامل شما از خدمات ماست',
                icon: Heart,
              },
            ].map((value, index) => (
              <div 
                key={index}
                className="bg-card rounded-xl border border-border p-6 text-center"
              >
                <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <value.icon className="w-7 h-7 text-primary" aria-hidden="true" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">{value.title}</h3>
                <p className="text-sm text-muted-foreground">{value.description}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
