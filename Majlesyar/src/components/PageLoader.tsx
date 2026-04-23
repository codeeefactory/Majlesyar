import { defaultSettings } from "@/data/siteConstants";

interface PageLoaderProps {
  fullscreen?: boolean;
  brandName?: string;
}

const defaultBrandName = defaultSettings.siteBranding.siteAlternateName || "Majlesyar";

export function PageLoader({ fullscreen = true, brandName = defaultBrandName }: PageLoaderProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Loading"
      className={`relative flex items-center justify-center overflow-hidden px-6 ${
        fullscreen ? "min-h-screen bg-background" : "py-6"
      }`}
    >
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/8 blur-3xl" />
        <div className="site-loader-pulse absolute right-[12%] top-[18%] h-36 w-36 rounded-full bg-secondary/60 blur-3xl" />
        <div
          className="site-loader-pulse absolute bottom-[14%] left-[10%] h-28 w-28 rounded-full bg-primary/10 blur-3xl"
          style={{ animationDelay: "-1.4s" }}
        />
      </div>

      <div className="relative z-10 w-[min(90vw,21rem)] rounded-[2rem] border border-border/70 bg-card/80 px-7 py-7 shadow-[0_24px_80px_-40px_hsl(var(--primary)/0.45)] backdrop-blur-xl">
        <div className="relative mx-auto mb-5 flex h-24 w-24 items-center justify-center">
          <div className="site-loader-pulse absolute h-24 w-24 rounded-full bg-primary/12 blur-2xl" />
          <div className="relative flex h-20 w-20 items-center justify-center rounded-full border border-primary/15 bg-background/90">
            <div className="absolute inset-[0.45rem] rounded-full border border-primary/10" />
            <div className="absolute inset-[1.1rem] rounded-full bg-primary/12" />
            {[0, 1, 2].map((index) => (
              <span
                key={index}
                className="site-loader-orbit absolute left-1/2 top-1/2 block h-3 w-3 rounded-full bg-primary"
                style={{
                  animationDelay: `-${index * 0.8}s`,
                  boxShadow: "0 0 0 6px hsl(var(--primary) / 0.08)",
                }}
              />
            ))}
            <span className="site-loader-float relative h-3.5 w-3.5 rounded-full bg-primary shadow-[0_0_24px_hsl(var(--primary)/0.32)]" />
          </div>
        </div>

        <div className="space-y-3 text-center">
          <div className="mx-auto h-px w-14 bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
          <p className="truncate text-xs font-semibold tracking-[0.34em] text-primary/80">{brandName}</p>
        </div>

        <div className="mt-5 overflow-hidden rounded-full bg-muted/85">
          <div className="relative h-1.5 rounded-full bg-[linear-gradient(90deg,hsl(var(--primary)/0.18),hsl(var(--primary)/0.56),hsl(var(--primary)/0.18))]">
            <span className="site-loader-shimmer absolute inset-y-0 left-0 w-20 bg-[linear-gradient(90deg,transparent,hsl(var(--background)/0.96),transparent)]" />
          </div>
        </div>

        <span className="sr-only">Loading</span>
      </div>
    </div>
  );
}
