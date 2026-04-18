import { useEffect } from "react";
import { useSettings } from "@/contexts/SettingsContext";

function hexToRgb(hex: string) {
  const normalized = hex.trim().replace("#", "");
  const expanded =
    normalized.length === 3
      ? normalized
          .split("")
          .map((value) => value + value)
          .join("")
      : normalized;

  const red = Number.parseInt(expanded.slice(0, 2), 16);
  const green = Number.parseInt(expanded.slice(2, 4), 16);
  const blue = Number.parseInt(expanded.slice(4, 6), 16);
  return { red, green, blue };
}

function rgbToHslChannels(red: number, green: number, blue: number) {
  const r = red / 255;
  const g = green / 255;
  const b = blue / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const lightness = (max + min) / 2;

  if (max === min) {
    return `0 0% ${Math.round(lightness * 100)}%`;
  }

  const delta = max - min;
  const saturation =
    lightness > 0.5 ? delta / (2 - max - min) : delta / (max + min);

  let hue = 0;
  switch (max) {
    case r:
      hue = (g - b) / delta + (g < b ? 6 : 0);
      break;
    case g:
      hue = (b - r) / delta + 2;
      break;
    default:
      hue = (r - g) / delta + 4;
  }

  hue /= 6;
  return `${Math.round(hue * 360)} ${Math.round(saturation * 100)}% ${Math.round(lightness * 100)}%`;
}

function mixHex(base: string, overlay: string, ratio: number) {
  const amount = Math.max(0, Math.min(1, ratio));
  const baseRgb = hexToRgb(base);
  const overlayRgb = hexToRgb(overlay);
  const red = Math.round(baseRgb.red * (1 - amount) + overlayRgb.red * amount);
  const green = Math.round(baseRgb.green * (1 - amount) + overlayRgb.green * amount);
  const blue = Math.round(baseRgb.blue * (1 - amount) + overlayRgb.blue * amount);
  return `#${[red, green, blue].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function getReadableTextColor(background: string) {
  const { red, green, blue } = hexToRgb(background);
  const brightness = (red * 299 + green * 587 + blue * 114) / 1000;
  return brightness > 148 ? "#111827" : "#FFFFFF";
}

function toHslChannels(hex: string) {
  const { red, green, blue } = hexToRgb(hex);
  return rgbToHslChannels(red, green, blue);
}

function setMetaTag(name: string, content: string) {
  if (typeof document === "undefined") return;
  const selector = `meta[name="${name}"]`;
  let tag = document.head.querySelector(selector) as HTMLMetaElement | null;
  if (!tag) {
    tag = document.createElement("meta");
    tag.setAttribute("name", name);
    document.head.appendChild(tag);
  }
  tag.setAttribute("content", content);
}

function upsertLink(rel: string, href: string) {
  if (typeof document === "undefined") return;
  const selector = `link[rel="${rel}"]`;
  let link = document.head.querySelector(selector) as HTMLLinkElement | null;
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("rel", rel);
    document.head.appendChild(link);
  }
  link.href = href;
}

export function SiteThemeSync() {
  const { settings } = useSettings();

  useEffect(() => {
    const root = document.documentElement;
    const palette = settings.themePalette;

    const primaryForeground = getReadableTextColor(palette.primary);
    const accentForeground = getReadableTextColor(palette.accent);
    const successForeground = getReadableTextColor(palette.success);
    const warningForeground = getReadableTextColor(palette.warning);
    const secondary = mixHex(palette.background, palette.primary, 0.12);
    const secondaryForeground = mixHex(palette.foreground, palette.primary, 0.08);
    const accentSurface = mixHex(palette.background, palette.accent, 0.18);
    const muted = mixHex(palette.background, palette.foreground, 0.06);
    const border = mixHex(palette.surface, palette.foreground, 0.16);
    const ring = mixHex(palette.primary, "#FFFFFF", 0.16);
    const glowColor = hexToRgb(palette.primary);

    const cssColors = {
      "--background": toHslChannels(palette.background),
      "--foreground": toHslChannels(palette.foreground),
      "--card": toHslChannels(palette.surface),
      "--card-foreground": toHslChannels(palette.foreground),
      "--popover": toHslChannels(palette.surface),
      "--popover-foreground": toHslChannels(palette.foreground),
      "--primary": toHslChannels(palette.primary),
      "--primary-foreground": toHslChannels(primaryForeground),
      "--secondary": toHslChannels(secondary),
      "--secondary-foreground": toHslChannels(secondaryForeground),
      "--muted": toHslChannels(muted),
      "--muted-foreground": toHslChannels(palette.mutedForeground),
      "--accent": toHslChannels(accentSurface),
      "--accent-foreground": toHslChannels(accentForeground),
      "--success": toHslChannels(palette.success),
      "--success-foreground": toHslChannels(successForeground),
      "--warning": toHslChannels(palette.warning),
      "--warning-foreground": toHslChannels(warningForeground),
      "--border": toHslChannels(border),
      "--input": toHslChannels(border),
      "--ring": toHslChannels(ring),
      "--sidebar-background": toHslChannels(mixHex(palette.background, palette.surface, 0.5)),
      "--sidebar-foreground": toHslChannels(palette.foreground),
      "--sidebar-primary": toHslChannels(palette.primary),
      "--sidebar-primary-foreground": toHslChannels(primaryForeground),
      "--sidebar-accent": toHslChannels(accentSurface),
      "--sidebar-accent-foreground": toHslChannels(accentForeground),
      "--sidebar-border": toHslChannels(border),
      "--sidebar-ring": toHslChannels(ring),
    };

    Object.entries(cssColors).forEach(([name, value]) => {
      root.style.setProperty(name, value);
    });

    root.style.setProperty("--gold-gradient", `linear-gradient(135deg, ${palette.accent} 0%, ${mixHex(palette.accent, palette.primary, 0.22)} 100%)`);
    root.style.setProperty("--teal-gradient", `linear-gradient(135deg, ${mixHex(palette.primary, "#FFFFFF", 0.12)} 0%, ${mixHex(palette.primary, "#000000", 0.12)} 100%)`);
    root.style.setProperty("--cream-gradient", `linear-gradient(180deg, ${palette.background} 0%, ${mixHex(palette.background, palette.surface, 0.45)} 100%)`);
    root.style.setProperty("--shadow-soft", `0 4px 20px -4px rgb(${glowColor.red} ${glowColor.green} ${glowColor.blue} / 0.10)`);
    root.style.setProperty("--shadow-medium", `0 8px 30px -8px rgb(${glowColor.red} ${glowColor.green} ${glowColor.blue} / 0.18)`);
    root.style.setProperty("--shadow-glow", `0 0 40px rgb(${glowColor.red} ${glowColor.green} ${glowColor.blue} / 0.22)`);

    setMetaTag("theme-color", palette.primary);
    setMetaTag("msapplication-TileColor", palette.primary);
    setMetaTag("msapplication-navbutton-color", palette.primary);

    if (settings.siteFaviconUrl) {
      upsertLink("icon", settings.siteFaviconUrl);
      upsertLink("apple-touch-icon", settings.siteFaviconUrl);
    }
  }, [settings]);

  return null;
}
