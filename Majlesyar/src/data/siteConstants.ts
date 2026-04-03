import type { Settings } from "@/types/domain";

export const CONTACT_PHONE = "+98991505141";
export const CONTACT_PHONE_DISPLAY = CONTACT_PHONE;
export const CONTACT_PHONE_WHATSAPP = CONTACT_PHONE.replace("+", "");

export interface EventType {
  id: string;
  name: string;
  slug: string;
  description: string;
  seoTitle?: string;
  seoDescription?: string;
  seoKeywords?: string[];
  faqs?: { question: string; answer: string }[];
  icon: string;
  color: string;
  available?: boolean;
}

export const eventTypes: EventType[] = [
  {
    id: "conference",
    name: "فینگر فود",
    slug: "conference",
    description: "سفارش فینگر فود مراسم، همایش و پذیرایی شرکتی با چیدمان حرفه‌ای و آماده‌سازی سفارشی.",
    seoTitle: "فینگر فود مراسم و همایش",
    seoDescription:
      "سفارش فینگر فود برای همایش، مراسم شرکتی و پذیرایی رسمی. انواع فینگر فود با آماده‌سازی حرفه‌ای، تحویل سریع در تهران و البرز و امکان ثبت سفارش عمده.",
    seoKeywords: [
      "فینگر فود",
      "فینگرفود",
      "فینگر فود همایش",
      "فینگر فود مراسم",
      "فینگر فود شرکتی",
      "سفارش فینگر فود",
      "فینگرفود تهران",
    ],
    faqs: [
      {
        question: "فینگر فود برای چه مراسمی مناسب است؟",
        answer: "فینگر فود برای همایش، جلسات شرکتی، افتتاحیه، دورهمی رسمی و پذیرایی ایستاده گزینه مناسبی است.",
      },
      {
        question: "آیا امکان سفارش عمده فینگر فود وجود دارد؟",
        answer: "بله، سفارش عمده فینگر فود برای مراسم با تعداد بالا انجام می‌شود و جزئیات بر اساس نوع پذیرایی هماهنگ می‌گردد.",
      },
    ],
    icon: "🍢",
    color: "bg-secondary",
    available: true,
  },
  {
    id: "memorial",
    name: "ترحیم",
    slug: "memorial",
    description: "پک‌های متناسب با مراسم ترحیم",
    icon: "🕯️",
    color: "bg-muted",
    available: true,
  },
  {
    id: "defense",
    name: "???? ? ????",
    slug: "defense",
    description: "به‌زودی فعال می‌شود",
    icon: "🎓",
    color: "bg-accent",
    available: false,
  },
  {
    id: "party",
    name: "گل",
    slug: "party",
    description: "سفارش گل و گل‌آرایی برای مراسم، ترحیم، هدیه و مناسبت‌های ویژه با طراحی آماده و اختصاصی.",
    seoTitle: "گل و گل‌آرایی مراسم",
    seoDescription:
      "سفارش گل مراسم، دسته گل و گل‌آرایی برای ترحیم، هدیه و مناسبت‌های ویژه. طراحی متنوع، ثبت سفارش سریع و هماهنگی بر اساس سلیقه شما.",
    seoKeywords: [
      "گل مراسم",
      "گل آرایی",
      "گل‌آرایی",
      "دسته گل",
      "سفارش گل",
      "گل ترحیم",
      "گل مناسب مراسم",
    ],
    faqs: [
      {
        question: "آیا امکان سفارش دسته گل با طرح مشابه تصاویر وجود دارد؟",
        answer: "بله، سفارش دسته گل و گل‌آرایی بر اساس تصاویر نمونه یا با هماهنگی برای طراحی مشابه انجام می‌شود.",
      },
      {
        question: "گل‌های این بخش برای چه مناسبت‌هایی مناسب هستند؟",
        answer: "این محصولات برای ترحیم، هدیه، مجالس رسمی و سایر مناسبت‌های خاص قابل سفارش هستند.",
      },
    ],
    icon: "💐",
    color: "bg-primary/20",
    available: true,
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
