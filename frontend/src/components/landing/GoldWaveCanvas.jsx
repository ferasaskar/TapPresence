import { useEffect, useRef } from "react";

/* Cinematic "gold signal" — layered flowing particle ribbons on a transparent
   canvas. GPU-light (pre-rendered sprite + additive blend), pauses when
   offscreen, scales particle count on mobile, and honours prefers-reduced-motion. */

const TAU = Math.PI * 2;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

const GOLD = { r: 240, g: 205, b: 132 };
const GOLD_DEEP = { r: 200, g: 150, b: 70 };
const BLUE = { r: 90, g: 150, b: 255 };

function makeSprite(color) {
  const s = 32;
  const c = document.createElement("canvas");
  c.width = c.height = s;
  const g = c.getContext("2d");
  const grd = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
  grd.addColorStop(0, `rgba(${color.r},${color.g},${color.b},1)`);
  grd.addColorStop(0.35, `rgba(${color.r},${color.g},${color.b},0.55)`);
  grd.addColorStop(1, `rgba(${color.r},${color.g},${color.b},0)`);
  g.fillStyle = grd;
  g.fillRect(0, 0, s, s);
  return c;
}

const CONFIGS = {
  cta: {
    scrollReactive: true,
    layers: [
      { baseY: 0.66, amp: 0.14, freq: 1.0, speed: 0.0038, slope: 0, color: GOLD_DEEP, count: 150, size: 2.6, opacity: 0.5, depth: 10 },
      { baseY: 0.73, amp: 0.11, freq: 1.35, speed: 0.006, slope: 0, color: GOLD, count: 230, size: 2.1, opacity: 0.92, depth: 18 },
      { baseY: 0.81, amp: 0.08, freq: 1.75, speed: 0.009, slope: 0, color: GOLD, count: 180, size: 1.6, opacity: 0.7, depth: 26 },
    ],
    travelers: { count: 34, color: GOLD, size: 2.3, speed: 0.02, layer: 1 },
  },
  hero: {
    scrollReactive: false,
    layers: [
      { baseY: 0.52, amp: 0.10, freq: 0.9, speed: 0.0034, slope: -0.16, color: GOLD, count: 120, size: 2.0, opacity: 0.42, depth: 22, mix: true },
      { baseY: 0.60, amp: 0.07, freq: 1.3, speed: 0.0052, slope: -0.12, color: GOLD_DEEP, count: 90, size: 1.6, opacity: 0.3, depth: 30, mix: true },
    ],
    travelers: { count: 14, color: GOLD, size: 2.0, speed: 0.017, layer: 0 },
  },
};

