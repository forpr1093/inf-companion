<script lang="ts">
  import { onMount } from "svelte";
  import { Application, Container, Graphics, Sprite } from "pixi.js";
  import { settings, skinMissing, subscribeKeys, subscribeReset } from "../stores";
  import type { KeyEvent, Lane, Settings } from "../events";
  import { laneLayout, SKIN_W, type LaneGeom } from "./layout";
  import { NoteField } from "./notes";
  import { loadSkin, NOTE_H, skinUrls, spriteKind, type SkinTextures } from "./skin";

  const debug = new URLSearchParams(location.search).has("debug");
  const BEAM_FADE_MS = 200;
  const JUDGE = 0.8; // judge line at 80% of the height
  const BEAM_BANDS = 14;

  let host: HTMLDivElement;
  let latency = $state<{ mean: number; p95: number } | null>(null);

  onMount(() => {
    const field = new NoteField();
    const app = new Application();
    const bg = new Graphics(); // lanes, dividers, judge line: redrawn on resize/theme
    const beamsG = new Graphics();
    const notesG = new Graphics();
    const noteSprites = new Container();
    const capsG = new Graphics();
    const disc = new Container();
    const discG = new Graphics();
    disc.addChild(discG);

    let lanes: LaneGeom[] = [];
    let judgeY = 0;
    let width = 0;
    let height = 0;
    let colors = readColors();
    let s: Settings | null = null;
    let skin: SkinTextures | null = null;
    let skinKey = "";
    let scratchDir = 0;
    let lastFrame = performance.now();
    let destroyed = false;
    let ready = false;
    const released = new Map<Lane, number>();
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const samples: number[] = [];

    function readColors() {
      const cs = getComputedStyle(document.documentElement);
      const v = (n: string) => cs.getPropertyValue(n).trim() || "#888";
      return {
        white: v("--key-white"), black: v("--key-black"), scratch: v("--key-scratch"),
        laneBg: v("--lane-bg"), laneLine: v("--lane-line"), lineStrong: v("--line-strong"),
        accent: v("--accent"), bg: v("--bg"),
      };
    }

    function relayout() {
      width = host.clientWidth;
      height = host.clientHeight;
      if (!s || !width || !height) return;
      ({ lanes } = laneLayout(s.side, width, height));
      judgeY = Math.round(height * JUDGE);
      bg.clear();
      bg.rect(0, 0, width, height).fill({ color: colors.laneBg });
      for (const l of lanes.slice(1)) bg.rect(Math.round(l.x - 2), 0, 1, judgeY).fill({ color: colors.laneLine });
      bg.rect(0, judgeY, width, height - judgeY).fill({ color: colors.bg });
      bg.rect(0, judgeY - 2, width, 4).fill({ color: colors.scratch });

      const sl = lanes.find(l => l.lane === "S")!;
      const d = sl.w * 0.9;
      const r = d / 2;
      disc.x = sl.x + sl.w / 2;
      disc.y = judgeY + 10 + r;
      discG.clear();
      discG.circle(0, 0, r).fill({ color: colors.laneBg }).stroke({ color: colors.lineStrong, width: Math.max(2, r * 0.12) });
      discG.circle(0, 0, r * 0.18).fill({ color: colors.lineStrong });
      discG.rect(-1.5, -r * 0.92, 3, r * 0.6).fill({ color: colors.white });
    }

    async function refreshSkin(next: Settings) {
      const urls = skinUrls(next);
      const key = urls.notes;
      if (key === skinKey) return;
      skinKey = key;
      const result = await loadSkin(urls);
      if (destroyed || key !== skinKey) return;
      skin = result.textures;
      skinMissing.set(result.missing);
    }

    function render() {
      if (destroyed || !s || !width) return;
      const now = performance.now();
      const dt = now - lastFrame;
      lastFrame = now;
      const k = width / SKIN_W.total;
      const minH = NOTE_H * k;
      const byLane = new Map<Lane, LaneGeom>(lanes.map(l => [l.lane, l]));

      // Beams: lit while held, fade after release. Banded vertical gradient.
      beamsG.clear();
      const beamH = judgeY * 0.45;
      for (const l of lanes) {
        const held = field.isHeld(l.lane);
        const rel = released.get(l.lane);
        const a = held ? 1 : rel === undefined ? 0 : Math.max(0, 1 - (now - rel) / BEAM_FADE_MS);
        if (a <= 0) continue;
        const bandH = beamH / BEAM_BANDS;
        for (let i = 0; i < BEAM_BANDS; i++) {
          const y = judgeY - (i + 1) * bandH;
          beamsG.rect(l.x, y, l.w, bandH + 0.5).fill({ color: colors.accent, alpha: 0.45 * a * (1 - i / BEAM_BANDS) });
        }
      }

      // Notes.
      notesG.clear();
      let used = 0;
      const views = field.frame(now);
      if (!reduced.matches) {
        for (const n of views) {
          const l = byLane.get(n.lane);
          if (!l) continue;
          const yBottom = judgeY - n.bottom * judgeY;
          const yTop = Math.min(judgeY - n.top * judgeY, yBottom - minH);
          if (skin) {
            let sp = noteSprites.children[used] as Sprite | undefined;
            if (!sp) { sp = new Sprite(); noteSprites.addChild(sp); }
            sp.texture = skin.note[spriteKind(n.lane)];
            sp.visible = true;
            sp.x = l.x; sp.y = yTop; sp.width = l.w; sp.height = yBottom - yTop; sp.alpha = n.alpha;
            used++;
          } else {
            notesG.rect(l.x, yTop, l.w, yBottom - yTop).fill({ color: colors[l.color], alpha: n.alpha });
          }
        }
      }
      for (let i = used; i < noteSprites.children.length; i++) noteSprites.children[i].visible = false;

      // Key caps under the judge line; the scratch lane has the disc instead.
      capsG.clear();
      const capTop = judgeY + 10;
      const capH = height - capTop - 8;
      for (const l of lanes) {
        if (l.lane === "S") continue;
        const held = field.isHeld(l.lane);
        const top = l.color === "black" ? capTop + capH * 0.12 : capTop;
        const inset = l.w * 0.08;
        capsG.roundRect(l.x + inset, top, l.w - inset * 2, Math.max(4, capH * 0.62), 4)
          .fill({ color: l.color === "black" ? colors.black : colors.white, alpha: held ? 1 : 0.28 });
      }
      if (!reduced.matches) disc.rotation += scratchDir * Math.PI * 2 * (dt / 1000);
      disc.alpha = field.isHeld("S") ? 1 : 0.85;
    }

    function onKey(e: KeyEvent) {
      const t = performance.now();
      if (e.type === "key_down") {
        field.press(e.lane, t);
        released.delete(e.lane);
        if (e.lane === "S") scratchDir = e.dir === "down" ? -1 : 1;
      } else {
        field.release(e.lane, t);
        released.set(e.lane, t);
        if (e.lane === "S") scratchDir = 0;
      }
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
    const unsubReset = subscribeReset(() => { field.releaseAll(performance.now()); scratchDir = 0; });
    const unsubSettings = settings.subscribe(next => {
      s = next;
      queueMicrotask(() => {
        colors = readColors();
        if (ready) { relayout(); refreshSkin(next); }
      });
    });
    const ro = new ResizeObserver(() => { if (ready) { app.renderer.resize(host.clientWidth, host.clientHeight); relayout(); } });

    app.init({ resizeTo: host, antialias: true, backgroundAlpha: 0, autoDensity: true, resolution: window.devicePixelRatio || 1 })
      .then(() => {
        if (destroyed) { app.destroy(true); return; }
        host.appendChild(app.canvas);
        app.stage.addChild(bg, beamsG, notesG, noteSprites, capsG, disc);
        ready = true;
        relayout();
        if (s) refreshSkin(s);
        ro.observe(host);
        app.ticker.add(render);
      });

    return () => {
      destroyed = true;
      unsubKeys(); unsubReset(); unsubSettings(); ro.disconnect();
      if (ready) app.destroy(true, { children: true });
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
