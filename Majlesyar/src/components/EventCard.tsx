import { Link } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';

interface EventCardProps {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  color: string;
}

export function EventCard({ id, name, slug, description, icon, color }: EventCardProps) {
  return (
    <article>
      <Link
        to={`/events/${slug}`}
        className={`group block p-6 rounded-2xl border border-border ${color} card-hover relative overflow-hidden focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2`}
        aria-label={`مشاهده پک‌های ${name}`}
      >
        {/* Background decoration - hidden by default to prevent LCP issues */}
        <div 
          className="absolute -bottom-4 -left-4 text-8xl opacity-0 group-hover:opacity-10 transition-opacity pointer-events-none" 
          aria-hidden="true"
        >
          {icon}
        </div>

        <div className="relative z-10">
          <div className="text-4xl mb-4" role="img" aria-label={`آیکون ${name}`}>{icon}</div>
          <h3 className="text-xl font-bold text-foreground mb-2 group-hover:text-primary transition-colors">
            {name}
          </h3>
          <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
        </div>

        {/* Hover arrow */}
        <div className="absolute bottom-4 left-4 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-primary text-sm font-semibold">مشاهده پک‌ها ←</span>
        </div>
      </Link>
    </article>
  );
}
