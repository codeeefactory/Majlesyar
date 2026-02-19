import type { Settings } from "@/types/domain";

export interface EventType {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  color: string;
  available?: boolean;
}

export const eventTypes: EventType[] = [
  {
    id: "conference",
    name: "حلوا",
    slug: "conference",
    description: "پک‌های حلوا برای مراسم ترحیم و یادبود",
    icon: "🍮",
    color: "bg-secondary",
    available: true,
  },
  {
    id: "memorial",
    name: "پک ترحیم",
    slug: "memorial",
    description: "پک‌های متناسب با مراسم ترحیم",
    icon: "🕯️",
    color: "bg-muted",
    available: true,
  },
  {
    id: "defense",
    name: "دفاع",
    slug: "defense",
    description: "به‌زودی فعال می‌شود",
    icon: "🎓",
    color: "bg-accent",
    available: false,
  },
  {
    id: "party",
    name: "تولد/مهمانی",
    slug: "party",
    description: "به‌زودی فعال می‌شود",
    icon: "🎂",
    color: "bg-primary/20",
    available: false,
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
