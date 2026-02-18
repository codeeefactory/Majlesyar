import { Check } from 'lucide-react';

interface TimelineStep {
  id: string;
  label: string;
  completed: boolean;
  current: boolean;
}

interface OrderTimelineProps {
  currentStatus: 'pending' | 'confirmed' | 'preparing' | 'shipped' | 'delivered';
}

export function OrderTimeline({ currentStatus }: OrderTimelineProps) {
  const statuses = ['pending', 'confirmed', 'preparing', 'shipped', 'delivered'];
  const labels: Record<string, string> = {
    pending: 'ثبت شد',
    confirmed: 'تایید شد',
    preparing: 'آماده‌سازی',
    shipped: 'ارسال شد',
    delivered: 'تحویل شد',
  };

  const currentIndex = statuses.indexOf(currentStatus);

  const steps: TimelineStep[] = statuses.map((status, index) => ({
    id: status,
    label: labels[status],
    completed: index < currentIndex,
    current: index === currentIndex,
  }));

  return (
    <div className="w-full">
      <div className="flex items-center justify-between relative">
        {/* Progress Line */}
        <div className="absolute top-5 right-5 left-5 h-1 bg-muted rounded-full">
          <div 
            className="h-full gold-gradient rounded-full transition-all duration-500"
            style={{ width: `${(currentIndex / (statuses.length - 1)) * 100}%` }}
          />
        </div>

        {/* Steps */}
        {steps.map((step, index) => (
          <div key={step.id} className="flex flex-col items-center relative z-10">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 ${
                step.completed
                  ? 'gold-gradient text-primary-foreground shadow-glow'
                  : step.current
                  ? 'bg-primary text-primary-foreground shadow-medium animate-pulse-soft'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {step.completed ? (
                <Check className="w-5 h-5" />
              ) : (
                <span className="text-sm font-semibold">{index + 1}</span>
              )}
            </div>
            <span 
              className={`mt-2 text-xs font-medium whitespace-nowrap ${
                step.completed || step.current ? 'text-foreground' : 'text-muted-foreground'
              }`}
            >
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
