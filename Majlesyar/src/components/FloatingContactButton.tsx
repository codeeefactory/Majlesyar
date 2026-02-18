import { Phone } from 'lucide-react';
import { Button } from '@/components/ui/button';

const CONTACT_PHONE = '09123456789';

export function FloatingContactButton() {
  return (
    <div className="fixed bottom-4 left-4 z-50">
      <Button
        variant="gold"
        size="lg"
        className="rounded-full w-14 h-14 p-0 shadow-lg hover:shadow-xl transition-all duration-200 active:scale-95"
        onClick={() => window.location.href = `tel:${CONTACT_PHONE}`}
        aria-label="تماس برای سفارش"
      >
        <Phone className="w-6 h-6" />
      </Button>
    </div>
  );
}
