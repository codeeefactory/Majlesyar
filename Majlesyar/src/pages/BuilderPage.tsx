import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { AppShell } from '@/components/layout';
import { SEO } from '@/components/SEO';
import { Button } from '@/components/ui/button';
import { RuleAlert } from '@/components/RuleAlert';
import { getBuilderConfig } from '@/lib/api';
import { notifySuccess } from '@/lib/notify';
import { cn } from '@/lib/utils';
import { useCart } from '@/contexts/CartContext';
import type { BuilderItem } from '@/types/domain';
import {
  ArrowLeft,
  ArrowRight,
  Box,
  Check,
  HelpCircle,
  Loader2,
  Minus,
  Package,
  Plus,
  RotateCcw,
  ShoppingCart,
  Sparkles,
} from 'lucide-react';

type BaseStep = 'packaging' | 'fruit' | 'drink' | 'snack' | 'addons' | 'quantity';
type ChoiceStep = Exclude<BaseStep, 'quantity'>;
type ChoiceSource = 'builder';

interface BuilderChoice {
  id: string;
  name: string;
  group: Exclude<BaseStep, 'quantity'>;
  price: number;
  required: boolean;
  image?: string;
  source: ChoiceSource;
  productId?: string;
  categoryIds: string[];
  description?: string;
  model3dUrl?: string;
  model3dStatus?: 'missing' | 'queued' | 'processing' | 'ready' | 'failed';
}

interface BuilderSceneControls {
  rotateLeft: () => void;
  rotateRight: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  reset: () => void;
}

interface BuilderSceneStats {
  webglReady: boolean;
  loadedModels: number;
  failedModels: number;
}

interface Selections {
  packaging: string[];
  fruit: string[];
  drink: string[];
  snack: string[];
  addons: string[];
}

type TelegramHapticStyle = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft';

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready?: () => void;
        expand?: () => void;
        setHeaderColor?: (color: string) => void;
        setBackgroundColor?: (color: string) => void;
        HapticFeedback?: {
          impactOccurred?: (style: TelegramHapticStyle) => void;
          notificationOccurred?: (type: 'error' | 'success' | 'warning') => void;
          selectionChanged?: () => void;
        };
      };
    };
  }
}

const stepLabels: Record<BaseStep, string> = {
  packaging: 'بسته‌بندی',
  fruit: 'میوه',
  drink: 'نوشیدنی',
  snack: 'کیک/اسنک',
  addons: 'افزودنی‌ها',
  quantity: 'تعداد',
};

const stepOrder: BaseStep[] = ['packaging', 'fruit', 'drink', 'snack', 'addons', 'quantity'];
const BUILDER_3D_PREVIEW_ENABLED = true;
const choiceSteps: ChoiceStep[] = ['packaging', 'fruit', 'drink', 'snack', 'addons'];
const stepStories: Record<BaseStep, string> = {
  packaging: 'اول جعبه را انتخاب کن؛ صحنه باز می‌شود و آماده چیدن می‌ماند.',
  fruit: 'میوه‌ها کنار جعبه ظاهر می‌شوند و برای چیدمان نهایی آماده‌اند.',
  drink: 'نوشیدنی‌ها مثل آیتم‌های بازی وارد صف کنار جعبه می‌شوند.',
  snack: 'کیک یا اسنک وزن پک را کامل‌تر می‌کند.',
  addons: 'افزودنی‌ها اختیاری‌اند؛ هر انتخاب کنار جعبه اضافه می‌شود.',
  quantity: 'حالا جعبه بسته می‌شود؛ تعداد را بزن و پک را به سبد بفرست.',
};
const stepHints: Record<BaseStep, string> = {
  packaging: 'انتخاب چند بسته‌بندی آزاد است',
  fruit: 'چند میوه را هم‌زمان انتخاب کن',
  drink: 'چند نوشیدنی را هم‌زمان انتخاب کن',
  snack: 'چند خوراکی را هم‌زمان انتخاب کن',
  addons: 'چند انتخاب آزاد',
  quantity: 'مرحله نهایی',
};
function triggerHaptic(type: 'select' | 'impact' | 'success' = 'select') {
  const feedback = window.Telegram?.WebApp?.HapticFeedback;
  if (!feedback) return;
  if (type === 'success') feedback.notificationOccurred?.('success');
  else if (type === 'impact') feedback.impactOccurred?.('light');
  else feedback.selectionChanged?.();
}

function toChoice(item: BuilderItem): BuilderChoice {
  return {
    id: `builder:${item.id}`,
    name: item.name,
    group: item.group === 'addon' ? 'addons' : item.group,
    price: item.price,
    required: item.required,
    image: item.image,
    source: 'builder',
    categoryIds: [],
    model3dUrl: item.model3dUrl,
    model3dStatus: item.model3dStatus,
  };
}

