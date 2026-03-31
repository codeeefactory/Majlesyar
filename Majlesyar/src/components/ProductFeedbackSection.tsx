import { Badge } from '@/components/ui/badge';
import { Quote, ShieldCheck, Star, Truck } from 'lucide-react';

interface ProductFeedbackSectionProps {
  productName: string;
}

interface FeedbackItem {
  id: number;
  name: string;
  role: string;
  comment: string;
  rating: number;
  eventType: string;
}

const feedbackItems: FeedbackItem[] = [
  {
    id: 1,
    name: 'الهام رضایی',
    role: 'برگزارکننده مراسم',
    comment: 'بسته بندی تمیز و محترمانه بود و همه سفارش به موقع رسید. کیفیت اقلام کاملا مطابق انتظار بود.',
    rating: 5,
    eventType: 'ترحیم',
  },
  {
    id: 2,
    name: 'محمد مرادی',
    role: 'مدیر اجرایی',
    comment: 'پیگیری سفارش دقیق انجام شد و تیم پشتیبانی پاسخگو بود. برای برنامه های بعدی هم قطعا سفارش می دهم.',
    rating: 5,
    eventType: 'فینگر فود',
  },
  {
    id: 3,
    name: 'زهرا کاظمی',
    role: 'کارشناس منابع انسانی',
    comment: 'کیفیت خوراکی ها عالی بود و مهمان ها بازخورد خیلی خوبی دادند. تحویل در بازه اعلام شده انجام شد.',
    rating: 4,
    eventType: 'شرکتی',
  },
];

export function ProductFeedbackSection({ productName }: ProductFeedbackSectionProps) {
  return (
    <section
      className="mt-12"
      aria-labelledby="product-feedback-heading"
      style={{ contentVisibility: 'auto', containIntrinsicSize: '1px 560px' }}
    >
      <div className="rounded-2xl border border-border bg-gradient-to-br from-primary/5 via-accent/10 to-background p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h2 id="product-feedback-heading" className="text-xl sm:text-2xl font-bold text-foreground">
              نظر مشتریان درباره {productName}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              تجربه واقعی خریداران از کیفیت، بسته بندی و زمان تحویل
            </p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full bg-card border border-border px-3 py-1.5">
            <div className="flex items-center gap-0.5" role="img" aria-label="امتیاز کلی ۴.۹ از ۵">
              {[1, 2, 3, 4, 5].map((star) => (
                <Star key={star} className="w-4 h-4 fill-primary text-primary" aria-hidden="true" />
              ))}
            </div>
            <span className="text-sm font-semibold text-foreground">۴.۹/۵</span>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {feedbackItems.map((item, index) => (
            <article
              key={item.id}
              className="bg-card border border-border rounded-xl p-4 shadow-soft hover:shadow-medium transition-shadow animate-fade-in"
              style={{ animationDelay: `${index * 0.06}s` }}
            >
              <div className="flex items-center justify-between mb-3">
                <Badge variant="secondary" className="text-xs">
                  {item.eventType}
                </Badge>
                <Quote className="w-4 h-4 text-primary/60" aria-hidden="true" />
              </div>

              <p className="text-sm text-foreground leading-relaxed mb-4">{item.comment}</p>

              <div className="flex items-center gap-0.5 mb-3" role="img" aria-label={`امتیاز ${item.rating} از ۵`}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <Star
                    key={star}
                    className={`w-4 h-4 ${star <= item.rating ? 'fill-primary text-primary' : 'text-muted-foreground/40'}`}
                    aria-hidden="true"
                  />
                ))}
              </div>

              <div className="pt-3 border-t border-border">
                <p className="text-sm font-semibold text-foreground">{item.name}</p>
                <p className="text-xs text-muted-foreground">{item.role}</p>
              </div>
            </article>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3 text-xs sm:text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-success" aria-hidden="true" />
            تضمین کیفیت اقلام
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Truck className="w-4 h-4 text-primary" aria-hidden="true" />
            ارسال سریع تهران و البرز
          </span>
        </div>
      </div>
    </section>
  );
}
