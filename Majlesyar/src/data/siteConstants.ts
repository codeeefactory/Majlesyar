import type { EventPage, Settings } from "@/types/domain";
import { pdfPageContentBlocks } from "@/data/pdfPageContent";

export const CONTACT_PHONE = "09122148354";
export const CONTACT_PHONE_DISPLAY = CONTACT_PHONE;
export const CONTACT_PHONE_WHATSAPP = "989122148354";

export type EventType = EventPage;

const QUESTION_LABEL = "\u0633\u0648\u0627\u0644:";
const ANSWER_LABEL = "\u067e\u0627\u0633\u062e:";
const FAQ_HEADING_LABEL = "\u0633\u0648\u0627\u0644\u0627\u062a \u0645\u062a\u062f\u0627\u0648\u0644";
const ADDRESS_LABEL = "\u0622\u062f\u0631\u0633";

const pdfFaqsFromContentBlocks = (contentBlocks?: EventPage["contentBlocks"]): EventPage["faqs"] => {
  if (!contentBlocks?.length) return [];

  const text = contentBlocks
    .map((block) => block.text)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
  const faqs: NonNullable<EventPage["faqs"]> = [];
  const pattern = /\u0633\u0648\u0627\u0644:\s*(.*?)\s*\u067e\u0627\u0633\u062e:\s*(.*?)(?=\s*\u0633\u0648\u0627\u0644:|$)/g;

  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text))) {
    const question = match[1]?.replace(FAQ_HEADING_LABEL, "").trim();
    const answer = match[2]
      ?.replaceAll(ANSWER_LABEL, "")
      .split(ADDRESS_LABEL)[0]
      .replace(/\s+\d+\s*$/, "")
      .trim();

    if (question && answer) {
      faqs.push({ question, answer });
    }
  }

  return faqs;
};

const withPdfFaqs = <T extends EventType>(event: T): T => ({
  ...event,
  faqs: pdfFaqsFromContentBlocks(event.contentBlocks) || event.faqs,
});

const hiddenEventRoutePathSet = new Set([
  "/pack/personal",
  "/pack/memorial/luxury",
  "/flower/congratulation-wreaths",
  "/flower/congratulatory-wreaths",
  "/flower/funeral-bouquet",
  "/flower/box",
  "/halva-khorma/luxury",
  "/food",
  "/food/charcuterie-board",
  "/food/ashe-rashteh",
  "/food/dessert",
  "/food/juice",
]);

export function isHiddenEventRoutePath(routePath?: string) {
  if (!routePath) return false;
  return hiddenEventRoutePathSet.has(routePath.replace(/\/+$/, "") || "/");
}

const sharedServiceBenefits = [
  {
    title: "پرداخت پس از تایید کیفیت",
    description: "۸۰ درصد هزینه سفارش پس از تحویل و تایید نهایی کیفیت پرداخت می‌شود.",
  },
  {
    title: "تعهد زمان تحویل",
    description: "زمان مراسم قابل جابه‌جایی نیست؛ برای تحویل به‌موقع برنامه‌ریزی دقیق انجام می‌شود.",
  },
  {
    title: "کیفیت تازه و بهداشتی",
    description: "اقلام پس از ثبت سفارش تهیه، شست‌وشو و با بسته‌بندی مرتب آماده می‌شوند.",
  },
  {
    title: "قیمت رقابتی",
    description: "به دلیل تامین مستقیم و ساختار یکپارچه، سفارش‌های تعداد بالا با قیمت منصفانه ارائه می‌شوند.",
  },
];

const internalPageLinks = {
  home: { label: "خانه", url: "/" },
  pack: { label: "پک میوه و پذیرایی", url: "/pack" },
  memorial: { label: "پک ترحیم", url: "/pack/memorial" },
  halvaKhorma: { label: "حلوا خرما", url: "/halva-khorma" },
  khormaGerdoo: { label: "خرما گردو", url: "/halva-khorma" },
  flower: { label: "گل ترحیم و تسلیت", url: "/flower/memorial-wreaths" },
  memorialWreaths: { label: "تاج گل ترحیم", url: "/flower/memorial-wreaths" },
  bouquets: { label: "دسته گل", url: "/flower/bouquets" },
  flowerBox: { label: "باکس گل", url: "/flower/box" },
  fingerFood: { label: "فینگر فود", url: "/food/finger_food" },
  shalehZard: { label: "شله زرد", url: "/food/shaleh-zard" },
};

