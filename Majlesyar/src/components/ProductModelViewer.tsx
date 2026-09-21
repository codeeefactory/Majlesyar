import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Box, Loader2, Rotate3D } from 'lucide-react';

interface ProductModelViewerProps {
  modelUrl: string;
  productName: string;
}

export function ProductModelViewer({ modelUrl, productName }: ProductModelViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'failed'>('loading');

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    setState('loading');
    let disposed = false;
    let animationFrame = 0;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    } catch {
      setState('failed');
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 100);
    camera.position.set(0, 1.1, 3.4);

    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.autoRotate = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    controls.autoRotateSpeed = 0.75;
    controls.enablePan = false;
    controls.minDistance = 1.6;
    controls.maxDistance = 6;
    controls.target.set(0, 0.15, 0);

    scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 2.4));
    const keyLight = new THREE.DirectionalLight(0xffffff, 3.2);
    keyLight.position.set(3, 4, 5);
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0x8ddcf1, 1.4);
    fillLight.position.set(-4, 2, -3);
    scene.add(fillLight);

    const platform = new THREE.Mesh(
      new THREE.CylinderGeometry(1.25, 1.35, 0.08, 64),
      new THREE.MeshStandardMaterial({ color: 0xe8e2d8, roughness: 0.88, metalness: 0.02 }),
    );
    platform.position.y = -0.77;
    scene.add(platform);

    const resize = () => {
      const { width, height } = container.getBoundingClientRect();
      if (!width || !height) return;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    resize();

    const loader = new GLTFLoader();
    loader.load(
      modelUrl,
      (gltf) => {
        if (disposed) {
          gltf.scene.traverse((object) => {
            if (object instanceof THREE.Mesh) object.geometry?.dispose();
          });
          return;
        }
        const model = gltf.scene;
        const bounds = new THREE.Box3().setFromObject(model);
        const size = bounds.getSize(new THREE.Vector3());
        const center = bounds.getCenter(new THREE.Vector3());
        const largestSide = Math.max(size.x, size.y, size.z, 0.001);
        const scale = 1.85 / largestSide;
        model.scale.setScalar(scale);
        model.position.set(-center.x * scale, -bounds.min.y * scale - 0.72, -center.z * scale);
        model.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = false;
            child.receiveShadow = false;
          }
        });
        scene.add(model);
        setState('ready');
      },
      undefined,
      () => {
        if (!disposed) setState('failed');
      },
    );

    const render = () => {
      controls.update();
      renderer.render(scene, camera);
      animationFrame = window.requestAnimationFrame(render);
    };
    render();

    const stopAutoRotate = () => {
      controls.autoRotate = false;
    };
    canvas.addEventListener('pointerdown', stopAutoRotate, { once: true });
    canvas.addEventListener('wheel', stopAutoRotate, { once: true, passive: true });

    return () => {
      disposed = true;
      window.cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      controls.dispose();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry?.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => {
            for (const value of Object.values(material)) {
              if (value instanceof THREE.Texture) value.dispose();
            }
            material.dispose();
          });
        }
      });
      renderer.dispose();
    };
  }, [modelUrl]);

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden bg-[radial-gradient(circle_at_50%_35%,hsl(var(--primary)/0.14),transparent_65%)]">
      <canvas
        ref={canvasRef}
        className="h-full w-full touch-none cursor-grab active:cursor-grabbing"
        aria-label={`مدل سه‌بعدی ${productName}. برای چرخاندن بکشید و برای زوم اسکرول کنید.`}
      />
      {state === 'loading' && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-3 bg-background/55 backdrop-blur-sm">
          <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
          <span className="text-sm font-bold text-foreground">در حال بارگذاری مدل سه‌بعدی…</span>
        </div>
      )}
      {state === 'failed' && (
        <div role="alert" className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-muted px-6 text-center">
          <Box className="h-14 w-14 text-muted-foreground/55" aria-hidden="true" />
          <p className="text-sm font-bold text-foreground">مدل سه‌بعدی بارگذاری نشد؛ عکس محصول همچنان در دسترس است.</p>
        </div>
      )}
      {state === 'ready' && (
        <div className="pointer-events-none absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full bg-card/90 px-3 py-1.5 text-[11px] font-bold text-muted-foreground shadow-soft backdrop-blur">
          <Rotate3D className="h-4 w-4 text-primary" aria-hidden="true" />
          بکشید برای چرخش · اسکرول برای زوم
        </div>
      )}
    </div>
  );
}
