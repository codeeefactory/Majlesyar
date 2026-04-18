import { Clock3, Coins, ShieldCheck, Sparkles, type LucideIcon } from 'lucide-react';

import { useSettings } from '@/contexts/SettingsContext';

const benefitIcons: LucideIcon[] = [Clock3, Sparkles, Coins, ShieldCheck];

export function HomepageBenefitsSection() {
  const { settings } = useSettings();
  const section = settings.homepageBenefitsSection;
  const items = section.items.filter((item) => item.title || item.description || item.note);

  if (!section.eyebrow && !section.title && items.length === 0) {
    return null;
  }

  return (
    <section className="container pb-16 md:pb-20" aria-labelledby="benefits-heading">
      <div className="overflow-hidden rounded-3xl border border-border bg-[linear-gradient(180deg,hsl(var(--secondary)/0.35),hsl(var(--background))_55%,hsl(var(--accent)/0.18))] p-6 shadow-soft md:p-8">
        <div className="mb-8 max-w-2xl">
          {section.eyebrow ? <p className="mb-2 text-sm font-semibold text-primary">{section.eyebrow}</p> : null}
          {section.title ? (
            <h2 id="benefits-heading" className="text-2xl font-bold text-foreground md:text-3xl">
              {section.title}
            </h2>
          ) : null}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {items.map((item, index) => {
            const Icon = benefitIcons[index % benefitIcons.length];

            return (
              <article
                key={`${item.title}-${index}`}
                className="rounded-2xl border border-border/70 bg-card/90 p-5 shadow-sm transition-transform duration-300 hover:-translate-y-0.5"
              >
                <div className="flex items-start gap-4">
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div className="space-y-2">
                    {item.title ? <h3 className="text-lg font-bold text-foreground">{item.title}</h3> : null}
                    {item.description ? (
                      <div className="text-sm leading-7 text-muted-foreground md:text-base">
                        <p>{item.description}</p>
                        {item.note ? (
                          <span className="mt-1 block text-xs leading-6 text-muted-foreground/80 md:text-sm">
                            ({item.note})
                          </span>
                        ) : null}
                      </div>
                    ) : item.note ? (
                      <div className="text-sm leading-7 text-muted-foreground md:text-base">
                        <span className="block text-xs leading-6 text-muted-foreground/80 md:text-sm">
                          ({item.note})
                        </span>
                      </div>
                    ) : null}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
