import { useEffect, useMemo, useRef, useState } from 'react';
import type { KeyboardEvent, TouchEvent } from 'react';
import { ChevronLeft, ChevronRight, Package } from 'lucide-react';
import { ResponsiveProductImage } from '@/components/ResponsiveProductImage';
import type { Product } from '@/types/domain';

interface ProductImageGalleryProps {
  product: Product;
}

interface GallerySlide {
  id: string;
  src: string;
  alt: string;
  primary: boolean;
}

const SWIPE_THRESHOLD = 42;

export function ProductImageGallery({ product }: ProductImageGalleryProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [failedImages, setFailedImages] = useState<Set<string>>(() => new Set());
  const touchStartX = useRef<number | null>(null);

  const allImages = useMemo<GallerySlide[]>(() => {
    const images: GallerySlide[] = [];
    if (product.image && product.image !== '/placeholder.svg') {
      images.push({
        id: 'primary',
        src: product.image,
        alt: product.imageAlt || product.name,
        primary: true,
      });
    }
    for (const image of product.galleryImages || []) {
      if (!image.image || image.image === '/placeholder.svg') continue;
      images.push({
        id: image.id,
        src: image.image,
        alt: image.imageAlt || product.name,
        primary: false,
      });
    }
    return images;
  }, [product]);

  const images = allImages.filter((image) => !failedImages.has(image.src));
  const visibleIndex = Math.min(activeIndex, Math.max(images.length - 1, 0));

  useEffect(() => {
    setActiveIndex(0);
    setFailedImages(new Set());
  }, [product.id]);

  useEffect(() => {
    if (activeIndex !== visibleIndex) setActiveIndex(visibleIndex);
  }, [activeIndex, visibleIndex]);

  const goTo = (index: number) => {
    if (!images.length) return;
    setActiveIndex((index + images.length) % images.length);
  };

  const showPrevious = () => goTo(visibleIndex - 1);
  const showNext = () => goTo(visibleIndex + 1);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      showPrevious();
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      showNext();
    }
  };

  const handleTouchStart = (event: TouchEvent<HTMLDivElement>) => {
    touchStartX.current = event.touches[0]?.clientX ?? null;
  };

  const handleTouchEnd = (event: TouchEvent<HTMLDivElement>) => {
    if (touchStartX.current === null) return;
    const endX = event.changedTouches[0]?.clientX ?? touchStartX.current;
    const distance = endX - touchStartX.current;
    touchStartX.current = null;
    if (Math.abs(distance) < SWIPE_THRESHOLD) return;
    if (distance < 0) showNext();
    else showPrevious();
  };

  const markFailed = (src: string) => {
    setFailedImages((current) => new Set(current).add(src));
  };

  if (!images.length) {
    return (
      <div className="aspect-square bg-muted rounded-2xl border border-border relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center">
          <Package className="w-24 h-24 text-muted-foreground/40" aria-hidden="true" />
        </div>
      </div>
    );
  }

  return (
    <section aria-label={`گالری تصاویر ${product.name}`} aria-roledescription="carousel" className="space-y-3">
      <div
        className="group relative aspect-square touch-pan-y overflow-hidden rounded-2xl border border-border bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        tabIndex={images.length > 1 ? 0 : -1}
        onKeyDown={handleKeyDown}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <div
          dir="ltr"
          className="flex h-full transition-transform duration-300 ease-out motion-reduce:transition-none"
          style={{ transform: `translateX(-${visibleIndex * 100}%)` }}
        >
          {images.map((image, index) => (
            <figure
              key={image.id}
              className="h-full w-full shrink-0"
              aria-hidden={index !== visibleIndex}
            >
              {image.primary ? (
                <ResponsiveProductImage
                  product={product}
                  alt={image.alt}
                  loading={index === 0 ? 'eager' : 'lazy'}
                  fetchPriority={index === 0 ? 'high' : 'auto'}
                  sizesKey="detail"
                  sizes="(max-width: 640px) 100vw, 50vw"
                  className="h-full w-full object-cover object-center"
                  onError={() => markFailed(image.src)}
                />
              ) : (
                <img
                  src={image.src}
                  alt={image.alt}
                  loading={index === visibleIndex ? 'eager' : 'lazy'}
                  decoding="async"
                  className="h-full w-full object-cover object-center"
                  onError={() => markFailed(image.src)}
                />
              )}
            </figure>
          ))}
        </div>

        {images.length > 1 ? (
          <>
            <button
              type="button"
              onClick={showPrevious}
              aria-label="تصویر قبلی"
              className="absolute left-3 top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-white/60 bg-background/85 text-foreground shadow-lg backdrop-blur transition hover:bg-background focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ChevronLeft className="h-6 w-6" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={showNext}
              aria-label="تصویر بعدی"
              className="absolute right-3 top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-white/60 bg-background/85 text-foreground shadow-lg backdrop-blur transition hover:bg-background focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ChevronRight className="h-6 w-6" aria-hidden="true" />
            </button>
            <span
              dir="ltr"
              className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-background/85 px-3 py-1 text-xs font-semibold text-foreground shadow backdrop-blur"
              aria-live="polite"
            >
              {(visibleIndex + 1).toLocaleString('fa-IR')} / {images.length.toLocaleString('fa-IR')}
            </span>
          </>
        ) : null}
      </div>

      {images.length > 1 ? (
        <div
          dir="ltr"
          className="flex snap-x gap-2 overflow-x-auto pb-1 [scrollbar-width:thin]"
          aria-label="انتخاب تصویر محصول"
        >
          {images.map((image, index) => (
            <button
              key={image.id}
              type="button"
              onClick={() => goTo(index)}
              aria-label={`نمایش تصویر ${index + 1} از ${images.length}`}
              aria-current={index === visibleIndex ? 'true' : undefined}
              className={`h-20 w-20 shrink-0 snap-start overflow-hidden rounded-xl border-2 bg-muted transition focus:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                index === visibleIndex ? 'border-primary shadow-sm' : 'border-border opacity-75 hover:opacity-100'
              }`}
            >
              <img src={image.src} alt="" loading="lazy" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