function useBuilderScene({
  canvasRef,
  currentStep,
  selectedChoices,
  totalPrice,
  quantity,
  selections,
}: {
  canvasRef: React.RefObject<HTMLCanvasElement>;
  currentStep: BaseStep;
  selectedChoices: BuilderChoice[];
  totalPrice: number;
  quantity: number;
  selections: Selections;
}) {
  const imageCacheRef = useRef<Map<string, HTMLImageElement>>(new Map());

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const styles = getComputedStyle(document.documentElement);
    const theme = {
      background: `hsl(${styles.getPropertyValue('--background').trim() || '222 47% 11%'})`,
      card: `hsl(${styles.getPropertyValue('--card').trim() || '222 47% 13%'})`,
      muted: `hsl(${styles.getPropertyValue('--muted').trim() || '217 32% 18%'})`,
      foreground: `hsl(${styles.getPropertyValue('--foreground').trim() || '210 40% 98%'})`,
      mutedForeground: `hsl(${styles.getPropertyValue('--muted-foreground').trim() || '215 20% 65%'})`,
      primary: `hsl(${styles.getPropertyValue('--primary').trim() || '192 88% 41%'})`,
      border: `hsl(${styles.getPropertyValue('--border').trim() || '217 32% 22%'})`,
      accent: `hsl(${styles.getPropertyValue('--accent').trim() || '37 58% 60%'})`,
    };

    const imageCache = imageCacheRef.current;
    selectedChoices.forEach((choice) => {
      if (!choice.image || imageCache.has(choice.image)) return;
      const image = new Image();
      image.crossOrigin = 'anonymous';
      image.decoding = 'async';
      image.src = choice.image;
      imageCache.set(choice.image, image);
    });

    let elapsed = 0;
    let lastTime = performance.now();
    let raf = 0;
    const isCoarsePointer = window.matchMedia('(pointer: coarse)').matches;
    const dpr = Math.min(window.devicePixelRatio || 1, isCoarsePointer ? 1.25 : 1.5);
    const pointer = { x: 0, y: 0, active: false };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const nextWidth = Math.max(320, Math.floor(rect.width * dpr));
      const nextHeight = Math.max(230, Math.floor(rect.height * dpr));
      if (canvas.width === nextWidth && canvas.height === nextHeight) return;
      canvas.width = nextWidth;
      canvas.height = nextHeight;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
    };

    const pathRoundedRect = (x: number, y: number, width: number, height: number, radius: number) => {
      ctx.beginPath();
      if ('roundRect' in ctx) {
        ctx.roundRect(x, y, width, height, radius);
        return;
      }
      const r = Math.min(radius, Math.abs(width) / 2, Math.abs(height) / 2);
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + width - r, y);
      ctx.quadraticCurveTo(x + width, y, x + width, y + r);
      ctx.lineTo(x + width, y + height - r);
      ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
      ctx.lineTo(x + r, y + height);
      ctx.quadraticCurveTo(x, y + height, x, y + height - r);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
    };

    const drawRoundedRect = (x: number, y: number, width: number, height: number, radius: number) => {
      pathRoundedRect(x, y, width, height, radius);
      ctx.fill();
    };

    const easeOutCubic = (value: number) => 1 - Math.pow(1 - value, 3);
    const easeOutBack = (value: number) => {
      const c1 = 1.70158;
      const c3 = c1 + 1;
      return 1 + c3 * Math.pow(value - 1, 3) + c1 * Math.pow(value - 1, 2);
    };

    const drawSpark = (x: number, y: number, size: number, alpha: number) => {
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = '#d6a45b';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x - size, y);
      ctx.lineTo(x + size, y);
      ctx.moveTo(x, y - size);
      ctx.lineTo(x, y + size);
      ctx.stroke();
      ctx.restore();
    };

    const drawItemIcon = (choice: BuilderChoice, x: number, y: number, size: number, rotation = 0) => {
      const image = choice.image ? imageCache.get(choice.image) : undefined;
      const palette = choice.group === 'fruit'
        ? '#ef6f4d'
        : choice.group === 'drink'
        ? '#0c9fc7'
        : choice.group === 'snack'
        ? '#d6a45b'
        : choice.group === 'packaging'
        ? '#5aa986'
        : '#7bbf75';
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(rotation);
      ctx.shadowColor = 'rgba(36, 48, 58, 0.16)';
      ctx.shadowBlur = 10;
      ctx.shadowOffsetY = 5;
      ctx.fillStyle = palette;
      if (image?.complete && image.naturalWidth > 0) {
        pathRoundedRect(-size * 0.58, -size * 0.58, size * 1.16, size * 1.16, size * 0.22);
        ctx.fill();
        ctx.clip();
        ctx.drawImage(image, -size * 0.58, -size * 0.58, size * 1.16, size * 1.16);
        ctx.restore();
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(rotation);
        ctx.strokeStyle = 'rgba(255,255,255,0.82)';
        ctx.lineWidth = 2;
        pathRoundedRect(-size * 0.58, -size * 0.58, size * 1.16, size * 1.16, size * 0.22);
        ctx.stroke();
      } else if (choice.group === 'drink') {
        drawRoundedRect(-size * 0.32, -size * 0.52, size * 0.64, size * 1.04, size * 0.16);
        ctx.fillStyle = 'rgba(255,255,255,0.75)';
        drawRoundedRect(-size * 0.16, -size * 0.34, size * 0.32, size * 0.18, 4);
      } else if (choice.group === 'snack') {
        drawRoundedRect(-size * 0.55, -size * 0.38, size * 1.1, size * 0.76, size * 0.18);
        ctx.fillStyle = 'rgba(255,255,255,0.55)';
        drawRoundedRect(-size * 0.34, -size * 0.15, size * 0.68, size * 0.14, 4);
      } else {
        ctx.beginPath();
        ctx.arc(0, 0, size * 0.48, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = 'rgba(255,255,255,0.7)';
        ctx.beginPath();
        ctx.arc(-size * 0.16, -size * 0.16, size * 0.12, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.shadowColor = 'transparent';
      ctx.restore();
    };

    const drawHudPill = (label: string, x: number, y: number, active: boolean, done: boolean) => {
      const width = Math.max(58, label.length * 8 + 28);
      ctx.fillStyle = done ? 'rgba(16, 185, 129, 0.22)' : active ? 'rgba(12, 159, 199, 0.95)' : 'rgba(255, 255, 255, 0.08)';
      drawRoundedRect(x - width / 2, y - 17, width, 34, 17);
      ctx.fillStyle = active ? '#06121f' : done ? '#8ef4c1' : theme.mutedForeground;
      ctx.font = '800 11px Vazirmatn, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`${done ? '✓ ' : ''}${label}`, x, y + 4);
    };

    const drawSummaryHud = (width: number, height: number) => {
      const panelX = width * 0.035;
      const panelY = height * 0.12;
      const panelW = Math.min(250, width * 0.26);
      const panelH = height * 0.68;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.055)';
      drawRoundedRect(panelX, panelY, panelW, panelH, 22);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
      ctx.lineWidth = 1;
      pathRoundedRect(panelX, panelY, panelW, panelH, 22);
      ctx.stroke();

      ctx.fillStyle = theme.foreground;
      ctx.font = '900 14px Vazirmatn, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText('خلاصه پک', panelX + panelW - 18, panelY + 31);
      ctx.fillStyle = theme.primary;
      ctx.font = '900 12px Vazirmatn, sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(`${selectedChoices.length.toLocaleString('fa-IR')} آیتم`, panelX + 18, panelY + 31);

      const summaryRows: Array<[string, string]> = [
        [stepLabels.packaging, selections.packaging.length ? `${selections.packaging.length.toLocaleString('fa-IR')} انتخاب` : '-'],
        [stepLabels.fruit, selections.fruit.length ? `${selections.fruit.length.toLocaleString('fa-IR')} انتخاب` : '-'],
        [stepLabels.drink, selections.drink.length ? `${selections.drink.length.toLocaleString('fa-IR')} انتخاب` : '-'],
        [stepLabels.snack, selections.snack.length ? `${selections.snack.length.toLocaleString('fa-IR')} انتخاب` : '-'],
        [stepLabels.addons, selections.addons.length ? `${selections.addons.length.toLocaleString('fa-IR')} انتخاب` : '-'],
      ];

      ctx.font = '800 11px Vazirmatn, sans-serif';
      summaryRows.forEach(([label, value], index) => {
        const y = panelY + 62 + index * 27;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.fillRect(panelX + 16, y + 9, panelW - 32, 1);
        ctx.fillStyle = theme.mutedForeground;
        ctx.textAlign = 'right';
        ctx.fillText(label, panelX + panelW - 18, y);
        ctx.fillStyle = value === '-' ? theme.mutedForeground : theme.primary;
        ctx.textAlign = 'left';
        ctx.fillText(value, panelX + 18, y);
      });

      const totalY = panelY + panelH - 58;
      ctx.fillStyle = 'rgba(12, 159, 199, 0.13)';
      drawRoundedRect(panelX + 16, totalY - 18, panelW - 32, 46, 14);
      ctx.fillStyle = theme.mutedForeground;
      ctx.textAlign = 'right';
      ctx.font = '800 11px Vazirmatn, sans-serif';
      ctx.fillText('جمع', panelX + panelW - 28, totalY);
      ctx.fillText('تعداد', panelX + panelW - 28, totalY + 20);
      ctx.fillStyle = theme.primary;
      ctx.textAlign = 'left';
      ctx.fillText(`${(totalPrice * quantity).toLocaleString('fa-IR')} تومان`, panelX + 28, totalY);
      ctx.fillText(quantity.toLocaleString('fa-IR'), panelX + 28, totalY + 20);
    };

    const draw = (timestamp = performance.now()) => {
      if (document.hidden) {
        lastTime = timestamp;
        raf = 0;
        return;
      }
      const delta = prefersReducedMotion ? 16 : Math.min(34, timestamp - lastTime);
      lastTime = timestamp;
      elapsed += prefersReducedMotion ? 0 : delta;
      const width = canvas.width / dpr;
      const height = canvas.height / dpr;
      const compact = width < 700;
      const t = elapsed / 1000;
      const tick = elapsed / 16.67;
      const parallaxX = pointer.active ? pointer.x * 12 : Math.sin(t * 0.6) * 3;
      const parallaxY = pointer.active ? pointer.y * 8 : Math.cos(t * 0.7) * 2;
      ctx.clearRect(0, 0, width, height);

      const bg = ctx.createLinearGradient(0, 0, width, height);
      bg.addColorStop(0, theme.card);
      bg.addColorStop(0.55, theme.background);
      bg.addColorStop(1, theme.muted);
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
      ctx.lineWidth = 1;
      for (let x = -40 + ((tick * 0.42) % 40); x < width + 40; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x + 80, height);
        ctx.stroke();
      }

      const glow = ctx.createRadialGradient(
        width * 0.58 + parallaxX,
        height * 0.48 + parallaxY,
        20,
        width * 0.58 + parallaxX,
        height * 0.48 + parallaxY,
        width * 0.42,
      );
      glow.addColorStop(0, 'rgba(214, 164, 91, 0.18)');
      glow.addColorStop(0.55, 'rgba(12, 159, 199, 0.12)');
      glow.addColorStop(1, 'rgba(12, 159, 199, 0)');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, width, height);

      if (!compact) drawSummaryHud(width, height);

      const trayX = compact ? width * 0.07 : width * 0.32;
      const trayY = compact ? height * 0.2 : height * 0.12;
      const trayW = compact ? Math.min(96, width * 0.22) : Math.min(220, width * 0.2);

      if (!compact && selectedChoices.length > 9999) {
      ctx.fillStyle = 'rgba(255, 255, 255, 0.045)';
      drawRoundedRect(trayX, trayY, trayW, height * 0.68, 22);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      ctx.lineWidth = 1;
      pathRoundedRect(trayX + 4, trayY + 4, trayW - 8, height * 0.68 - 8, 18);
      ctx.stroke();
      ctx.fillStyle = theme.foreground;
      ctx.font = '800 13px Vazirmatn, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('محصولات انتخابی', trayX + trayW / 2 + parallaxX * 0.12, height * 0.18);

      }

      const trayChoices = [] as BuilderChoice[];
      trayChoices.forEach((choice, index) => {
        const col = index % 2;
        const row = Math.floor(index / 2);
        const x = trayX + trayW * 0.28 + col * trayW * 0.42 + parallaxX * 0.18;
        const y = height * 0.27 + row * 46 + Math.sin(t * 3 + index) * 2 + parallaxY * 0.1;
        drawItemIcon(choice, x, y, 26, Math.sin(t + index) * 0.1);
      });

      const tableY = compact ? height * 0.76 : height * 0.78;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.12)';
      drawRoundedRect(compact ? width * 0.08 : width * 0.28, tableY, compact ? width * 0.84 : width * 0.64, 24, 12);
      ctx.fillStyle = 'rgba(255, 255, 255, 0.22)';
      for (let x = (compact ? width * 0.12 : width * 0.3) + ((tick * 0.95) % 38); x < width * 0.88; x += 38) {
        drawRoundedRect(x, tableY + 7, 20, 4, 2);
      }

      const packX = (compact ? width * 0.5 : width * 0.58) - 112 + parallaxX * 0.24;
      const packY = (compact ? height * 0.45 : height * 0.48) + parallaxY * 0.2;
      const packBob = Math.sin(t * 2) * 2;
      const itemCount = selectedChoices.length;
      const isComplete = currentStep === 'quantity';
      const openProgress = easeOutCubic(isComplete ? Math.max(0, 1 - elapsed / 900) : Math.min(1, elapsed / 650));
      const closeProgress = isComplete ? Math.min(1, elapsed / 850) : 0;

      ctx.save();
      ctx.globalAlpha = 0.24;
      ctx.fillStyle = '#24303a';
      ctx.beginPath();
      ctx.ellipse(packX + 112, tableY + 6, 132, 18, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      ctx.shadowColor = 'rgba(0, 0, 0, 0.38)';
      ctx.shadowBlur = 18;
      ctx.shadowOffsetY = 10;
      const boxGradient = ctx.createLinearGradient(packX, packY, packX + 224, packY + 104);
      boxGradient.addColorStop(0, isComplete ? '#fff8e6' : '#ffffff');
      boxGradient.addColorStop(0.52, '#fff2d4');
      boxGradient.addColorStop(1, '#e8bf76');
      ctx.fillStyle = boxGradient;
      drawRoundedRect(packX, packY + packBob, 224, 104, 18);
      ctx.shadowColor = 'transparent';

      ctx.fillStyle = 'rgba(214, 164, 91, 0.32)';
      ctx.beginPath();
      ctx.moveTo(packX + 12, packY + 22 + packBob);
      ctx.lineTo(packX + 52, packY - 24 + packBob);
      ctx.lineTo(packX + 110, packY + 18 + packBob);
      ctx.lineTo(packX + 72, packY + 44 + packBob);
      ctx.closePath();
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(packX + 212, packY + 22 + packBob);
      ctx.lineTo(packX + 172, packY - 24 + packBob);
      ctx.lineTo(packX + 114, packY + 18 + packBob);
      ctx.lineTo(packX + 152, packY + 44 + packBob);
      ctx.closePath();
      ctx.fill();

      ctx.strokeStyle = '#d6a45b';
      ctx.lineWidth = 3;
      ctx.strokeRect(packX + 24, packY + 22 + packBob, 176, 58);
      ctx.fillStyle = 'rgba(214, 164, 91, 0.15)';
      drawRoundedRect(packX + 32, packY + 30 + packBob, 160, 42, 10);

      if (!isComplete) {
        selectedChoices.slice(-10).forEach((choice, index) => {
          const progress = Math.min(1, Math.max(0, (elapsed - index * 130) / 720));
          const ease = easeOutBack(progress);
          const side = index % 2 === 0 ? -1 : 1;
          const startX = packX + 112 + side * (compact ? 92 : 160) + Math.sin(t * 1.8 + index) * 12;
          const startY = packY - (compact ? 58 : 82) + (index % 4) * 24 + Math.cos(t * 1.5 + index) * 8;
          const targetX = packX + 64 + (index % 5) * 24;
          const targetY = packY + 46 + Math.floor(index / 5) * 18 + packBob;
          const x = startX + (targetX - startX) * ease;
          const y = startY + (targetY - startY) * ease - Math.sin(progress * Math.PI) * 72;
          drawItemIcon(choice, x, y, 22 + Math.sin(progress * Math.PI) * 4, (1 - progress) * 0.8 + Math.sin(t + index) * 0.08);
          if (progress > 0.78 && progress < 1) {
            drawSpark(targetX + 16, targetY - 8, 6 + Math.sin(t * 8) * 2, 1 - progress);
          }
        });
      } else {
        selectedChoices.slice(-8).forEach((choice, index) => {
          drawItemIcon(choice, packX + 62 + (index % 4) * 34, packY + 52 + Math.floor(index / 4) * 20 + packBob, 18, 0);
        });
      }

      const lidLift = 64 * openProgress * (1 - closeProgress);
      ctx.save();
      ctx.translate(packX + 112, packY + 12 + packBob - lidLift);
      ctx.rotate(-0.52 * openProgress * (1 - closeProgress));
      const lidGradient = ctx.createLinearGradient(-98, -14, 98, 12);
      lidGradient.addColorStop(0, '#fffaf0');
      lidGradient.addColorStop(1, '#e9bd72');
      ctx.fillStyle = lidGradient;
      drawRoundedRect(-98, -14, 196, 26, 10);
      ctx.restore();

      if (isComplete) {
        const sparkCount = isCoarsePointer ? 5 : 8;
        for (let i = 0; i < sparkCount; i += 1) {
          const angle = t * 1.8 + i * 0.8;
          const sparkleX = packX + 112 + Math.cos(angle) * (94 + (i % 2) * 18);
          const sparkleY = packY + 36 + packBob + Math.sin(angle * 1.3) * 44;
          drawSpark(sparkleX, sparkleY, 4 + (i % 3), 0.35 + Math.sin(t * 4 + i) * 0.25);
        }
        ctx.fillStyle = 'rgba(214, 164, 91, 0.7)';
        drawRoundedRect(packX + 78, packY + 45 + packBob, 68, 18, 8);
        ctx.fillStyle = '#24303a';
        ctx.font = '900 13px Vazirmatn, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('پک کامل شد', packX + 112, packY + 59 + packBob);
      }

      const badgeText = itemCount
        ? isComplete
          ? 'جعبه بسته شد'
          : 'آیتم‌ها داخل جعبه می‌روند'
        : 'اول یک محصول انتخاب کنید';
      ctx.fillStyle = 'rgba(12, 159, 199, 0.16)';
      drawRoundedRect(compact ? width * 0.18 : width * 0.68, height * 0.14, compact ? width * 0.64 : width * 0.24, 44, 18);
      ctx.fillStyle = theme.primary;
      ctx.font = `900 ${compact ? 11 : 13}px Vazirmatn, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText(badgeText, compact ? width * 0.5 : width * 0.8, height * 0.17 + 18);

      if (!compact) {
      ctx.fillStyle = theme.foreground;
      ctx.font = '800 15px Vazirmatn, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(stepLabels[currentStep], width - 22, 32);
      ctx.font = '700 12px Vazirmatn, sans-serif';
      ctx.fillStyle = theme.primary;
      ctx.fillText(`${totalPrice.toLocaleString('fa-IR')} تومان / هر پک`, width - 22, 54);

      }

      if (!compact) {
      const chipY = height - 30;
      const availableWidth = width * 0.6;
      const startX = width * 0.38;
      stepOrder.forEach((step, index) => {
        const x = startX + (availableWidth / Math.max(stepOrder.length - 1, 1)) * index;
        drawHudPill(stepLabels[step], x, chipY, step === currentStep, index < stepOrder.indexOf(currentStep));
      });
      }

      if (!prefersReducedMotion) raf = requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener('resize', resize);
    const handlePointerMove = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
      pointer.y = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
      pointer.active = true;
    };
    const handlePointerLeave = () => {
      pointer.active = false;
    };
    canvas.addEventListener('pointermove', handlePointerMove, { passive: true });
    canvas.addEventListener('pointerleave', handlePointerLeave);
    const handleVisibilityChange = () => {
      lastTime = performance.now();
      if (!document.hidden && !raf) {
        raf = requestAnimationFrame(draw);
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    raf = requestAnimationFrame(draw);
    return () => {
      window.removeEventListener('resize', resize);
      canvas.removeEventListener('pointermove', handlePointerMove);
      canvas.removeEventListener('pointerleave', handlePointerLeave);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      cancelAnimationFrame(raf);
    };
  }, [canvasRef, currentStep, selectedChoices, totalPrice, quantity, selections]);
}

function useBuilderScene3D({
  canvasRef,
  currentStep,
  selectedChoices,
  totalPrice,
  quantity,
  controlsRef,
  onStats,
}: {
  canvasRef: React.RefObject<HTMLCanvasElement>;
  currentStep: BaseStep;
  selectedChoices: BuilderChoice[];
  totalPrice: number;
  quantity: number;
  controlsRef: React.MutableRefObject<BuilderSceneControls | null>;
  onStats: React.Dispatch<React.SetStateAction<BuilderSceneStats>>;
}) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const styles = getComputedStyle(document.documentElement);
    const cssVarColor = (name: string, fallback: [number, number, number]) => {
      const raw = styles.getPropertyValue(name).trim();
      const match = raw.match(/([\d.]+)\s+([\d.]+)%\s+([\d.]+)%/);
      const [h, s, l] = match
        ? [Number(match[1]), Number(match[2]), Number(match[3])]
        : fallback;
      return new THREE.Color().setHSL(h / 360, s / 100, l / 100);
    };
    const theme = {
      background: cssVarColor('--background', [222, 47, 11]),
      card: cssVarColor('--card', [222, 47, 13]),
      primary: cssVarColor('--primary', [192, 88, 41]),
      accent: cssVarColor('--accent', [37, 58, 60]),
    };

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
      onStats({ webglReady: true, loadedModels: 0, failedModels: 0 });
    } catch {
      onStats({ webglReady: false, loadedModels: 0, failedModels: 0 });
      return;
    }
    renderer.setClearColor(theme.background, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(theme.card, 7, 15);

    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.set(0, 3.25, 7.2);
    camera.lookAt(0, 0.75, 0);

    const root = new THREE.Group();
    scene.add(root);
    let responsiveScale = 1;

    const ambient = new THREE.HemisphereLight(0xffffff, 0x263446, 2.2);
    scene.add(ambient);

    const key = new THREE.DirectionalLight(0xfff2d2, 3.2);
    key.position.set(-3, 5, 5);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    scene.add(key);

    const rim = new THREE.PointLight(theme.primary, 2.8, 8);
    rim.position.set(3.5, 2.2, 2.5);
    scene.add(rim);

    const stageGlow = new THREE.PointLight(theme.accent, 1.4, 6);
    stageGlow.position.set(-2.5, 1.2, 1.8);
    scene.add(stageGlow);

    const backdrop = new THREE.Mesh(
      new THREE.PlaneGeometry(9.5, 5.8),
      new THREE.MeshStandardMaterial({
        color: theme.card.clone().lerp(theme.primary, 0.06),
        roughness: 0.82,
        metalness: 0.02,
        transparent: true,
        opacity: 0.82,
      }),
    );
    backdrop.position.set(0, 1.85, -2.8);
    root.add(backdrop);

    const gridGroup = new THREE.Group();
    const gridMat = new THREE.LineBasicMaterial({ color: theme.primary, transparent: true, opacity: 0.16 });
    for (let i = -5; i <= 5; i += 1) {
      const vertical = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(i * 0.9, -0.6, -2.76),
        new THREE.Vector3(i * 0.9 + 0.55, 4.5, -2.76),
      ]);
      const horizontal = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-4.5, i * 0.45 + 1.5, -2.75),
        new THREE.Vector3(4.5, i * 0.45 + 1.5, -2.75),
      ]);
      gridGroup.add(new THREE.Line(vertical, gridMat));
      gridGroup.add(new THREE.Line(horizontal, gridMat));
    }
    root.add(gridGroup);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(9, 5.2),
      new THREE.MeshStandardMaterial({ color: theme.card.clone().lerp(theme.primary, 0.08), roughness: 0.72, metalness: 0.05 }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.72;
    floor.receiveShadow = true;
    root.add(floor);

    const belt = new THREE.Mesh(
      new THREE.BoxGeometry(6.6, 0.08, 0.42),
      new THREE.MeshStandardMaterial({ color: 0x89a0a7, roughness: 0.64, transparent: true, opacity: 0.36 }),
    );
    belt.position.set(0, -0.44, 0.68);
    belt.receiveShadow = true;
    root.add(belt);

    const railMat = new THREE.MeshStandardMaterial({ color: theme.primary, roughness: 0.35, metalness: 0.25, transparent: true, opacity: 0.5 });
    [-1, 1].forEach((side) => {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.12, 2.8), railMat);
      rail.position.set(side * 2.95, -0.34, 0.58);
      rail.rotation.y = side * 0.03;
      rail.receiveShadow = true;
      root.add(rail);
    });

    const beltMarks = new THREE.Group();
    const markMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.22 });
    for (let i = 0; i < 12; i += 1) {
      const mark = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.015, 0.035), markMat);
      mark.position.set(-3.1 + i * 0.58, -0.385, 0.68);
      beltMarks.add(mark);
    }
    root.add(beltMarks);

    const boxGroup = new THREE.Group();
    boxGroup.position.set(0, -0.05, 0);
    root.add(boxGroup);

    const boxMat = new THREE.MeshStandardMaterial({ color: 0xf5c976, roughness: 0.42, metalness: 0.05 });
    const boxSideMat = new THREE.MeshStandardMaterial({ color: 0xffe6b8, roughness: 0.48, metalness: 0.03 });
    const trimMat = new THREE.MeshStandardMaterial({ color: 0xd79f4d, roughness: 0.35, metalness: 0.08 });

    const base = new THREE.Mesh(new THREE.BoxGeometry(2.9, 1.05, 1.65), boxMat);
    base.position.y = 0.12;
    base.castShadow = true;
    base.receiveShadow = true;
    boxGroup.add(base);

    const baseEdges = new THREE.LineSegments(
      new THREE.EdgesGeometry(base.geometry),
      new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.34 }),
    );
    baseEdges.position.copy(base.position);
    boxGroup.add(baseEdges);

    const inner = new THREE.Mesh(new THREE.BoxGeometry(2.45, 0.64, 1.3), boxSideMat);
    inner.position.set(0, 0.24, -0.03);
    inner.castShadow = true;
    boxGroup.add(inner);

    const frontFrame = new THREE.Mesh(new THREE.BoxGeometry(2.58, 0.06, 0.07), trimMat);
    frontFrame.position.set(0, 0.6, 0.86);
    frontFrame.castShadow = true;
    boxGroup.add(frontFrame);

    const seal = new THREE.Mesh(
      new THREE.TorusGeometry(0.34, 0.018, 10, 32),
      new THREE.MeshStandardMaterial({ color: theme.primary, roughness: 0.2, metalness: 0.2, emissive: theme.primary, emissiveIntensity: 0.08 }),
    );
    seal.position.set(0, 0.63, 0.91);
    seal.rotation.x = Math.PI / 2;
    boxGroup.add(seal);

    const lidPivot = new THREE.Group();
    lidPivot.position.set(-1.18, 0.96, -0.72);
    boxGroup.add(lidPivot);
    const lid = new THREE.Mesh(new THREE.BoxGeometry(3, 0.18, 1.75), boxMat);
    lid.position.set(1.18, 0.05, 0.72);
    lid.castShadow = true;
    lid.receiveShadow = true;
    lidPivot.add(lid);

    const ribbon = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.2, 1.82), new THREE.MeshStandardMaterial({ color: 0xf6d25e, roughness: 0.35 }));
    ribbon.position.set(0, 0.22, 0);
    lid.add(ribbon);

    const foodTrayGroup = new THREE.Group();
    foodTrayGroup.position.set(0, 0.82, 0.08);
    foodTrayGroup.visible = false;
    boxGroup.add(foodTrayGroup);

    const trayBaseMat = new THREE.MeshStandardMaterial({ color: 0x121923, roughness: 0.38, metalness: 0.18 });
    const trayGoldMat = new THREE.MeshStandardMaterial({ color: 0xd6a45b, roughness: 0.32, metalness: 0.22 });
    const clearLidMat = new THREE.MeshPhysicalMaterial({
      color: 0xdff7ff,
      roughness: 0.05,
      metalness: 0,
      transparent: true,
      opacity: 0.28,
      transmission: 0.55,
      thickness: 0.12,
      clearcoat: 1,
      clearcoatRoughness: 0.08,
    });
    const halvaMat = new THREE.MeshStandardMaterial({ color: 0x8d4f2a, roughness: 0.48, metalness: 0.02 });
    const dateMat = new THREE.MeshStandardMaterial({ color: 0x4b2418, roughness: 0.42, metalness: 0.03 });
    const fingerMat = new THREE.MeshStandardMaterial({ color: 0xf2c56b, roughness: 0.36, metalness: 0.03 });
    const herbMat = new THREE.MeshStandardMaterial({ color: 0x4aa36a, roughness: 0.55 });

    const addRectTray = () => {
      const tray = new THREE.Mesh(new THREE.BoxGeometry(2.18, 0.12, 1.14), trayBaseMat);
      tray.position.y = -0.04;
      tray.castShadow = true;
      tray.receiveShadow = true;
      foodTrayGroup.add(tray);
      const rim = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(2.28, 0.16, 1.22)),
        new THREE.LineBasicMaterial({ color: 0xf2dca7, transparent: true, opacity: 0.72 }),
      );
      rim.position.y = 0.02;
      foodTrayGroup.add(rim);
      const lid = new THREE.Mesh(new THREE.BoxGeometry(2.28, 0.5, 1.22), clearLidMat);
      lid.position.y = 0.28;
      lid.castShadow = true;
      foodTrayGroup.add(lid);
      [-0.36, 0.36].forEach((x) => {
        const divider = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.08, 1.08), trayGoldMat);
        divider.position.set(x, 0.08, 0);
        foodTrayGroup.add(divider);
      });
    };

    const addRoundTray = () => {
      const tray = new THREE.Mesh(new THREE.CylinderGeometry(0.82, 0.9, 0.1, 64), trayBaseMat);
      tray.position.set(0, 0.04, 0);
      tray.castShadow = true;
      tray.receiveShadow = true;
      foodTrayGroup.add(tray);
      const rim = new THREE.Mesh(new THREE.TorusGeometry(0.86, 0.025, 10, 64), trayGoldMat);
      rim.position.y = 0.11;
      rim.rotation.x = Math.PI / 2;
      foodTrayGroup.add(rim);
      const dome = new THREE.Mesh(new THREE.SphereGeometry(0.86, 48, 18, 0, Math.PI * 2, 0, Math.PI / 2), clearLidMat);
      dome.position.y = 0.14;
      dome.scale.y = 0.42;
      dome.castShadow = true;
      foodTrayGroup.add(dome);
    };

    const addHalvaPieces = () => {
      for (let row = 0; row < 2; row += 1) {
        for (let col = 0; col < 4; col += 1) {
          const piece = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.09, 0.24), halvaMat);
          piece.position.set(-0.58 + col * 0.38, 0.14, -0.18 + row * 0.36);
          piece.rotation.y = (col - 1.5) * 0.08;
          piece.castShadow = true;
          foodTrayGroup.add(piece);
          const pistachio = new THREE.Mesh(new THREE.CapsuleGeometry(0.025, 0.09, 4, 8), herbMat);
          pistachio.position.set(piece.position.x, 0.205, piece.position.z);
          pistachio.rotation.z = Math.PI / 2;
          foodTrayGroup.add(pistachio);
        }
      }
      [-0.48, 0, 0.48].forEach((x) => {
        const date = new THREE.Mesh(new THREE.SphereGeometry(0.12, 18, 12), dateMat);
        date.position.set(x, 0.17, 0.42);
        date.scale.set(1.25, 0.68, 0.86);
        date.castShadow = true;
        foodTrayGroup.add(date);
      });
    };

    const addFingerFoodPieces = () => {
      for (let i = 0; i < 9; i += 1) {
        const x = -0.72 + (i % 3) * 0.72;
        const z = -0.34 + Math.floor(i / 3) * 0.34;
        const base = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.16, 0.11, 18), fingerMat);
        base.position.set(x, 0.15, z);
        base.castShadow = true;
        foodTrayGroup.add(base);
        const top = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.06, 0.18), new THREE.MeshStandardMaterial({ color: i % 2 ? 0xe86c53 : 0xf7f0d0, roughness: 0.4 }));
        top.position.set(x, 0.24, z);
        top.rotation.y = i * 0.35;
        top.castShadow = true;
        foodTrayGroup.add(top);
        const pick = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.28, 8), trayGoldMat);
        pick.position.set(x, 0.38, z);
        pick.castShadow = true;
        foodTrayGroup.add(pick);
      }
    };

    const choiceText = selectedChoices.map((choice) => `${choice.name} ${choice.description || ''} ${choice.group}`).join(' ').toLowerCase();
    const hasHalva = /حلوا|خرما|halva|date/.test(choiceText);
    const hasFingerFood = /فینگر|finger|ساندویچ|mini|snack|food/.test(choiceText);
    if (hasHalva || hasFingerFood) {
      if (hasHalva && !hasFingerFood) addRoundTray();
      else addRectTray();
      if (hasHalva) addHalvaPieces();
      if (hasFingerFood) addFingerFoodPieces();
      foodTrayGroup.visible = true;
    }

    const sidePods = new THREE.Group();
    const podMat = new THREE.MeshStandardMaterial({ color: theme.card.clone().lerp(theme.primary, 0.22), roughness: 0.55, metalness: 0.08, transparent: true, opacity: 0.74 });
    [-1, 1].forEach((side) => {
      const pod = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.55, 0.1, 32), podMat);
      pod.position.set(side * 2.25, -0.42, 0.1);
      pod.userData.baseY = pod.position.y;
      pod.castShadow = true;
      pod.receiveShadow = true;
      sidePods.add(pod);
      const halo = new THREE.Mesh(
        new THREE.TorusGeometry(0.56, 0.014, 8, 48),
        new THREE.MeshBasicMaterial({ color: theme.primary, transparent: true, opacity: 0.38 }),
      );
      halo.position.copy(pod.position);
      halo.rotation.x = Math.PI / 2;
      halo.userData.baseY = halo.position.y;
      sidePods.add(halo);
    });
    root.add(sidePods);

    const itemGroup = new THREE.Group();
    root.add(itemGroup);

    const palette: Record<Exclude<BaseStep, 'quantity'>, number> = {
      packaging: 0x5aa986,
      fruit: 0xef6f4d,
      drink: 0x0c9fc7,
      snack: 0xd6a45b,
      addons: 0x8f63d7,
    };

    const disposeObject = (object: THREE.Object3D) => {
      object.traverse((child) => {
        if ('geometry' in child && child.geometry) (child.geometry as THREE.BufferGeometry).dispose();
        if ('material' in child && child.material) {
          const materials = Array.isArray(child.material) ? child.material : [child.material];
          materials.forEach((material: THREE.Material) => {
            const materialWithMap = material as THREE.Material & { map?: THREE.Texture | null };
            materialWithMap.map?.dispose();
            material.dispose();
          });
        }
      });
    };
    const textureLoader = new THREE.TextureLoader();
    textureLoader.setCrossOrigin('anonymous');
    const gltfLoader = new GLTFLoader();
    let disposed = false;
    let loadedModels = 0;
    let failedModels = 0;

    const makeItemObject = (choice: BuilderChoice, index: number) => {
      const wrapper = new THREE.Group();
      const sideMaterial = new THREE.MeshStandardMaterial({
        color: palette[choice.group],
        roughness: 0.34,
        metalness: 0.08,
        emissive: palette[choice.group],
        emissiveIntensity: 0.04,
      });
      let proxy: THREE.Mesh;
      if (choice.image) {
        const texture = textureLoader.load(choice.image);
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
        const photoMaterial = new THREE.MeshStandardMaterial({ map: texture, color: 0xffffff, roughness: 0.58 });
        const materials = [sideMaterial, sideMaterial, sideMaterial, sideMaterial, photoMaterial, photoMaterial];
        proxy = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.6, 0.18), materials);
      } else {
        const geometry = choice.group === 'drink'
          ? new THREE.CapsuleGeometry(0.16, 0.38, 5, 12)
          : choice.group === 'fruit'
          ? new THREE.SphereGeometry(0.22, 24, 16)
          : new THREE.BoxGeometry(0.42, 0.3, 0.38);
        proxy = new THREE.Mesh(geometry, sideMaterial);
      }
      proxy.castShadow = true;
      proxy.receiveShadow = true;
      wrapper.add(proxy);
      wrapper.userData = {
        index,
        side: index % 2 === 0 ? -1 : 1,
        phase: (index * 0.61) % (Math.PI * 2),
      };
      wrapper.rotation.set(-0.35 + (index % 3) * 0.18, (index % 2 ? 1 : -1) * 0.55, 0);

      if (choice.model3dUrl) {
        gltfLoader.load(
          choice.model3dUrl,
          (gltf) => {
            if (disposed) {
              disposeObject(gltf.scene);
              return;
            }
            const model = gltf.scene;
            const bounds = new THREE.Box3().setFromObject(model);
            const size = bounds.getSize(new THREE.Vector3());
            const center = bounds.getCenter(new THREE.Vector3());
            const largestSide = Math.max(size.x, size.y, size.z, 0.001);
            model.position.sub(center);
            model.scale.setScalar(0.72 / largestSide);
            model.traverse((child) => {
              if (child instanceof THREE.Mesh) {
                child.castShadow = true;
                child.receiveShadow = true;
              }
            });
            wrapper.remove(proxy);
            disposeObject(proxy);
            wrapper.add(model);
            loadedModels += 1;
            onStats({ webglReady: true, loadedModels, failedModels });
          },
          undefined,
          () => {
            if (disposed) return;
            failedModels += 1;
            onStats({ webglReady: true, loadedModels, failedModels });
          },
        );
      }
      return wrapper;
    };

    const rebuildItems = () => {
      itemGroup.clear();
      selectedChoices.forEach((choice, index) => itemGroup.add(makeItemObject(choice, index)));
    };
    rebuildItems();

    const sparkGroup = new THREE.Group();
    root.add(sparkGroup);
    for (let i = 0; i < 18; i += 1) {
      const spark = new THREE.Mesh(
        new THREE.TetrahedronGeometry(0.055),
        new THREE.MeshBasicMaterial({ color: theme.accent, transparent: true, opacity: 0.55 }),
      );
      spark.userData = { phase: i * 0.7 };
      sparkGroup.add(spark);
    }

    const pointer = { x: 0, y: 0, active: false };
    const controls = {
      dragging: false,
      lastX: 0,
      lastY: 0,
      rotX: -0.04,
      rotY: 0,
      zoom: 1,
      targetZoom: 1,
    };
    const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
    const resetView = () => {
      controls.rotX = -0.04;
      controls.rotY = 0;
      controls.targetZoom = 1;
    };
    controlsRef.current = {
      rotateLeft: () => { controls.rotY -= 0.28; },
      rotateRight: () => { controls.rotY += 0.28; },
      zoomIn: () => { controls.targetZoom = clamp(controls.targetZoom + 0.12, 0.72, 1.45); },
      zoomOut: () => { controls.targetZoom = clamp(controls.targetZoom - 0.12, 0.72, 1.45); },
      reset: resetView,
    };
    const handlePointerDown = (event: PointerEvent) => {
      controls.dragging = true;
      controls.lastX = event.clientX;
      controls.lastY = event.clientY;
      pointer.active = true;
      canvas.setPointerCapture?.(event.pointerId);
    };
    const handlePointerMove = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
      pointer.y = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
      pointer.active = true;
      if (controls.dragging) {
        const dx = event.clientX - controls.lastX;
        const dy = event.clientY - controls.lastY;
        controls.lastX = event.clientX;
        controls.lastY = event.clientY;
        controls.rotY += dx * 0.006;
        controls.rotX = clamp(controls.rotX + dy * 0.004, -0.42, 0.32);
      }
    };
    const handlePointerUp = (event: PointerEvent) => {
      controls.dragging = false;
      canvas.releasePointerCapture?.(event.pointerId);
    };
    const handlePointerLeave = () => {
      pointer.active = false;
      controls.dragging = false;
    };
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      controls.targetZoom = clamp(controls.targetZoom - event.deltaY * 0.0012, 0.72, 1.45);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      const rotationStep = event.shiftKey ? 0.18 : 0.1;
      if (event.key === 'ArrowLeft') controls.rotY -= rotationStep;
      else if (event.key === 'ArrowRight') controls.rotY += rotationStep;
      else if (event.key === 'ArrowUp') controls.rotX = clamp(controls.rotX - rotationStep, -0.42, 0.32);
      else if (event.key === 'ArrowDown') controls.rotX = clamp(controls.rotX + rotationStep, -0.42, 0.32);
      else if (event.key === '+' || event.key === '=') controls.targetZoom = clamp(controls.targetZoom + 0.1, 0.72, 1.45);
      else if (event.key === '-' || event.key === '_') controls.targetZoom = clamp(controls.targetZoom - 0.1, 0.72, 1.45);
      else if (event.key === '0' || event.key === 'Home') resetView();
      else return;
      event.preventDefault();
    };
    canvas.addEventListener('pointerdown', handlePointerDown, { passive: true });
    canvas.addEventListener('pointermove', handlePointerMove, { passive: true });
    canvas.addEventListener('pointerup', handlePointerUp, { passive: true });
    canvas.addEventListener('pointercancel', handlePointerUp, { passive: true });
    canvas.addEventListener('pointerleave', handlePointerLeave);
    canvas.addEventListener('wheel', handleWheel, { passive: false });
    canvas.addEventListener('keydown', handleKeyDown);

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const width = Math.max(240, Math.floor(rect.width));
      const height = Math.max(220, Math.floor(rect.height));
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.position.z = width < 420 ? 8.1 : width < 700 ? 7.7 : 7.2;
      camera.position.x = 0;
      camera.lookAt(camera.position.x, 0.75, 0);
      responsiveScale = width < 420 ? 0.78 : width < 700 ? 0.9 : 1;
      root.scale.setScalar(responsiveScale * controls.zoom);
      root.position.x = 0;
      camera.updateProjectionMatrix();
    };

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();

    let raf = 0;
    let last = performance.now();
    let elapsed = prefersReducedMotion ? 1000 : 0;
    const isComplete = currentStep === 'quantity';
    const draw = (time: number) => {
      const delta = Math.min(42, time - last);
      last = time;
      if (!document.hidden && !prefersReducedMotion) elapsed += delta;
      const t = elapsed / 1000;
      const width = canvas.width / Math.min(window.devicePixelRatio || 1, 1.75);
      const compact = width < 700;

      const open = isComplete ? Math.max(0, 1 - Math.min(1, elapsed / 850)) : Math.min(1, elapsed / 700);
      lidPivot.rotation.x = -1.05 * open;
      lidPivot.rotation.z = -0.12 * open;
      boxGroup.position.x = width < 420 ? 0 : compact ? 0.42 : 0;
      boxGroup.position.y = -0.05 + Math.sin(t * 2.1) * 0.025;
      controls.zoom += (controls.targetZoom - controls.zoom) * 0.12;
      root.scale.setScalar(responsiveScale * controls.zoom);
      const idleY = controls.dragging ? 0 : Math.sin(t * 0.35) * 0.04;
      root.rotation.y += (controls.rotY + idleY - root.rotation.y) * 0.06;
      root.rotation.x += (controls.rotX - root.rotation.x) * 0.06;

      itemGroup.children.forEach((child) => {
        const item = child as THREE.Object3D;
        const index = item.userData.index as number;
        const side = item.userData.side as number;
        const phase = item.userData.phase as number;
        const arrival = Math.min(1, Math.max(0, (elapsed - index * 90) / 650));
        const arc = Math.sin(arrival * Math.PI);
        const startX = side * (compact ? 1.44 : 2.18) + Math.sin(t * 1.4 + phase) * 0.14;
        const startY = 0.8 + (index % 4) * 0.28 + Math.cos(t * 1.2 + phase) * 0.08;
        const startZ = -0.08 + (index % 3) * 0.34;
        const itemCount = itemGroup.children.length;
        const columns = Math.min(5, Math.max(1, Math.ceil(Math.sqrt(itemCount * 1.5))));
        const rows = Math.max(1, Math.ceil(itemCount / columns));
        const column = index % columns;
        const row = Math.floor(index / columns);
        const targetX = columns === 1 ? 0 : -0.82 + (column / (columns - 1)) * 1.64;
        const targetY = 0.72 + Math.floor(row / 4) * 0.18;
        const targetZ = rows === 1 ? 0.18 : -0.34 + ((row % 4) / Math.min(rows - 1, 3)) * 0.68;
        item.position.set(
          startX + (targetX - startX) * arrival,
          startY + (targetY - startY) * arrival + arc * 0.72,
          startZ + (targetZ - startZ) * arrival,
        );
        item.rotation.x += (-0.08 - item.rotation.x) * 0.09;
        item.rotation.y += (0 - item.rotation.y) * 0.09;
        const settledScale = itemCount > 20 ? 0.48 : itemCount > 12 ? 0.58 : itemCount > 6 ? 0.72 : 0.96;
        item.scale.setScalar(settledScale + arc * 0.2);
      });

      sparkGroup.visible = isComplete;
      sparkGroup.children.forEach((child, index) => {
        const spark = child as THREE.Mesh;
        const phase = spark.userData.phase as number;
        spark.position.set(
          Math.cos(t * 1.5 + phase) * (1.65 + (index % 3) * 0.12),
          0.75 + Math.sin(t * 2.2 + phase) * 0.7,
          Math.sin(t * 1.7 + phase) * 1.05,
        );
        spark.rotation.x += 0.05;
        spark.rotation.y += 0.04;
      });

      belt.position.x = (t * 0.08) % 0.2;
      beltMarks.position.x = -((t * 0.55) % 0.58);
      seal.rotation.z += 0.012;
      sidePods.children.forEach((child, index) => {
        child.position.y = (child.userData.baseY as number) + Math.sin(t * 2.1 + index) * 0.018;
      });
      stageGlow.intensity = 1.05 + Math.sin(t * 2.4) * 0.35;
      renderer.render(scene, camera);
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);

    return () => {
      disposed = true;
      controlsRef.current = null;
      cancelAnimationFrame(raf);
      observer.disconnect();
      canvas.removeEventListener('pointerdown', handlePointerDown);
      canvas.removeEventListener('pointermove', handlePointerMove);
      canvas.removeEventListener('pointerup', handlePointerUp);
      canvas.removeEventListener('pointercancel', handlePointerUp);
      canvas.removeEventListener('pointerleave', handlePointerLeave);
      canvas.removeEventListener('wheel', handleWheel);
      canvas.removeEventListener('keydown', handleKeyDown);
      disposeObject(scene);
      renderer.dispose();
    };
  }, [canvasRef, controlsRef, currentStep, onStats, quantity, selectedChoices, totalPrice]);
}

function BuilderAnimation({
  currentStep,
  selectedChoices,
  totalPrice,
  quantity,
}: {
  currentStep: BaseStep;
  selectedChoices: BuilderChoice[];
  totalPrice: number;
  quantity: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const controlsRef = useRef<BuilderSceneControls | null>(null);
  const [sceneStats, setSceneStats] = useState<BuilderSceneStats>({
    webglReady: true,
    loadedModels: 0,
    failedModels: 0,
  });
  useBuilderScene3D({
    canvasRef,
    currentStep,
    selectedChoices,
    totalPrice,
    quantity,
    controlsRef,
    onStats: setSceneStats,
  });
  const progress = Math.round(((stepOrder.indexOf(currentStep) + 1) / stepOrder.length) * 100);
  const previewChoices = selectedChoices.slice(-4);
  const readyModelCount = selectedChoices.filter((choice) => choice.model3dUrl).length;
  const runControl = (command: keyof BuilderSceneControls) => {
    controlsRef.current?.[command]();
    canvasRef.current?.focus();
  };

  return (
    <section
      className="min-w-0 max-w-full overflow-hidden rounded-xl border border-border/70 bg-card shadow-soft"
      aria-label="پیش‌نمایش سه‌بعدی ساخت پک"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 px-3 py-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><Box className="h-4 w-4" /></span>
          <div className="min-w-0">
            <h2 className="text-sm font-black text-foreground">پیش‌نمایش سه‌بعدی پک</h2>
            <p className="truncate text-[10px] font-bold text-muted-foreground">
              {readyModelCount
                ? `${sceneStats.loadedModels.toLocaleString('fa-IR')} مدل واقعی بارگذاری شد؛ بقیه پیش‌نمایش عکس‌محورند`
                : 'پیش‌نمایش تقریبی چیدمان؛ ابعاد نهایی پس از بررسی سفارش'}
            </p>
          </div>
        </div>
        <span className="rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 text-[10px] font-black text-primary">
          {selectedChoices.length.toLocaleString('fa-IR')} آیتم
        </span>
      </div>

      <div className="relative bg-muted/20">
        <div className="pointer-events-none absolute inset-x-3 top-3 z-10">
        <div className="h-1.5 overflow-hidden rounded-full bg-muted/70">
          <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${progress}%` }} />
        </div>
        </div>
        <canvas
          ref={canvasRef}
          className="block h-[280px] w-full cursor-grab touch-none outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring active:cursor-grabbing sm:h-[360px] lg:h-[440px]"
          aria-label={`پیش‌نمایش زنده ساخت پک با ${selectedChoices.length.toLocaleString('fa-IR')} آیتم`}
          aria-describedby="builder-3d-help"
          tabIndex={0}
        />
        {!sceneStats.webglReady && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/90 p-6 text-center text-xs leading-6 text-muted-foreground">
            مرورگر شما WebGL را اجرا نکرد؛ انتخاب محصولات و ثبت سفارش همچنان فعال است.
          </div>
        )}
        {sceneStats.failedModels > 0 && (
          <span className="absolute bottom-3 right-3 rounded-full bg-warning/15 px-2.5 py-1 text-[10px] font-bold text-warning">
            {sceneStats.failedModels.toLocaleString('fa-IR')} مدل با نمای عکس جایگزین شد
          </span>
        )}
      </div>

      <div className="border-t border-border/70 p-3 sm:p-4">
        <div className="mb-3 grid grid-cols-5 gap-2" aria-label="کنترل نمای سه‌بعدی">
          <Button type="button" variant="outline" size="sm" onClick={() => runControl('rotateRight')} aria-label="چرخش به راست" title="چرخش به راست"><ArrowRight className="h-4 w-4" /></Button>
          <Button type="button" variant="outline" size="sm" onClick={() => runControl('rotateLeft')} aria-label="چرخش به چپ" title="چرخش به چپ"><ArrowLeft className="h-4 w-4" /></Button>
          <Button type="button" variant="outline" size="sm" onClick={() => runControl('zoomIn')} aria-label="بزرگ‌نمایی" title="بزرگ‌نمایی"><Plus className="h-4 w-4" /></Button>
          <Button type="button" variant="outline" size="sm" onClick={() => runControl('zoomOut')} aria-label="کوچک‌نمایی" title="کوچک‌نمایی"><Minus className="h-4 w-4" /></Button>
          <Button type="button" variant="outline" size="sm" onClick={() => runControl('reset')} aria-label="بازنشانی نما" title="بازنشانی نما"><RotateCcw className="h-4 w-4" /></Button>
        </div>

        <div className="rounded-lg bg-primary/5 p-3">
          <div className="mb-1 flex items-center justify-between gap-2">
            <span className="text-xs font-black text-primary">{stepLabels[currentStep]}</span>
            <span className="truncate text-[10px] font-bold text-muted-foreground">{stepHints[currentStep]}</span>
          </div>
          <p className="text-[11px] leading-5 text-foreground sm:text-xs sm:leading-6">{stepStories[currentStep]}</p>
        </div>

        <div className="mt-3 flex min-w-0 items-center gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" aria-live="polite">
          {previewChoices.length ? previewChoices.map((choice) => (
            <span key={choice.id} className="max-w-[8rem] shrink-0 truncate rounded-full bg-muted px-2.5 py-1 text-[10px] font-bold text-muted-foreground">
              {choice.name}
            </span>
          )) : <span className="text-[11px] font-bold text-muted-foreground">از مرحله اول، آیتم دلخواه را انتخاب کن.</span>}
        </div>

        <details className="mt-3 rounded-lg border border-border/70 bg-background px-3 py-2" id="builder-3d-help">
          <summary className="flex cursor-pointer list-none items-center gap-2 text-xs font-black text-foreground">
            <HelpCircle className="h-4 w-4 text-primary" /> راهنمای استفاده از نمای سه‌بعدی
          </summary>
          <ol className="mt-2 space-y-1 pr-5 text-[11px] leading-6 text-muted-foreground">
            <li>۱. هر محصولی را انتخاب کنی همان لحظه به صحنه اضافه می‌شود.</li>
            <li>۲. روی تصویر بکش یا دکمه‌های جهت را بزن تا پک بچرخد.</li>
            <li>۳. با + و − زوم کن؛ دکمه بازنشانی، نمای اول را برمی‌گرداند.</li>
            <li>۴. مدل‌های آماده با GLB واقعی دیده می‌شوند؛ بقیه تا زمان پردازش ML با عکس حجمی نمایش داده می‌شوند.</li>
            <li>۵. این تصویر راهنمای چیدمان است؛ تعداد و قیمت ثبت‌شده در خلاصه سفارش معیار نهایی‌اند.</li>
          </ol>
        </details>
      </div>
    </section>
  );
}

