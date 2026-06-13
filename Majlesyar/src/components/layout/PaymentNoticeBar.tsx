import { Coins } from 'lucide-react';
import { useLocation } from 'react-router-dom';

import { useSettings } from '@/contexts/SettingsContext';
import type { EventContentBlock, EventPage, SiteTopNotice } from '@/types/domain';

const PERCENT_80 = "\u06f8\u06f0";
const PAYMENT_LABEL = "\u067e\u0631\u062f\u0627\u062e\u062a";
const NOTICE_HEADINGS = [
  "\u0645\u0632\u0627\u06cc\u0627\u06cc",
  "\u0646\u06a9\u0627\u062a",
  "\u0646\u06a9\u062a\u0647",
];
const DETAIL_STOP_HEADINGS = [
  "\u0645\u0639\u0631\u0641\u06cc",
  "\u062a\u0648\u0636\u06cc\u062d\u0627\u062a",
  "\u0633\u0648\u0627\u0644\u0627\u062a",
];
const EMOJI_PATTERN = /[\u{1f300}-\u{1faff}\u2600-\u27bf]/u;

function normalizePath(path?: string) {
  if (!path) return '';
  return path === '/' ? path : path.replace(/\/+$/, '');
}

function getCurrentEvent(pathname: string, eventPages: EventPage[]) {
  const currentPath = normalizePath(pathname);
  return eventPages.find((event) => normalizePath(event.routePath) === currentPath);
}

function textBeforeColon(text: string) {
  return text.split(":")[0]?.replace(EMOJI_PATTERN, "").trim() || text;
}

function buildPageNotice(event?: EventPage): SiteTopNotice | null {
  const blocks = event?.contentBlocks;
  if (!blocks?.length) return null;

  const headingIndex = blocks.findIndex((block) => NOTICE_HEADINGS.some((prefix) => block.text.startsWith(prefix)));
  const heading = headingIndex >= 0 ? blocks[headingIndex] : undefined;
  const noticeBlocks = headingIndex >= 0 ? blocks.slice(headingIndex + 1) : blocks;
  const detail = noticeBlocks.find((block: EventContentBlock) => {
    const text = block.text.trim();
    return (
      EMOJI_PATTERN.test(text) &&
      !DETAIL_STOP_HEADINGS.some((prefix) => text.startsWith(prefix))
    );
  });
  const payment = noticeBlocks.find((block) => block.text.includes(PAYMENT_LABEL) || block.text.includes(PERCENT_80));

  if (!heading && !detail && !payment) return null;

  return {
    title: heading?.text || (detail ? textBeforeColon(detail.text) : event.name),
    message: detail?.text || payment?.text || event.description,
    badge: payment ? textBeforeColon(payment.text) : "",
  };
}

export function PaymentNoticeBar() {
  const { settings } = useSettings();
  const { pathname } = useLocation();
  const currentEvent = getCurrentEvent(pathname, settings.eventPages);
  const notice = buildPageNotice(currentEvent) || settings.siteTopNotice;

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