const hiddenEventPage = (
  id: string,
  name: string,
  routePath: string,
  description: string,
  icon = "📦",
  color = "bg-muted",
  contentBlocks?: EventPage["contentBlocks"],
): EventType => ({
  id,
  name,
  slug: id,
  routePath,
  description,
  seoTitle: `${name} | مجلس یار`,
  seoDescription: description,
  seoKeywords: [name, "مجلس یار"],
  icon,
  color,
  contentBlocks,
  available: true,
  hidden: true,
});

export const eventTypes: EventType[] = [
  {
    id: "conference",
    name: "فینگر فود",
    slug: "conference",
    routePath: "/food/finger_food",
    description: "مشاهده لیست انواع فودها، دسرها و... برای شرکت ها و مراسمات",
    seoTitle: "خرید انواع فینگرفود برای تولد، جشن و مجالس | مجلس یار",
    seoDescription:
      "سفارش انواع فینگر فود لوکس شامل مینی ساندویچ، الویه و مرغ ویژه تولد، جشن و همایش. کیفیت عالی، قیمت مناسب، ارسال تهران و کرج و پرداخت در محل.",
    seoKeywords: [
      "فینگر فود",
      "فینگرفود",
      "فینگر فود همایش",
      "فینگر فود مراسم",
      "فینگر فود شرکتی",
      "سفارش فینگر فود",
      "فینگرفود تهران",
    ],
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.fingerFood,
    internalLinks: [internalPageLinks.pack, internalPageLinks.home],
    introTitle: "معرفی بخش فینگر فود و مینی ساندویچ",
    introDescription:
      "مجلس‌یار فینگر فود، مینی ساندویچ و سینی مزه را برای همایش، تولد، افتتاحیه و پذیرایی شرکتی با امکان انتخاب آیتم‌ها و چیدمان اختصاصی آماده می‌کند.",
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
    name: "پک ترحیم",
    slug: "memorial",
    routePath: "/pack/memorial",
    description: "سفارش پک ترحیم، حلوا و اقلام پذیرایی مراسم با بسته‌بندی محترمانه و تحویل سریع در تهران و البرز.",
    seoTitle: "خرید پک ترحیم و پک میوه برای ختم + قیمت | مجلس یار",
    seoDescription:
      "فروش انواع پک میوه ترحیم و سینی میوه مجلسی با میوه دست‌چین و شسته شده برای عزا. ارزان‌ترین قیمت بازار، ارسال فوری و پرداخت در محل جهت اطمینان از کیفیت.",
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
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.memorial,
    internalLinks: [
      internalPageLinks.memorial,
      internalPageLinks.halvaKhorma,
      internalPageLinks.khormaGerdoo,
      internalPageLinks.flower,
      internalPageLinks.home,
    ],
    introTitle: "معرفی بخش پک ترحیم در مجلس",
    introDescription:
      "برای مراسم ختم، سالگرد و یادبود، پک ترحیم مجلس‌یار با میوه ممتاز، آبمیوه، دستمال و اقلام دلخواه آماده می‌شود تا پذیرایی آبرومند و بی‌دغدغه باشد.",
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
    name: "حلوا و خرما",
    slug: "halva-khorma",
    routePath: "/halva-khorma",
    description: "سفارش حلوا خرما و خرما گردو برای مراسم ترحیم با ارسال فوری تهران و البرز",
    seoTitle: "خرما گردو و حلوا خرما مراسم ترحیم | انواع حلوا مجلسی | مجلس یار",
    seoDescription:
      "خرید آنلاین خرما گردو و حلوا خرما تازه برای مراسم ترحیم. انواع حلوا خرما شیک با تزیین حرفه‌ای و ارسال فوری تهران، البرز. تضمین کیفیت واقعی: بخشی از هزینه را پس از تحویل پرداخت کنید.",
    seoKeywords: [
      "حلوا و خرما",
      "سفارش حلوا و خرما",
      "حلوا ترحیم",
      "خرما ترحیم",
      "حلوا مجلسی",
      "حلوا ختم",
      "خرما بسته بندی",
      "پک حلوا و خرما",
    ],
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.halvaKhorma,
    internalLinks: [
      internalPageLinks.shalehZard,
      internalPageLinks.bouquets,
      internalPageLinks.memorial,
      internalPageLinks.home,
    ],
    introTitle: "معرفی بخش حلوا خرما",
    introDescription:
      "حلوا و خرمای مجلس‌یار برای مراسم ترحیم، ختم، یادبود و پذیرایی رسمی با مواد تازه، تزیین حرفه‌ای و امکان سفارش عددی یا کیلویی ارائه می‌شود.",
    faqs: [
      {
        question: "حلوا و خرما برای چه مراسمی مناسب است؟",
        answer: "این بخش برای مراسم ترحیم، ختم، یادبود و پذیرایی‌های رسمی طراحی شده است و امکان سفارش عددی و عمده دارد.",
      },
      {
        question: "آیا امکان سفارش حلوا و خرما با هم وجود دارد؟",
        answer: "بله، بسته به نوع مراسم می‌توان حلوا و خرما را به‌صورت همزمان و در قالب پک‌های پذیرایی سفارش داد.",
      },
    ],
    icon: "🍯",
    color: "bg-accent",
    available: true,
  },
  {
    id: "party",
    name: "گل",
    slug: "party",
    routePath: "/flower",
    description: "مشاهده بخش گل و گل مجلس برای مراسمات تبریک، شادی و عزا",
    seoTitle: "خرید گل آنلاین | مرجع خرید انواع گل در تهران | مجلس یار",
    seoDescription:
      "خرید گل از مرجع تخصصی انواع گل‌ها شامل تاج گل ترحیم و تبریک، انواع گل برای خواستگاری و تولد و سفارش آنلاین خدمات گل‌آرایی مراسم با ارسال در تهران و کرج.",
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
    benefits: [
      {
        title: "گل تازه از گلخانه",
        description: "گل پس از ثبت سفارش تامین می‌شود تا شادابی و طراوت چندروزه حفظ شود.",
      },
      {
        title: "تطابق با تصویر",
        description: "تصاویر سایت نمونه‌کار واقعی هستند و عکس محصول پیش از ارسال قابل هماهنگی است.",
      },
      {
        title: "پرداخت پس از رویت کالا",
        description: "۸۰ درصد مبلغ سفارش پس از تحویل و تایید کیفیت پرداخت می‌شود.",
      },
      {
        title: "خدمات تشریفات یکپارچه",
        description: "امکان ارسال گل همراه با حلوا، فینگر فود یا پک پذیرایی وجود دارد.",
      },
    ],
    contentBlocks: pdfPageContentBlocks.flower,
    internalLinks: [
      internalPageLinks.memorialWreaths,
      internalPageLinks.bouquets,
      internalPageLinks.flowerBox,
      internalPageLinks.halvaKhorma,
      internalPageLinks.fingerFood,
      internalPageLinks.home,
    ],
    introTitle: "معرفی بخش گل در مجلس",
    introDescription:
      "بخش گل مجلس‌یار مرجع سفارش گل‌آرایی، باکس گل، دسته گل و تاج گل تبریک یا تسلیت در تهران و کرج است؛ طراحی‌ها با گل تازه و تامین مستقیم انجام می‌شوند.",
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
  {
    id: "pack",
    name: "پک میوه و پذیرایی",
    slug: "pack",
    routePath: "/pack",
    description: "سفارش پک میوه و پذیرایی برای مراسمات شما با ارسال سریع تهران و البرز",
    seoTitle: "خرید آنلاین پک پذیرایی و پک میوه + قیمت | مجلس یار",
    seoDescription:
      "خرید انواع پک پذیرایی و پک میوه همایش، پایان‌نامه و مجالس شما. باکس میوه همراه با ساندویچ برای تولد، جشن و شرکت با ارسال تهران و کرج. پرداخت در محل جهت اطمینان کیفیت.",
    seoKeywords: ["پک میوه", "پک پذیرایی", "پک دفاعیه", "پک همایش", "پذیرایی شرکتی"],
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.pack,
    internalLinks: [
      internalPageLinks.memorial,
      internalPageLinks.halvaKhorma,
      internalPageLinks.khormaGerdoo,
      internalPageLinks.flower,
      internalPageLinks.home,
    ],
    introTitle: "معرفی بخش پک میوه و پذیرایی مجلس",
    introDescription:
      "منوی پک پذیرایی مجلس‌یار کاملا منعطف است؛ می‌توانید میوه دست‌چین، آجیل، شیرینی، مینی ساندویچ و اقلام دلخواه را برای روز رویداد انتخاب کنید.",
    faqs: [
      {
        question: "چه زمانی باید برای سفارش پک دفاعیه یا همایش اقدام کنیم؟",
        answer: "برای هماهنگی و تامین اقلام تازه، بهتر است حداقل یک روز پیش از برگزاری جلسه دفاع یا همایش سفارش نهایی شود.",
      },
      {
        question: "چه اقلامی برای داخل پک پذیرایی مناسب هستند؟",
        answer: "میوه، آجیل، شیرینی، فینگر فود، مینی ساندویچ و اقلام بهداشتی قابل انتخاب هستند و در بخش ساخت پک اختصاصی قابل چیدمان‌اند.",
      },
      {
        question: "آیا امکان لغو سفارش سازمانی وجود دارد؟",
        answer: "برای سفارش‌های زیر ۲۰۰ عدد، در صورت باقی‌ماندن بیش از ۲۴ ساعت تا شروع رویداد امکان لغو و عودت وجه وجود دارد.",
      },
    ],
    icon: "🍎",
    color: "bg-secondary",
    available: true,
  },
  {
    id: "memorial-wreaths",
    name: "تاج گل ترحیم",
    slug: "memorial-wreaths",
    routePath: "/flower/memorial-wreaths",
    description: "سفارش تاج گل ترحیم و تسلیت با گل تازه، طراحی رسمی و ارسال راس ساعت به مسجد، تالار یا بهشت زهرا.",
    seoTitle: "سفارش گل ترحیم، تسلیت و تاج گل ترحیم با ارسال فوری | مجلس یار",
    seoDescription:
      "خرید آنلاین گل ختم، ترحیم و تسلیت برای ابراز همدردی. انواع تاج گل ترحیم با گلایل تازه، ارسال فوری به تهران و کرج و پرداخت در محل.",
    seoKeywords: ["تاج گل ترحیم", "گل تسلیت", "تاج گل ختم", "ارسال تاج گل", "گل یادبود"],
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.memorialWreaths,
    internalLinks: [internalPageLinks.home, internalPageLinks.halvaKhorma],
    introTitle: "توضیحات بخش تاج گل ترحیم و تسلیت",
    introDescription:
      "برای ابراز همدردی، تاج گل و سبد گل تسلیت مجلس‌یار با گل روز و پایه چوبی یا فلزی آماده می‌شود و عکس محصول پیش از ارسال برای هماهنگی ارائه می‌گردد.",
    faqs: [
      { question: "تاج گل بزرگ ترحیم چطور حمل می‌شود؟", answer: "تاج و پایه با خودروی مناسب حمل گل ارسال می‌شوند تا در برابر باد، گرما و تکان مسیر محافظت شوند." },
      { question: "آیا امکان چاپ متن تسلیت وجود دارد؟", answer: "بله، متن درخواستی به‌صورت رایگان روی استند یا کارت مخصوص چاپ و روی تاج نصب می‌شود." },
      { question: "حداقل زمان ثبت سفارش تاج گل فوری چقدر است؟", answer: "برای تضمین کیفیت و زمان مراسم، حداقل ۱۲ ساعت قبل سفارش خود را ثبت کنید." },
    ],
    icon: "🖤",
    color: "bg-muted",
    available: true,
  },
  {
    id: "bouquets",
    name: "دسته گل",
    slug: "bouquets",
    routePath: "/flower/bouquets",
    description: "سفارش دسته گل طبیعی، رز، لیلیوم و ارکیده با طراحی ژورنالی و ارسال در تهران و کرج.",
    seoTitle: "خرید دسته گل آنلاین با انواع مدل و گل + قیمت | مجلس یار",
    seoDescription: "سفارش دسته گل طبیعی برای خواستگاری، ولنتاین و تولد. گل رز، گل لیلیوم و گل عروس در طرح و گل مورد نظر شما با ارسال تهران و کرج و پرداخت در محل.",
    seoKeywords: ["دسته گل", "دسته گل رز", "دسته گل طبیعی", "خرید دسته گل", "ارسال دسته گل"],
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.bouquets,
    internalLinks: [internalPageLinks.flowerBox, internalPageLinks.fingerFood, internalPageLinks.home],
    introTitle: "توضیحات بخش دسته گل در مجلس",
    introDescription: "دسته گل‌های مجلس‌یار با گل ممتاز روزانه تهیه می‌شوند و برای هدیه، مراسم رسمی و مناسبت‌های خاص قابل سفارش هستند.",
    faqs: [
      { question: "دسته گل طبیعی با چه وسیله‌ای ارسال می‌شود؟", answer: "دسته گل در بسته‌بندی مناسب و با پیک هماهنگ‌شده به آدرس شما در تهران و کرج ارسال می‌شود." },
      { question: "آیا همراه دسته گل کارت پستال هم ارسال می‌شود؟", answer: "بله، کارت پستال با متن دلخواه شما قابل اضافه شدن است." },
      { question: "چطور ماندگاری دسته گل را بیشتر کنیم؟", answer: "گل‌ها را در آب تمیز، دور از گرمای مستقیم نگه دارید و آب ظرف را روزانه تعویض کنید." },
    ],
    icon: "🌸",
    color: "bg-primary/20",
    available: true,
  },
  {
    id: "congratulatory-wreaths",
    name: "تاج گل تبریک و افتتاحیه",
    slug: "congratulatory-wreaths",
    routePath: "/flower/congratulation-wreaths",
    description: "سفارش تاج گل تبریک برای افتتاحیه، نمایشگاه و مراسم رسمی با امکان درج متن و لوگوی شرکت.",
    seoTitle: "خرید گل تبریک، نمایشگاه و افتتاحیه + قیمت | مجلس یار",
    seoDescription: "خرید آنلاین انواع تاج گل تبریک، نمایشگاه و افتتاحیه با بالاترین کیفیت و نازل‌ترین قیمت. ارسال فوری به تهران و کرج و پرداخت در محل.",
    seoKeywords: ["تاج گل تبریک", "تاج گل افتتاحیه", "گل نمایشگاه", "گل تبریک شرکت"],
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.congratulatoryWreaths,
    internalLinks: [internalPageLinks.fingerFood, internalPageLinks.home],
    introTitle: "توضیحات بخش تاج گل تبریک و افتتاحیه",
    introDescription: "تاج گل تبریک مجلس‌یار برای افتتاحیه فروشگاه، غرفه نمایشگاهی، رویداد شرکتی و مراسم رسمی طراحی می‌شود.",
    faqs: [
      { question: "هزینه ارسال تاج گل تبریک چقدر است؟", answer: "هزینه ارسال بر اساس مقصد، فاصله و شرایط روز محاسبه و پیش از نهایی‌سازی اعلام می‌شود." },
      { question: "چند ساعت قبل باید سفارش داد؟", answer: "برای آماده‌سازی دقیق، بهتر است حداقل ۱۲ ساعت قبل از شروع مراسم سفارش ثبت شود." },
      { question: "آیا امکان درج لوگوی شرکت وجود دارد؟", answer: "بله، متن و لوگوی شرکت می‌تواند روی کارت تاج گل درج شود." },
    ],
    icon: "🎉",
    color: "bg-accent",
    available: true,
    hidden: true,
  },
  {
    id: "flower-box",
    name: "باکس گل",
    slug: "flower-box",
    routePath: "/flower/box",
    description: "خرید باکس گل لوکس با گل تازه، جعبه قابل انتخاب و ارسال در تهران و کرج.",
    seoTitle: "خرید باکس گل لوکس | ارسال فوری تهران و کرج | مجلس یار",
    seoDescription: "باکس گل مجلس‌یار با گل روز، رنگ‌بندی قابل انتخاب و طراحی نزدیک به تصویر محصول آماده می‌شود.",
    seoKeywords: ["باکس گل", "باکس گل لوکس", "خرید باکس گل", "ارسال باکس گل"],
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.flowerBox,
    internalLinks: [internalPageLinks.bouquets, internalPageLinks.fingerFood, internalPageLinks.home],
    introTitle: "توضیحات بخش باکس گل مجلس",
    introDescription: "باکس گل برای هدیه، مراسم رسمی و مناسبت‌های خاص با امکان انتخاب رنگ جعبه و نوع گل آماده می‌شود.",
    faqs: [
      { question: "چرا باکس گل مجلس ماندگاری بالاتری دارد؟", answer: "گل‌ها پس از ثبت سفارش تامین می‌شوند و با چیدمان تازه در باکس مناسب قرار می‌گیرند." },
      { question: "شرایط ارسال باکس گل چیست؟", answer: "ارسال در تهران و کرج با هماهنگی زمان تحویل و هزینه بر اساس مسیر انجام می‌شود." },
      { question: "آیا می‌توان رنگ جعبه یا نوع گل را تغییر داد؟", answer: "بله، رنگ جعبه و ترکیب گل‌ها تا حد امکان طبق درخواست شما هماهنگ می‌شود." },
    ],
    icon: "🌷",
    color: "bg-primary/20",
    available: true,
    hidden: true,
  },
  {
    id: "food",
    name: "منوی غذا",
    slug: "food",
    routePath: "/food",
    description: "منوی جامع غذا و پذیرایی مجلس‌یار شامل فینگر فود، مینی ساندویچ و شله زرد برای مراسم.",
    seoTitle: "کاتالوگ جامع خدمات غذایی مجالس | مجلس یار",
    seoDescription: "مشاهده و بررسی منوی کامل خدمات غذایی و تشریفات مجلس. ارائه پکیج پذیرایی متنوع سرد و گرم برای انواع مجالس، جشن و رویدادها در تهران و کرج.",
    seoKeywords: ["غذای مراسم", "منوی پذیرایی", "فینگر فود", "شله زرد", "مینی ساندویچ"],
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.food,
    internalLinks: [internalPageLinks.fingerFood, internalPageLinks.shalehZard, internalPageLinks.home],
    introTitle: "معرفی بخش فود در مجلس",
    introDescription: "بخش فود مجلس‌یار برای پذیرایی رسمی، دورهمی، نذری و مراسم سازمانی طراحی شده و سفارش‌ها با زمان‌بندی مشخص آماده می‌شوند.",
    faqs: [
      { question: "آیا منوی غذا قابل شخصی‌سازی است؟", answer: "بله، بر اساس تعداد مهمان، نوع مراسم و بودجه، آیتم‌ها قابل انتخاب و تغییر هستند." },
      { question: "ارسال غذا چگونه انجام می‌شود؟", answer: "ارسال با پیک یا خودروی مناسب و با هماهنگی زمان تحویل انجام می‌شود." },
    ],
    icon: "🍽️",
    color: "bg-secondary",
    available: true,
    hidden: true,
  },
  {
    id: "shaleh-zard",
    name: "شله زرد",
    slug: "shaleh-zard",
    routePath: "/food/shaleh-zard",
    description: "سفارش شله زرد مجلسی با زعفران قائنات، برنج ایرانی، گلاب، هل و تزیین اختصاصی.",
    seoTitle: "خرید شله زرد آنلاین؛ sholezard تک نفره و کیلویی + قیمت | مجلس یار",
    seoDescription: "سفارش انواع شله زرد به صورت تک نفره، کیلویی و مجلسی برای مراسم مختلف و نذری همراه با تزئین دلخواه شما با لیست مواد تشکیل دهنده مرغوب و ارسال تهران و کرج.",
    seoKeywords: ["شله زرد", "شله زرد مجلسی", "سفارش شله زرد", "شله زرد نذری", "شله زرد کیلویی"],
    benefits: sharedServiceBenefits,
    contentBlocks: pdfPageContentBlocks.shalehZard,
    internalLinks: [internalPageLinks.halvaKhorma, internalPageLinks.khormaGerdoo, internalPageLinks.home],
    introTitle: "توضیحات بخش شله",
    introDescription: "شله زرد مجلس‌یار با دستورپخت اصیل، زعفران اعلا، برنج ایرانی، گلاب و هل آماده می‌شود و در وزن‌ها و ظرف‌های متنوع قابل سفارش است.",
    faqs: [
      { question: "حداقل مقدار سفارش شله مجلسی چقدر است؟", answer: "حداقل میزان قابل سفارش برای این محصول ۴ کیلوگرم است." },
      { question: "شله مجلسی با چه موادی طبخ می‌شود؟", answer: "زعفران اصل قائنات، برنج ایرانی اعلا، گلاب، عرق هل، کره و خلال بادام درختی استفاده می‌شود." },
      { question: "آیا سفارش کیلویی یا با تزیین خاص ممکن است؟", answer: "بله، شله در وزن‌های مختلف و با تزیین دارچین، خلال و پودر نارگیل طبق طرح درخواستی آماده می‌شود." },
      { question: "نحوه ارسال شله چگونه است؟", answer: "ارسال در تهران و کرج با تاکسی اینترنتی انجام می‌شود و امکان تحویل حضوری با هماهنگی قبلی نیز وجود دارد." },
    ],
    icon: "🍮",
    color: "bg-accent",
    available: true,
  },
  hiddenEventPage(
    "pack-personal",
    "پک پذیرایی شخصی",
    "/pack/personal",
    "پک پذیرایی شخصی برای مراسم، جلسات و مهمانی‌ها با امکان انتخاب اقلام، تعداد و نوع بسته‌بندی.",
    "📦",
    "bg-secondary",
  ),
  hiddenEventPage(
    "pack-memorial-luxury",
    "پک ترحیم لوکس",
    "/pack/memorial/luxury",
    "پک ترحیم لوکس با میوه ممتاز، بسته‌بندی رسمی و اقلام پذیرایی مناسب مراسم ختم و یادبود.",
    "🕯️",
    "bg-muted",
  ),
  hiddenEventPage(
    "flower-congratulation-wreaths",
    "تاج گل تبریک",
    "/flower/congratulatory-wreaths",
    "تاج گل تبریک برای افتتاحیه، نمایشگاه، موفقیت شغلی و مناسبت‌های رسمی با طراحی گل تازه.",
    "🎉",
    "bg-accent",
    pdfPageContentBlocks.congratulatoryWreaths,
  ),
  hiddenEventPage(
    "flower-funeral-bouquet",
    "دسته گل ترحیم",
    "/flower/funeral-bouquet",
    "دسته گل ترحیم و تسلیت با چیدمان محترمانه، گل تازه و امکان ارسال هماهنگ‌شده به محل مراسم.",
    "🖤",
    "bg-muted",
  ),
  hiddenEventPage(
    "halva-khorma-luxury",
    "حلوا خرما لوکس",
    "/halva-khorma/luxury",
    "حلوا خرما لوکس برای پذیرایی مراسم ترحیم و مجالس رسمی با تزیین حرفه‌ای و مواد تازه.",
    "🍯",
    "bg-accent",
  ),
  hiddenEventPage(
    "food-charcuterie-board",
    "چاکوتری برد",
    "/food/charcuterie-board",
    "چاکوتری برد و سینی مزه برای پذیرایی رسمی، دورهمی، افتتاحیه و رویدادهای خاص.",
    "🧀",
    "bg-secondary",
  ),
  hiddenEventPage(
    "food-ashe-rashteh",
    "آش رشته",
    "/food/ashe-rashteh",
    "آش رشته مجلسی برای نذری، افطاری، مراسم و پذیرایی تعداد بالا با پخت تازه.",
    "🍲",
    "bg-secondary",
  ),
  hiddenEventPage(
    "food-dessert",
    "دسر",
    "/food/dessert",
    "دسرهای تک‌نفره و مجلسی برای جشن، مراسم، پذیرایی شرکتی و چیدمان کنار فینگر فود.",
    "🍰",
    "bg-accent",
  ),
  hiddenEventPage(
    "food-juice",
    "آبمیوه",
    "/food/juice",
    "آبمیوه و نوشیدنی پذیرایی برای پک‌های مراسم، جلسات، همایش و رویدادهای سازمانی.",
    "🧃",
    "bg-secondary",
  ),
].map(withPdfFaqs);

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
  eitaaUrl: "https://eitaa.com/majlesyar",
  soroushUrl: "https://splus.ir/majlesyar",
  rubikaUrl: "https://rubika.ir/majlesyar",
  mapsUrl: "https://maps.google.com/?q=Tehran,Valiasr",
  mapsEmbedUrl:
    "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3239.9627430068!2d51.4066!3d35.7219!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zMzXCsDQzJzE4LjgiTiA1McKwMjQnMjMuOCJF!5e0!3m2!1sen!2s!4v1699999999999!5m2!1sen!2s",
  siteLogoUrl: undefined,
  siteFaviconUrl: undefined,
  siteOgImageUrl: undefined,
  siteBranding: {
    siteName: "مجلس یار",
    siteAlternateName: "Majlesyar",
    siteTagline: "پک‌های پذیرایی ویژه مراسمات",
    logoAlt: "لوگوی مجلس یار",
    metaAuthor: "مجلس یار",
    defaultMetaTitle: "سفارش آنلاین تاج گل، پک ترحیم و حلوا خرما (ارسال فوری)",
    defaultMetaDescription:
      "مجلس یار؛ مرجع خدمات مجالس ترحیم و تولد. سفارش آنلاین حلوا خرما، پک میوه، فینگر فود و تاج گل با پایین‌ترین قیمت و ارسال فوری. برای تضمین کیفیت، بخشی از وجه را هنگام تحویل بپردازید!",
    defaultMetaKeywords: [
      "پک پذیرایی",
      "پک نذری",
      "کترینگ مراسم",
      "فینگر فود",
      "ترحیم",
      "گل مراسم",
      "مجلس یار",
      "حلوا و خرما",
    ],
    adminSiteTitle: "پنل مدیریت مجلس یار",
    adminSiteHeader: "مجلس یار",
    adminSiteSubheader: "مدیریت فروش و سفارش پک‌های پذیرایی",
    adminSiteSymbol: "inventory_2",
  },
  themePalette: {
    primary: "#00C2F2",
    accent: "#00C2F2",
    background: "#FAF8F2",
    surface: "#F2ECE2",
    foreground: "#20262F",
    mutedForeground: "#566170",
    success: "#218A52",
    warning: "#C98A10",
  },
  pageSeo: {
    home: {
      title: "سفارش آنلاین تاج گل، پک ترحیم و حلوا خرما (ارسال فوری)",
      description:
        "مجلس یار؛ مرجع خدمات مجالس ترحیم و تولد. سفارش آنلاین حلوا خرما، پک میوه، فینگر فود و تاج گل با پایین‌ترین قیمت و ارسال فوری. برای تضمین کیفیت، بخشی از وجه را هنگام تحویل بپردازید!",
      keywords: [
        "حلوا",
        "خرما",
        "حلوا و خرما",
        "پک ترحیم",
        "گل مراسم",
        "گل ترحیم",
        "سفارش حلوا",
        "سفارش خرما",
        "پذیرایی ترحیم",
      ],
    },
    builder: {
      title: "ساخت پک اختصاصی",
      description: "ساخت پک پذیرایی سفارشی با انتخاب بسته‌بندی، میوه، نوشیدنی و اسنک دلخواه",
      keywords: ["ساخت پک", "پک اختصاصی", "پک سفارشی", "پذیرایی سفارشی"],
    },
    about: {
      title: "درباره ما",
      description: "مجلس‌یار با هدف ارائه خدمات کامل و باکیفیت برای انواع مراسم و مجالس راه‌اندازی شده است.",
      keywords: ["درباره مجلس یار", "خدمات مجالس", "پذیرایی مراسم"],
    },
    contact: {
      title: "تماس با ما",
      description: "تماس با مجلس یار برای سفارش پک‌های پذیرایی. تماس تلفنی، واتساپ و اینستاگرام.",
      keywords: ["تماس", "سفارش", "مجلس یار", "شماره تماس", "واتساپ"],
    },
    cart: {
      title: "سبد خرید",
      description: "مشاهده و مدیریت سبد خرید پک‌های پذیرایی",
      keywords: ["سبد خرید", "سفارش آنلاین", "پک پذیرایی"],
    },
    checkout: {
      title: "تکمیل سفارش",
      description: "تکمیل اطلاعات و ثبت سفارش پک‌های پذیرایی",
      keywords: ["تکمیل سفارش", "ثبت سفارش", "پذیرایی مراسم"],
    },
    track: {
      title: "پیگیری سفارش",
      description: "پیگیری وضعیت سفارش پک‌های پذیرایی با کد سفارش",
      keywords: ["پیگیری سفارش", "کد سفارش", "وضعیت سفارش"],
    },
    order: {
      title: "جزئیات سفارش",
      description: "مشاهده جزئیات و وضعیت سفارش",
      keywords: ["جزئیات سفارش", "وضعیت سفارش", "سفارش مجلس یار"],
    },
  },
  eventPages: eventTypes,
  siteTopNotice: {
    title: "پرداخت در محل",
    message: "با افتخار تنها مجموعه‌ای هستیم که ۸۰ درصد از مبلغ را در زمان تحویل دریافت می‌کنیم.",
    badge: "۸۰٪ هنگام تحویل",
  },
  homepageBenefitsSection: {
    eyebrow: "تعهدهای مجلس‌یار",
    title: "مزیت‌هایی که بعد از انتخاب محصول هم کنار شما می‌ماند",
    items: [
      {
        title: "تضمین ارسال به موقع",
        description: "با افتخار تنها مجموعه‌ای هستیم که در ارسال به موقع تضمین می‌دهیم",
        note: "در صورت دیر رسیدن تمامی سفارشات رایگان تحویل داده می‌شود",
      },
      {
        title: "کیفیت عالی",
        description:
          "در مجلس‌یار اقلام مورد نیاز، بعد از سفارش شما خریداری می‌شود، تا از تازگی و کیفیت اطمینان حاصل شود.",
      },
      {
        title: "قیمت منصفانه",
        description: "با افتخار پیدا کردن محصولی پایین از قیمت مجلس‌یار تقریباً غیرممکن است.",
      },
      {
        title: "بهداشت",
        description: "و در آخر با افتخار تمامی کارکنان مجلس‌یار دارای کارت بهداشت می‌باشند.",
      },
    ],
  },
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
