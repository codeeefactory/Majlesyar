import type { ReactEventHandler } from 'react';
import type { Product, ProductImageVariant } from '@/types/domain';

interface ResponsiveProductImageProps {
  product: Product;
  alt: string;
  className?: string;
  loading?: 'lazy' | 'eager';
  fetchPriority?: 'high' | 'low' | 'auto';
  sizesKey?: 'card' | 'detail';
  sizes?: string;
  onError?: ReactEventHandler<HTMLImageElement>;
}

function buildSrcSet(variants: ProductImageVariant[]): string | undefined {
  if (!variants.length) return undefined;
  return variants.map((variant) => `${variant.url} ${variant.width}w`).join(', ');
}

export function ResponsiveProductImage({
  product,
  alt,
  className,
  loading = 'lazy',
  fetchPriority = 'auto',
  sizesKey = 'card',
  sizes,
  onError,
}: ResponsiveProductImageProps) {
  const responsive = product.imageResponsive;
  const avifSrcSet = buildSrcSet(responsive?.formats.avif || []);
  const webpSrcSet = buildSrcSet(responsive?.formats.webp || []);
  const jpegSrcSet = buildSrcSet(responsive?.formats.jpeg || []);
  const fallbackSizes = sizes || responsive?.fallback?.sizes?.[sizesKey] || '(max-width: 640px) 100vw, 33vw';
  const fallbackSrc = responsive?.fallback?.src || product.image;
  const width = responsive?.width || responsive?.fallback?.width || undefined;
  const height = responsive?.height || responsive?.fallback?.height || undefined;

  return (
    <picture>
      {avifSrcSet ? <source type="image/avif" srcSet={avifSrcSet} sizes={fallbackSizes} /> : null}
      {webpSrcSet ? <source type="image/webp" srcSet={webpSrcSet} sizes={fallbackSizes} /> : null}
      <img
        src={fallbackSrc}
        srcSet={jpegSrcSet}
        sizes={fallbackSizes}
        alt={alt}
        width={width}
        height={height}
        loading={loading}
        fetchPriority={fetchPriority}
        decoding="async"
        className={className}
        onError={onError}
      />
    </picture>
  );
}
