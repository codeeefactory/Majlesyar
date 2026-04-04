import type { Settings } from "@/types/domain";

export const CONTACT_PHONE = "+989915505141";
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
    description: "سفارش پک ترحیم، حلوا و اقلام پذیرایی مراسم با بسته‌بندی محترمانه و تحویل سریع در تهران و البرز.",
    seoTitle: "سفارش حلوا و پک ترحیم مراسم",
    seoDescription:
      "خرید و سفارش حلوا، سینی حلوا و پک ترحیم برای مراسم ختم و یادبود. پک‌های پذیرایی ترحیم با چیدمان محترمانه، آماده‌سازی سریع و امکان سفارش عمده در تهران و البرز.",
    seoKeywords: [
      "حلوا",
      "سینی حلوا",
      "حلوا ترحیم",
      "پک ترحیم",
      "پذیرایی ترحیم",
      "پک ختم",
      "سفارش حلوا مراسم",
      "سفارش پک ترحیم",
      "خرما و حلوا",
    ],
    faqs: [
      {
        question: "آیا امکان سفارش حلوا برای مراسم ترحیم وجود دارد؟",
        answer: "بله، سفارش حلوا و سینی حلوا برای مراسم ترحیم و یادبود انجام می‌شود و بسته به نوع مراسم امکان هماهنگی تعداد و نحوه ارائه وجود دارد.",
      },
      {
        question: "پک ترحیم شامل چه اقلامی است؟",
        answer: "بسته به محصول انتخابی، پک ترحیم می‌تواند شامل حلوا، خرما، نوشیدنی، دستمال و سایر اقلام پذیرایی مراسم باشد.",
      },
      {
        question: "سفارش عمده پک ترحیم و حلوا چطور ثبت می‌شود؟",
        answer: "برای سفارش عمده حلوا و پک ترحیم کافی است تعداد، زمان مراسم و محل تحویل را مشخص کنید تا هماهنگی نهایی انجام شود.",
      },
    ],
    icon: "🕯️",
    color: "bg-muted",
    available: true,
  },
  {
    id: "defense",
    name: "دفاع پایان نامه",
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
    seoTitle: "سفارش گل و گل‌آرایی ترحیم و مراسم",
    seoDescription:
      "سفارش گل مراسم، گل ترحیم، دسته گل و گل‌آرایی برای یادبود، هدیه و مناسبت‌های ویژه. طراحی متنوع، ثبت سفارش سریع و هماهنگی بر اساس سلیقه شما.",
    seoKeywords: [
      "گل مراسم",
      "گل ترحیم",
      "سفارش گل ترحیم",
      "گل آرایی",
      "گل‌آرایی",
      "دسته گل",
      "دسته گل ترحیم",
      "سفارش گل",
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
      {
        question: "آیا امکان سفارش گل برای مراسم ترحیم وجود دارد؟",
        answer: "بله، سفارش گل ترحیم و دسته گل مناسب مراسم یادبود با هماهنگی نوع چیدمان و سبک موردنظر انجام می‌شود.",
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
  contactPhone: CONTACT_PHONE,
  contactAddress: "تهران، امیرآباد، خیابان کارگر شمالی، خیابان فرشی مقدم(شانزدهم)، پلاک ۹۱، واحد۶.",
  workingHours: "شنبه تا پنجشنبه ۹ صبح تا ۹ شب",
  instagramUrl: "https://instagram.com/majlesyar",
  telegramUrl: "https://t.me/majlesyar",
  whatsappUrl: `https://wa.me/${CONTACT_PHONE_WHATSAPP}`,
  baleUrl: "https://ble.ir/majlesyar",
  mapsUrl: "https://maps.google.com/?q=Tehran,Valiasr",
  mapsEmbedUrl:
    "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3239.9627430068!2d51.4066!3d35.7219!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zMzXCsDQzJzE4LjgiTiA1McKwMjQnMjMuOCJF!5e0!3m2!1sen!2s!4v1699999999999!5m2!1sen!2s",
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
