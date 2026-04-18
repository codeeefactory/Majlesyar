import { Coins } from 'lucide-react';

import { useSettings } from '@/contexts/SettingsContext';

export function PaymentNoticeBar() {
  const { settings } = useSettings();
  const notice = settings.siteTopNotice;

  if (!notice.title && !notice.message && !notice.badge) {
    return null;
  }

  return (
    <div className="border-b border-primary/15 bg-primary text-primary-foreground">
      <div className="container flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/14">
            <Coins className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="space-y-1">
            {notice.title ? <p className="text-sm font-black md:text-base">{notice.title}</p> : null}
            {notice.message ? (
              <p className="text-xs leading-6 text-primary-foreground/90 md:text-sm">{notice.message}</p>
            ) : null}
          </div>
        </div>
        {notice.badge ? (
          <span className="inline-flex self-start rounded-full bg-white/16 px-3 py-1 text-xs font-bold sm:self-center">
            {notice.badge}
          </span>
        ) : null}
      </div>
    </div>
  );
}