function ChoiceCard({
  choice,
  selected,
  onToggle,
  multi,
}: {
  choice: BuilderChoice;
  selected: boolean;
  onToggle: () => void;
  multi?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={selected}
      className={cn(
        'group relative flex min-h-[9rem] flex-col overflow-hidden rounded-xl border bg-card text-right transition-all duration-200 touch-manipulation focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        selected ? 'border-primary bg-primary/5 shadow-soft -translate-y-0.5' : 'border-border hover:-translate-y-0.5 hover:border-primary/45 hover:shadow-soft',
      )}
    >
      <div className="relative aspect-square w-full overflow-hidden bg-muted">
        {choice.image ? (
          <img src={choice.image} alt={choice.name} className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-[radial-gradient(circle,hsl(var(--primary)/0.16),hsl(var(--muted)))] text-3xl text-muted-foreground">
            <Package className="h-8 w-8" />
          </div>
        )}
        <div className="absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-background/85 to-transparent" />
        <span className="absolute right-2 top-2 rounded-full bg-background/90 px-2 py-1 text-[10px] font-bold text-foreground shadow-sm backdrop-blur">
          {choice.source === 'product' ? 'محصول' : 'آیتم'}
        </span>
        <span className={cn(
          'absolute left-2 top-2 flex h-7 w-7 items-center justify-center border-2 bg-background/90 shadow-sm backdrop-blur transition-colors',
          multi ? 'rounded-md' : 'rounded-full',
          selected ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-muted-foreground',
        )}>
          {selected && <Check className="h-3.5 w-3.5" />}
        </span>
        {selected && <span className="absolute inset-x-0 bottom-0 h-1 bg-primary" />}
      </div>
      <div className="flex flex-1 flex-col justify-between gap-2 p-3">
        <div>
          <p className="line-clamp-2 text-sm font-bold leading-6 text-foreground">{choice.name}</p>
          {choice.description && <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">{choice.description}</p>}
        </div>
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="rounded-full bg-muted px-2 py-1 text-[10px] font-bold text-muted-foreground">{stepLabels[choice.group]}</span>
        </div>
        <p className="text-xs font-black text-primary">
          {choice.price.toLocaleString('fa-IR')} تومان
        </p>
      </div>
    </button>
  );
}

export default function BuilderPage() {
  const navigate = useNavigate();
  const { addItem, minQuantityRequired } = useCart();
  const [builderItems, setBuilderItems] = useState<BuilderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState<BaseStep>('packaging');
  const [selections, setSelections] = useState<Selections>({
    packaging: [],
    fruit: [],
    drink: [],
    snack: [],
    addons: [],
  });
  const [quantity, setQuantity] = useState(minQuantityRequired);

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;
    if (!webApp) return;
    webApp.ready?.();
    webApp.expand?.();
    const styles = getComputedStyle(document.documentElement);
    const background = `hsl(${styles.getPropertyValue('--background').trim() || '222 47% 11%'})`;
    webApp.setBackgroundColor?.(background);
    webApp.setHeaderColor?.(background);
  }, []);

  useEffect(() => {
    const alignRtlViewport = () => {
      const root = document.documentElement;
      const overflow = root.scrollWidth - root.clientWidth;
      if (overflow > 1) {
        window.scrollTo({ left: -overflow, top: window.scrollY });
      }
    };

    const frame = window.requestAnimationFrame(alignRtlViewport);
    window.addEventListener('resize', alignRtlViewport);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener('resize', alignRtlViewport);
    };
  }, []);

  useEffect(() => {
    setQuantity((prev) => (prev < minQuantityRequired ? minQuantityRequired : prev));
  }, [minQuantityRequired]);

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      try {
        const itemsResult = await getBuilderConfig();
        if (!mounted) return;
        setBuilderItems(itemsResult);
      } catch {
        if (mounted) setBuilderItems([]);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  const choices = useMemo(() => {
    const itemChoices = builderItems.map(toChoice);
    const seen = new Set<string>();
    return itemChoices.filter((choice) => {
      const key = `${choice.group}:${choice.source}:${choice.productId || choice.id}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).sort((left, right) => left.name.localeCompare(right.name, 'fa'));
  }, [builderItems]);

  const choicesById = useMemo(() => new Map(choices.map((choice) => [choice.id, choice])), [choices]);
  const groupedChoices = useMemo(() => ({
    packaging: choices.filter((choice) => choice.group === 'packaging'),
    fruit: choices.filter((choice) => choice.group === 'fruit'),
    drink: choices.filter((choice) => choice.group === 'drink'),
    snack: choices.filter((choice) => choice.group === 'snack'),
    addons: choices.filter((choice) => choice.group === 'addons'),
  }), [choices]);

  const currentStepIndex = stepOrder.indexOf(currentStep);
  const selectedChoices = useMemo(() => {
    const ids = choiceSteps.flatMap((step) => selections[step]);
    return ids.map((id) => choicesById.get(id)).filter(Boolean) as BuilderChoice[];
  }, [choicesById, selections]);

  const canProceed = currentStep === 'quantity' ? quantity >= minQuantityRequired : true;

  const totalPrice = useMemo(
    () => selectedChoices.reduce((sum, choice) => sum + choice.price, 0),
    [selectedChoices],
  );

  const getChoiceName = (id: string) => {
    return choicesById.get(id)?.name || '-';
  };

  const handleMultiToggle = (step: ChoiceStep, id: string) => {
    triggerHaptic('impact');
    setSelections((prev) => ({
      ...prev,
      [step]: prev[step].includes(id)
        ? prev[step].filter((selectedId) => selectedId !== id)
        : [...prev[step], id],
    }));
  };

  const goNext = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < stepOrder.length) setCurrentStep(stepOrder[nextIndex]);
  };

  const goPrev = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) setCurrentStep(stepOrder[prevIndex]);
  };

  const resetBuilder = () => {
    triggerHaptic('impact');
    setSelections({ packaging: [], fruit: [], drink: [], snack: [], addons: [] });
    setQuantity(minQuantityRequired);
    setCurrentStep('packaging');
  };

  const handleAddToCart = () => {
    addItem({
      productId: `custom-${Date.now()}`,
      name: 'پک اختصاصی مجلس‌یار',
      quantity,
      price: totalPrice,
      isCustomPack: true,
      customConfig: {
        packaging: selections.packaging.map((id) => getChoiceName(id)),
        fruit: selections.fruit.map((id) => getChoiceName(id)),
        drink: selections.drink.map((id) => getChoiceName(id)),
        snack: selections.snack.map((id) => getChoiceName(id)),
        addons: selections.addons.map((id) => getChoiceName(id)),
      },
    });

    triggerHaptic('success');
    notifySuccess('پک اختصاصی به سبد خرید اضافه شد');
    navigate('/cart');
  };

  const renderEmptyState = (message: string) => (
    <div className="flex min-h-[180px] flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/30 p-6 text-center">
      <Package className="mb-3 h-9 w-9 text-muted-foreground" />
      <p className="text-sm font-semibold text-foreground">{message}</p>
      <p className="mt-1 text-xs text-muted-foreground">از پنل مدیریت محصول یا آیتم سازنده اضافه کنید.</p>
    </div>
  );

  const renderChoiceGrid = (step: ChoiceStep) => {
    const baseChoices = groupedChoices[step];
    const currentChoices = baseChoices;

    if (!baseChoices.length) {
      return renderEmptyState('افزودنی‌ای ثبت نشده است.');
    }

    return (
      <div className="min-w-0 space-y-4">
        {currentChoices.length ? (
          <div className="grid w-full min-w-0 max-w-full grid-cols-1 gap-3 min-[430px]:grid-cols-2 min-[1180px]:grid-cols-3">
            {currentChoices.map((choice) => (
              <ChoiceCard
                key={choice.id}
                choice={choice}
                selected={selections[step].includes(choice.id)}
                onToggle={() => handleMultiToggle(step, choice.id)}
                multi
              />
            ))}
          </div>
        ) : (
          renderEmptyState('در این دسته محصولی برای نمایش نیست.')
        )}
      </div>
    );
  };

  const renderStepContent = () => {
    if (currentStep === 'quantity') {
      return (
        <div className="space-y-5">
          <div className="flex flex-col gap-4 rounded-lg border border-border bg-muted/30 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-lg font-bold text-foreground">تعداد پک</h3>
              <p className="mt-1 text-sm text-muted-foreground">حداقل سفارش فعلی از تنظیمات سایت خوانده می‌شود.</p>
            </div>
            <div className="flex items-center gap-3">
              <input
                aria-label="تعداد پک"
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value, 10) || 1))}
                className="h-14 w-28 rounded-lg border-2 border-input bg-background text-center text-2xl font-black focus:outline-none focus:ring-2 focus:ring-ring"
                min={1}
              />
              <span className="text-sm text-muted-foreground">عدد</span>
            </div>
          </div>
          {quantity < minQuantityRequired && (
            <RuleAlert
              type="warning"
              message={`حداقل تعداد سفارش ${minQuantityRequired} عدد است.`}
            />
          )}
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">قیمت هر پک</p>
              <p className="mt-1 text-xl font-black text-primary">{totalPrice.toLocaleString('fa-IR')} تومان</p>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">تعداد آیتم انتخابی</p>
              <p className="mt-1 text-xl font-black text-foreground">{selectedChoices.length.toLocaleString('fa-IR')}</p>
            </div>
            <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
              <p className="text-xs text-muted-foreground">جمع کل</p>
              <p className="mt-1 text-xl font-black text-primary">{(totalPrice * quantity).toLocaleString('fa-IR')} تومان</p>
            </div>
          </div>
        </div>
      );
    }

    return renderChoiceGrid(currentStep);
  };

  if (loading) {
    return (
      <AppShell>
        <div className="container py-10">
          <div className="flex min-h-[340px] items-center justify-center rounded-xl border border-border bg-card">
            <div className="flex items-center gap-3 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>در حال آماده‌سازی سازنده پک...</span>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <SEO
        pageKey="builder"
        path="/builder"
        breadcrumbs={[
          { name: 'خانه', url: '/' },
          { name: 'ساخت پک اختصاصی', url: '/builder' },
        ]}
      />
      <div className="mx-auto w-full max-w-[1400px] overflow-x-clip px-3 pt-5 pb-36 sm:px-4 sm:pt-8 lg:pb-8">
        <div className="mb-5 flex min-w-0 flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <div className="mb-3 inline-flex max-w-full items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-[11px] font-bold text-primary sm:text-xs">
              <Sparkles className="h-3.5 w-3.5" />
              سازنده پویا با داده‌های بک‌اند
            </div>
            <h1 className="text-xl font-black leading-9 text-foreground sm:text-2xl md:text-3xl">ساخت پک اختصاصی</h1>
            <p className="mt-2 max-w-2xl text-xs leading-7 text-muted-foreground sm:text-sm">
              بسته‌بندی، میوه، نوشیدنی، خوراکی و افزودنی‌های دلخواه را به پک اضافه کنید.
            </p>
          </div>
          <Button variant="outline" onClick={resetBuilder} className="w-full gap-2 sm:w-auto">
            <RotateCcw className="h-4 w-4" />
            شروع دوباره
          </Button>
        </div>

        <div className="mb-4 grid gap-2 rounded-xl border border-primary/15 bg-primary/5 p-3 sm:grid-cols-3 sm:p-4" aria-label="راهنمای سریع ساخت پک">
          {[
            ['۱', 'مرحله را انتخاب کن', 'از بسته‌بندی شروع کن و با «بعدی» جلو برو.'],
            ['۲', 'هر تعداد خواستی بردار', 'با لمس کارت، آیتم فوراً به پک و نمای سه‌بعدی اضافه می‌شود.'],
            ['۳', 'قیمت را همان لحظه ببین', 'در مرحله آخر تعداد را بزن و پک را به سبد خرید بفرست.'],
          ].map(([number, title, description]) => (
            <div key={number} className="flex items-start gap-2 rounded-lg bg-background/75 p-2.5">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-[10px] font-black text-primary-foreground">{number}</span>
              <div>
                <p className="text-xs font-black text-foreground">{title}</p>
                <p className="mt-0.5 text-[10px] leading-5 text-muted-foreground">{description}</p>
              </div>
            </div>
          ))}
        </div>

        <div
          className={cn(
            'grid w-full min-w-0 max-w-full gap-4 lg:items-start',
            BUILDER_3D_PREVIEW_ENABLED
              ? 'lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]'
              : 'lg:grid-cols-1',
          )}
        >
          <section className="relative w-full min-w-0 max-w-full lg:col-span-2">
            <div className="w-full min-w-0 max-w-full space-y-3 lg:sticky lg:top-24">
              <div className="flex max-w-full gap-2 overflow-x-auto rounded-xl border border-border/70 bg-card/70 p-2 shadow-soft backdrop-blur [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {stepOrder.map((step, index) => (
                  <button
                    type="button"
                    key={step}
                    onClick={() => {
                      if (index <= currentStepIndex || canProceed) setCurrentStep(step);
                    }}
                    aria-current={step === currentStep ? 'step' : undefined}
                    className={cn(
                      'group flex min-h-10 min-w-fit items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-black transition-all touch-manipulation',
                      step === currentStep
                        ? 'bg-primary text-primary-foreground shadow-soft'
                        : index < currentStepIndex
                        ? 'bg-success/10 text-success'
                        : 'bg-muted/70 text-muted-foreground hover:text-foreground',
                    )}
                  >
                    <span className={cn(
                      'flex h-5 w-5 items-center justify-center rounded-full text-[10px]',
                      step === currentStep ? 'bg-primary-foreground/20' : 'bg-background/70',
                    )}>
                      {index < currentStepIndex ? <Check className="h-3 w-3" /> : index + 1}
                    </span>
                    {stepLabels[step]}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {BUILDER_3D_PREVIEW_ENABLED ? (
            <div className="min-w-0 lg:sticky lg:top-24">
              <BuilderAnimation
                currentStep={currentStep}
                selectedChoices={selectedChoices}
                totalPrice={totalPrice}
                quantity={quantity}
              />
            </div>
          ) : null}

          <section className="w-full min-w-0 max-w-full rounded-xl border border-border bg-card p-3 shadow-soft sm:p-5 lg:min-h-[70vh] lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-lg font-black text-foreground">{stepLabels[currentStep]}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    گزینه‌ها از آیتم‌های سازنده پک خوانده می‌شوند.
                  </p>
                </div>
                <span className="rounded-full bg-muted px-3 py-1 text-xs font-bold text-muted-foreground">
                  {currentStepIndex + 1} / {stepOrder.length}
                </span>
              </div>
              <div className="mb-4 rounded-xl border border-primary/15 bg-primary/5 p-3">
                <p className="text-xs font-black text-primary">{stepHints[currentStep]}</p>
                <p className="mt-1 text-xs leading-6 text-muted-foreground">{stepStories[currentStep]}</p>
              </div>
              {renderStepContent()}

              <div className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-2 items-center gap-2 border-t border-border bg-card/95 px-3 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] shadow-[0_-8px_20px_hsl(var(--background)/0.25)] backdrop-blur sm:flex sm:justify-between sm:gap-3 sm:px-5 sm:py-4 lg:sticky lg:inset-x-auto lg:z-20 lg:-mx-5 lg:mt-6">
              <Button
                variant="outline"
                onClick={goPrev}
                disabled={currentStepIndex === 0}
                className="min-h-[42px] min-w-0 gap-1 px-3 text-xs sm:min-h-[44px] sm:gap-2 sm:text-sm"
              >
                <ArrowRight className="h-4 w-4" />
                قبلی
              </Button>

              <div className="order-first col-span-2 min-w-0 text-center sm:order-none sm:col-span-1">
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">جمع زنده</p>
                <p className="truncate text-sm font-black text-primary sm:text-lg">{(totalPrice * quantity).toLocaleString('fa-IR')} تومان</p>
              </div>

              {currentStep === 'quantity' ? (
                <Button
                  variant="gold"
                  size="lg"
                  onClick={handleAddToCart}
                  disabled={totalPrice <= 0 || quantity < minQuantityRequired}
                  className="min-h-[44px] min-w-0 gap-1 px-3 text-xs sm:min-h-[48px] sm:flex-none sm:gap-2 sm:text-sm"
                >
                  <ShoppingCart className="h-5 w-5" />
                  افزودن به سبد
                </Button>
              ) : (
                <Button
                  variant="default"
                  onClick={goNext}
                  disabled={!canProceed}
                  className="min-h-[42px] min-w-0 gap-1 px-3 text-xs sm:min-h-[44px] sm:gap-2 sm:text-sm"
                >
                  بعدی
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              )}
              </div>
          </section>

          <aside className="hidden">
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="mb-4 flex items-center gap-2">
                <Package className="h-5 w-5 text-primary" />
                <h2 className="font-black text-foreground">خلاصه پک</h2>
              </div>

              <div className="space-y-3">
                {choiceSteps.map((step) => (
                  <div key={step} className="border-b border-border pb-2">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{stepLabels[step]}</span>
                      <span className="text-xs font-bold text-primary">{selections[step].length.toLocaleString('fa-IR')} انتخاب</span>
                    </div>
                    {selections[step].length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {selections[step].slice(0, 6).map((id) => (
                          <span key={id} className="rounded-full bg-muted px-2 py-1 text-[11px] text-muted-foreground">
                            {getChoiceName(id)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="mt-5 space-y-2 rounded-lg bg-muted/40 p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">هر پک</span>
                  <span className="font-black text-primary">{totalPrice.toLocaleString('fa-IR')} تومان</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">تعداد</span>
                  <span className="font-black text-foreground">{quantity.toLocaleString('fa-IR')}</span>
                </div>
                <div className="flex items-center justify-between border-t border-border pt-2">
                  <span className="font-bold text-foreground">جمع</span>
                  <span className="font-black text-primary">{(totalPrice * quantity).toLocaleString('fa-IR')} تومان</span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </AppShell>
  );
}
