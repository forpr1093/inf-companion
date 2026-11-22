<script lang="ts">
  import { onMount } from "svelte";
  import { Application, Graphics } from "pixi.js";
  import { settings, subscribeKeys, subscribeReset } from "../stores";
  import type { KeyEvent, Lane } from "../events";
  import { laneLayout, SKIN_W, type LaneGeom } from "./layout";
  import { NoteField } from "./notes";

  const debug = new URLSearchParams(location.search).has("debug");

  let host: HTMLDivElement;
  let latency = $state<{ mean: number; p95: number } | null>(null);

  onMount(() => {
    const field = new NoteField();
    const app = new Application();
    const bg = new Graphics();
    const notesG = new Graphics();
    const fx = new Graphics();
    const keysG = new Graphics();
    let lanes: LaneGeom[] = [];
    let judgeY = 0;
    let width = 0;
    let height = 0;
    let colors = readColors();
    let side: "1P" | "2P" = "1P";
    let destroyed = false;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const samples: number[] = [];

    function readColors() {
      const cs = getComputedStyle(document.documentElement);
      const v = (n: string) => cs.getPropertyValue(n).trim() || "#888";
      return {
        white: v("--key-white"), black: v("--key-black"), scratch: v("--key-scratch"),
        panel: v("--panel"), line: v("--line"), accent: v("--accent"), bg: v("--bg"),
      };
    }

    function relayout() {
      width = host.clientWidth;
      height = host.clientHeight;
      ({ lanes, judgeY } = laneLayout(side, width, height));
      drawBackground();
    }

    function drawBackground() {
      bg.clear();
      bg.rect(0, 0, width, height).fill({ color: colors.bg });
      for (const l of lanes) bg.rect(l.x, 0, l.w, judgeY).fill({ color: colors.panel });
      bg.rect(0, judgeY - 2, width, 4).fill({ color: colors.scratch });
    }

    function colorFor(l: LaneGeom) { return colors[l.color]; }

    function render() {
      if (destroyed) return;
      const now = performance.now();
      const k = width / SKIN_W.total;
      const minH = 19 * k;
      const travel = judgeY;
      const byLane = new Map<Lane, LaneGeom>(lanes.map(l => [l.lane, l]));

      notesG.clear();
      if (!reduced.matches) {
        for (const n of field.frame(now)) {
          const l = byLane.get(n.lane);
          if (!l) continue;
          const yBottom = judgeY - n.bottom * travel;
          const yTop = Math.min(judgeY - n.top * travel, yBottom - minH);
          notesG.rect(l.x, yTop, l.w, yBottom - yTop).fill({ color: colorFor(l), alpha: n.alpha });
        }
      } else {
        field.frame(now);
      }

      fx.clear();
      for (const f of field.flashes(now)) {
        const l = byLane.get(f.lane);
        if (!l) continue;
        fx.rect(l.x, judgeY * 0.55, l.w, judgeY * 0.45).fill({ color: colors.accent, alpha: 0.35 * f.alpha });
      }

      keysG.clear();
      for (const l of lanes) {
        const held = field.isHeld(l.lane);
        keysG.rect(l.x, judgeY + 6, l.w, height - judgeY - 6).fill({ color: colorFor(l), alpha: held ? 1 : 0.28 });
      }
    }

    function onKey(e: KeyEvent) {
      const t = performance.now();
      if (e.type === "key_down") field.press(e.lane, t);
      else field.release(e.lane, t);
      if (debug && e.type === "key_down") {
        samples.push(performance.timeOrigin + performance.now() - e.at);
        if (samples.length > 50) samples.shift();
        const sorted = [...samples].sort((a, b) => a - b);
        latency = {
          mean: samples.reduce((a, b) => a + b, 0) / samples.length,
          p95: sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))],
        };
      }
    }

    const unsubKeys = subscribeKeys(onKey);
    const unsubReset = subscribeReset(() => field.releaseAll(performance.now()));
    const unsubSettings = settings.subscribe(s => {
      side = s.side;
      queueMicrotask(() => { colors = readColors(); if (width) relayout(); });
    });
    const ro = new ResizeObserver(() => { if (app.renderer) { app.renderer.resize(host.clientWidth, host.clientHeight); relayout(); } });

    app.init({ resizeTo: host, antialias: true, backgroundAlpha: 0, autoDensity: true, resolution: window.devicePixelRatio || 1 })
      .then(() => {
        if (destroyed) { app.destroy(true); return; }
        host.appendChild(app.canvas);
        app.stage.addChild(bg, fx, notesG, keysG);
        relayout();
        ro.observe(host);
        app.ticker.add(render);
      });

    return () => {
      destroyed = true;
      unsubKeys(); unsubReset(); unsubSettings(); ro.disconnect();
      if (app.renderer) app.destroy(true, { children: true });
    };
  });
</script>

<div class="lane" bind:this={host}>
  {#if debug && latency}
    <p class="latency">key → note: {latency.mean.toFixed(1)} ms mean, {latency.p95.toFixed(1)} ms p95</p>
  {/if}
</div>

<style>
  .lane { position: relative; width: 100%; height: 100%; overflow: hidden; }
  .lane :global(canvas) { display: block; }
  .latency {
    position: absolute; left: 8px; top: 8px; margin: 0;
    padding: 4px 8px; background: var(--panel); color: var(--text);
    font-size: 0.85rem; border: 1px solid var(--line);
  }
</style>
