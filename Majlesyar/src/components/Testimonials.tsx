import { Star, Quote } from 'lucide-react';

interface Testimonial {
  id: number;
  name: string;
  role: string;
  content: string;
  rating: number;
  eventType: string;
}

const testimonials: Testimonial[] = [
  {
    id: 1,
    name: 'مریم احمدی',
    role: 'مدیر برگزاری همایش',
    content: 'کیفیت پک‌های پذیرایی عالی بود و تحویل به‌موقع انجام شد. همکاری با مجلس یار تجربه‌ای فوق‌العاده بود.',
    rating: 5,
    eventType: 'همایش علمی'
  },
  {
    id: 2,
    name: 'علی محمدی',
    role: 'برگزارکننده مراسم',
    content: 'برای مراسم ترحیم پدرم از پک نذری مجلس یار استفاده کردیم. بسته‌بندی شیک و محترمانه بود.',
    rating: 5,
    eventType: 'مراسم ترحیم'
  },
  {
    id: 3,
    name: 'سارا کریمی',
    role: 'دانشجوی دکتری',
    content: 'برای جلسه دفاع پایان‌نامه‌ام سفارش دادم. همه اساتید از کیفیت پذیرایی تعریف کردند.',
    rating: 5,
    eventType: 'دفاع پایان‌نامه'
  },
  {
    id: 4,
    name: 'رضا نوری',
    role: 'والدین',
    content: 'جشن تولد دخترم با پک‌های رنگارنگ مجلس یار خاص‌تر شد. بچه‌ها خیلی خوششان آمد!',
    rating: 5,
    eventType: 'جشن تولد'
  }
];

export function Testimonials() {
  return (
    <section className="container py-16" aria-labelledby="testimonials-heading">
      <header className="text-center mb-12">
        <h2 id="testimonials-heading" className="text-2xl md:text-3xl font-bold text-foreground mb-3">
          نظرات مشتریان
        </h2>
        <p className="text-muted-foreground text-base md:text-lg max-w-2xl mx-auto">
          رضایت مشتریان، افتخار ماست. بیش از ۵۰۰ مراسم موفق در سراسر تهران و البرز
        </p>
        
        {/* Overall Rating */}
        <div className="flex items-center justify-center gap-2 mt-4">
          <div className="flex items-center gap-0.5" role="img" aria-label="امتیاز کلی ۵ از ۵">
            {[1, 2, 3, 4, 5].map((star) => (
              <Star 
                key={star} 
                className="w-5 h-5 fill-primary text-primary" 
                aria-hidden="true" 
              />
            ))}
          </div>
          <span className="text-sm font-medium text-foreground">۵.۰</span>
          <span className="text-sm text-muted-foreground">(+۵۰۰ نظر)</span>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {testimonials.map((testimonial, index) => (
          <article 
            key={testimonial.id}
            className="bg-card rounded-2xl p-6 border border-border shadow-soft hover:shadow-medium transition-shadow"
          >
            {/* Quote Icon */}
            <div className="mb-4">
              <Quote className="w-8 h-8 text-primary/30" aria-hidden="true" />
            </div>

            {/* Content */}
            <blockquote className="text-foreground text-sm md:text-base leading-relaxed mb-4">
              "{testimonial.content}"
            </blockquote>

            {/* Rating */}
            <div className="flex items-center gap-0.5 mb-4" role="img" aria-label={`امتیاز ${testimonial.rating} از ۵`}>
              {[1, 2, 3, 4, 5].map((star) => (
                <Star 
                  key={star} 
                  className={`w-4 h-4 ${star <= testimonial.rating ? 'fill-primary text-primary' : 'text-muted-foreground/30'}`}
                  aria-hidden="true"
                />
              ))}
            </div>

            {/* Author */}
            <footer className="border-t border-border pt-4">
              <cite className="not-italic">
                <p className="font-semibold text-foreground text-sm">{testimonial.name}</p>
                <p className="text-xs text-muted-foreground">{testimonial.role}</p>
                <span className="inline-block mt-2 text-xs font-medium bg-secondary text-secondary-foreground px-2 py-0.5 rounded-full">
                  {testimonial.eventType}
                </span>
              </cite>
            </footer>
          </article>
        ))}
      </div>

      {/* Trust Indicators */}
      <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-success rounded-full" aria-hidden="true" />
          <span>تضمین کیفیت</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-primary rounded-full" aria-hidden="true" />
          <span>بازگشت وجه در صورت نارضایتی</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-secondary rounded-full" aria-hidden="true" />
          <span>پشتیبانی ۲۴ ساعته</span>
        </div>
      </div>
    </section>
  );
}
