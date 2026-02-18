import type { Settings } from "@/types/domain";

export interface EventType {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  color: string;
}

export const eventTypes: EventType[] = [
  {
    id: "conference",
    name: "همایش",
    slug: "conference",
    description: "پک‌های مناسب برای کنفرانس‌ها و سمینارها",
    icon: "🎤",
    color: "bg-secondary",
  },
  {
    id: "memorial",
    name: "ترحیم",
    slug: "memorial",
    description: "پک‌های متناسب با مراسم ترحیم",
    icon: "🕯️",
    color: "bg-muted",
  },
  {
    id: "defense",
    name: "دفاع",
    slug: "defense",
    description: "پک‌های ویژه جلسات دفاع پایان‌نامه",
    icon: "🎓",
    color: "bg-accent",
  },
  {
    id: "party",
    name: "تولد/مهمانی",
    slug: "party",
    description: "پک‌های شاد برای جشن‌ها و مهمانی‌ها",
    icon: "🎂",
    color: "bg-primary/20",
  },
];

export const defaultSettings: Settings = {
  minOrderQty: 40,
  leadTimeHours: 48,
  allowedProvinces: ["تهران", "البرز"],
  deliveryWindows: ["۱۰-۱۲", "۱۲-۱۴", "۱۴-۱۶", "۱۶-۱۸"],
  paymentMethods: [
    { id: "pay-later", label: "پرداخت بعد از تایید", enabled: true },
    { id: "online", label: "درگاه آنلاین (به‌زودی)", enabled: false },
  ],
};

export const allProvinces = [
  "تهران",
  "البرز",
  "اصفهان",
  "فارس",
  "خراسان رضوی",
  "آذربایجان شرقی",
  "مازندران",
  "گیلان",
  "کرمان",
  "خوزستان",
];
