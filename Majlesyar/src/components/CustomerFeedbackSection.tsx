import { Star } from "lucide-react";
import type { CustomerReview } from "@/types/domain";

interface CustomerFeedbackSectionProps {
  reviews: CustomerReview[];
  title?: string;
  description?: string;
}

function clampRating(rating: number) {
  return Math.max(1, Math.min(5, Math.round(rating || 5)));
}

export function CustomerFeedbackSection({
  reviews,
  title = "نظر مشتریان",
  description = "بازخورد مشتریانی که برای مراسم خود به مجلس‌یار اعتماد کرده‌اند",
}: CustomerFeedbackSectionProps) {
  const visibleReviews = reviews.filter((review) => review.comment).slice(0, 6);

  if (!visibleReviews.length) {
    return null;
  }

  return (
    <section className="container py-16" aria-labelledby="customer-feedback-heading">
      <header className="mb-8">
        <h2 id="customer-feedback-heading" className="text-2xl md:text-3xl font-bold text-foreground mb-2">
          {title}
        </h2>
        <p className="text-muted-foreground text-base md:text-lg">{description}</p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {visibleReviews.map((review) => {
          const rating = clampRating(review.rating);
          return (
            <article key={review.id} className="rounded-lg border border-border bg-card p-5">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-foreground">
                    {review.title || review.productName || "تجربه مشتری"}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {review.customerName}
                    {review.customerCity ? `، ${review.customerCity}` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-0.5" aria-label={`${rating} از ۵`}>
                  {Array.from({ length: 5 }, (_, index) => (
                    <Star
                      key={index}
                      className={`h-4 w-4 ${index < rating ? "fill-primary text-primary" : "text-muted-foreground/35"}`}
                      aria-hidden="true"
                    />
                  ))}
                </div>
              </div>
              <p className="leading-7 text-muted-foreground">{review.comment}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
