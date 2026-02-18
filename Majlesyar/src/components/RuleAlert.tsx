import { AlertCircle, CheckCircle, Info } from 'lucide-react';

interface RuleAlertProps {
  type: 'error' | 'warning' | 'success' | 'info';
  message: string;
  className?: string;
}

export function RuleAlert({ type, message, className = '' }: RuleAlertProps) {
  const styles = {
    error: 'bg-destructive/10 border-destructive/30 text-destructive',
    warning: 'bg-warning/20 border-warning/40 text-foreground',
    success: 'bg-success/10 border-success/30 text-success',
    info: 'bg-secondary/30 border-secondary text-foreground',
  };

  const icons = {
    error: AlertCircle,
    warning: AlertCircle,
    success: CheckCircle,
    info: Info,
  };

  const Icon = icons[type];

  return (
    <div className={`flex items-center gap-3 p-4 rounded-xl border ${styles[type]} ${className}`}>
      <Icon className="w-5 h-5 shrink-0" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}