export default function GoldWaveCanvas({ variant = "cta", className = "", style }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    const cfg = CONFIGS[variant] || CONFIGS.cta;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    const hover = window.matchMedia("(hover: hover) and (pointer: fine)").matches && !isMobile;
    const dpr = Math.min(window.devicePixelRatio || 1, isMobile ? 1.5 : 2);
    const countScale = isMobile ? 0.5 : 1;

    const spriteGold = makeSprite(GOLD);
    const spriteDeep = makeSprite(GOLD_DEEP);
    const spriteBlue = makeSprite(BLUE);
    const spriteFor = (layer, x) => {
      if (layer.mix) return x < 0.42 ? spriteBlue : spriteGold;
      return layer.color === GOLD_DEEP ? spriteDeep : spriteGold;
    };

    let W = 0, H = 0;
    const layers = cfg.layers.map((l) => ({
      ...l,
      particles: Array.from({ length: Math.max(6, Math.round(l.count * countScale)) }, () => ({
        x: Math.random(), b: Math.random() * TAU, r: l.size * (0.7 + Math.random() * 0.6),
      })),
    }));
    const trav = Array.from({ length: Math.max(4, Math.round(cfg.travelers.count * countScale)) }, () => ({
      x: Math.random(), r: cfg.travelers.size * (0.8 + Math.random() * 0.5),
    }));

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      W = Math.max(1, rect.width); H = Math.max(1, rect.height);
      canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    // pointer (desktop only)
    const pointer = { tx: 0, ty: 0, x: 0, y: 0 };
    const onMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      pointer.tx = clamp(((e.clientX - rect.left) / rect.width - 0.5) * 2, -1, 1);
      pointer.ty = clamp(((e.clientY - rect.top) / rect.height - 0.5) * 2, -1, 1);
    };
    if (hover) window.addEventListener("mousemove", onMove, { passive: true });

    // scroll factor (cta)
    let scrollF = 0;
    const onScroll = () => {
      const rect = canvas.getBoundingClientRect();
      const vh = window.innerHeight || 1;
      scrollF = clamp((vh / 2 - (rect.top + rect.height / 2)) / vh, -1, 1);
    };
    if (cfg.scrollReactive) { window.addEventListener("scroll", onScroll, { passive: true }); onScroll(); }

    const drawFrame = (time) => {
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      pointer.x += (pointer.tx - pointer.x) * 0.05;
      pointer.y += (pointer.ty - pointer.y) * 0.05;
      const scrollPhase = cfg.scrollReactive ? scrollF * 0.25 : 0;

      for (const layer of layers) {
        const sp = spriteFor(layer, 0.5);
        for (const p of layer.particles) {
          const px = p.x * W + pointer.x * layer.depth;
          const angle = (p.x * layer.freq + time * (layer.speed * 60) + scrollPhase) * TAU + p.b;
          const py = layer.baseY * H + layer.slope * (p.x * W) + Math.sin(angle) * layer.amp * H + pointer.y * layer.depth * 0.4;
          const brightness = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(angle));
          const size = p.r * (0.85 + 0.4 * brightness);
          ctx.globalAlpha = layer.opacity * brightness;
          const spr = layer.mix ? spriteFor(layer, p.x) : sp;
          ctx.drawImage(spr, px - size, py - size, size * 2, size * 2);
        }
      }
      // travelers — brighter fast dots riding a ribbon
      const tl = layers[cfg.travelers.layer] || layers[0];
      for (const t of trav) {
        const px = t.x * W + pointer.x * tl.depth;
        const angle = (t.x * tl.freq + time * (tl.speed * 60) + scrollPhase) * TAU;
        const py = tl.baseY * H + tl.slope * (t.x * W) + Math.sin(angle) * tl.amp * H + pointer.y * tl.depth * 0.4;
        ctx.globalAlpha = 0.9;
        const spr = tl.mix ? spriteFor(tl, t.x) : spriteGold;
        ctx.drawImage(spr, px - t.r, py - t.r, t.r * 2, t.r * 2);
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
    };

    const advance = (dt) => {
      for (const layer of layers)
        for (const p of layer.particles) { p.x += layer.speed * dt; if (p.x > 1) p.x -= 1; }
      const tl = layers[cfg.travelers.layer] || layers[0];
      for (const t of trav) { t.x += cfg.travelers.speed * dt; if (t.x > 1) t.x -= 1; }
    };

    if (reduce) { drawFrame(0); return () => { ro.disconnect(); }; }

    let raf = 0, last = performance.now(), t = 0, visible = true;
    const io = new IntersectionObserver((es) => { visible = es[0].isIntersecting; if (visible && !raf) loop(performance.now()); },
      { threshold: 0 });
    io.observe(canvas);

    const loop = (now) => {
      const dt = Math.min(2, (now - last) / 16.67);
      last = now; t += dt / 60;
      advance(dt); drawFrame(t);
      if (visible) raf = requestAnimationFrame(loop); else raf = 0;
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf); ro.disconnect(); io.disconnect();
      if (hover) window.removeEventListener("mousemove", onMove);
      if (cfg.scrollReactive) window.removeEventListener("scroll", onScroll);
    };
  }, [variant]);

  return <canvas ref={canvasRef} className={className} style={style} aria-hidden data-testid={`gold-wave-${variant}`} />;
}
