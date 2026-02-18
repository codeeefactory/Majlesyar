import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { defaultFaqs, type FAQ } from '@/data/faqData';

interface FAQSectionProps {
  faqs?: FAQ[];
  title?: string;
  description?: string;
}

export { defaultFaqs };
export type { FAQ };

export function FAQSection({ 
  faqs = defaultFaqs,
  title = 'سؤالات متداول',
  description = 'پاسخ سؤالات رایج درباره سفارش پک‌های پذیرایی'
}: FAQSectionProps) {
  return (
    <section className="container py-16" aria-labelledby="faq-heading">
      <header className="text-center mb-10">
        <h2 id="faq-heading" className="text-2xl md:text-3xl font-bold text-foreground mb-3">
          {title}
        </h2>
        <p className="text-muted-foreground text-base md:text-lg">
          {description}
        </p>
      </header>

      <div className="max-w-3xl mx-auto">
        <Accordion type="single" collapsible className="space-y-4">
          {faqs.map((faq, index) => (
            <AccordionItem 
              key={index} 
              value={`item-${index}`}
              className="bg-card border border-border rounded-xl px-6 data-[state=open]:shadow-soft transition-shadow"
            >
              <AccordionTrigger className="text-right hover:no-underline py-4">
                <span className="font-semibold text-foreground text-sm md:text-base">
                  {faq.question}
                </span>
              </AccordionTrigger>
              <AccordionContent className="text-muted-foreground text-sm md:text-base leading-relaxed pb-4">
                {faq.answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
