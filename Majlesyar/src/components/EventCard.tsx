import { Link } from 'react-router-dom';

interface EventCardProps {
  id: string;
  name: string;
  slug: string;
  routePath?: string;
  description: string;
  icon: string;
  color: string;
  available?: boolean;
}

const descriptionClass = 'text-xs md:text-sm text-muted-foreground leading-6 line-clamp-2';

export function EventCard({ name, slug, routePath, description, icon, color, available = true }: EventCardProps) {
  if (!available) {
    return (
      <article>
        <div
          className={`group block p-5 md:p-6 rounded-2xl border border-border ${color} relative overflow-hidden opacity-70 cursor-not-allowed`}
          aria-label={`${name} - به زودی`}
        >
          <div className="absolute top-3 left-3 bg-warning/20 text-warning-foreground text-xs font-semibold px-2 py-1 rounded-full">
            به زودی
          </div>

          <div className="relative z-10">
            <div className="text-3xl md:text-4xl mb-3 md:mb-4" role="img" aria-label={`آیکون ${name}`}>
              {icon}
            </div>
            <div className="text-lg md:text-xl font-bold text-foreground mb-2">{name}</div>
            <p className={descriptionClass}>{description}</p>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article>
      <Link
        to={routePath || `/events/${slug}`}
        className={`group block p-5 md:p-6 rounded-2xl border border-border ${color} card-hover relative overflow-hidden focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2`}
      >
        <div
          className="absolute -bottom-4 -left-4 text-8xl opacity-0 group-hover:opacity-10 transition-opacity pointer-events-none"
          aria-hidden="true"
        >
          {icon}
        </div>

        <div className="relative z-10">
          <div className="text-3xl md:text-4xl mb-3 md:mb-4" role="img" aria-label={`آیکون ${name}`}>
            {icon}
          </div>
          <div className="text-lg md:text-xl font-bold text-foreground mb-2 group-hover:text-primary transition-colors">
            {name}
          </div>
          <p className={descriptionClass}>{description}</p>
        </div>

        <div className="absolute bottom-4 left-4 opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-primary text-sm font-semibold">مشاهده محصولات ←</span>
        </div>
      </Link>
    </article>
  );
}
