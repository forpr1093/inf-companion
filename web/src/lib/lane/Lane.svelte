<script lang="ts">
  import { onMount } from "svelte";
  import { Application, Container, Graphics, Sprite, TilingSprite } from "pixi.js";
  import { settings, skinMissing, subscribeKeys, subscribeReset } from "../stores";
  import type { KeyEvent, Lane, Settings } from "../events";
  import { laneLayout, SKIN_W, type LaneGeom } from "./layout";
  import { NoteField } from "./notes";
  import { frameGeometry, loadSkin, skinUrls, spriteKind, type SkinTextures } from "./skin";

  const debug = new URLSearchParams(location.search).has("debug");
  const BEAM_FADE_MS = 200;

  let host: HTMLDivElement;
  let latency = $state<{ mean: number; p95: number } | null>(null);

  onMount(() => {
    const field = new NoteField();
    const app = new Application();
    // Layers, back to front.
    const bg = new Graphics();
    const skinBack = new Container();
    const beams = new Container();
    const fx = new Graphics();
    const notesG = new Graphics();
    const noteSprites = new Container();
    const flashSprites = new Container();
    const keysG = new Graphics();

    let lanes: LaneGeom[] = [];
    let judgeY = 0;
    let width = 0;
    let height = 0;
    let colors = readColors();
    let s: Settings | null = null;
    let skin: SkinTextures | null = null;
    let skinKey = "";
    let geo: ReturnType<typeof frameGeometry> | null = null;
    let label: Sprite | null = null;
    let scratchDir = 0; // +1 up, -1 down, 0 idle
    let lastFrame = performance.now();
    let destroyed = false;
    const released = new Map<Lane, number>(); // lane -> release time, for beam fade
    const beamByLane = new Map<Lane, Sprite>();
    const flashByLane = new Map<Lane, Sprite>();
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
      if (!s) return;
      skinBack.removeChildren();
      beams.removeChildren();
      flashSprites.removeChildren();
      beamByLane.clear();
      flashByLane.clear();
      label = null;
      bg.clear();
      if (skin) {
        geo = frameGeometry(s.side, width);
        const inner = laneLayout(s.side, geo.laneW, height);
        lanes = inner.lanes.map(l => ({ ...l, x: l.x + geo!.laneX }));
        judgeY = geo.judgeY;
        const frame = new Sprite(skin.frame);
        frame.width = width; frame.height = width * (1080 / 685);
        skinBack.addChild(frame);
        if (skin.lane) {
          const strip = new TilingSprite({ texture: skin.lane, width: geo.laneW, height: judgeY });
          strip.x = geo.laneX;
          strip.tileScale.set(geo.laneW / skin.lane.width, geo.scale);
          skinBack.addChild(strip);
        }
        for (const l of lanes) {
          const k = spriteKind(l.lane);
          const beam = new Sprite(skin.beam[k]);
          beam.x = l.x; beam.width = l.w; beam.height = 723 * geo.scale; beam.y = judgeY - beam.height;
          beam.alpha = 0;
          beams.addChild(beam);
          beamByLane.set(l.lane, beam);
          if (k !== "s" && skin.flash) {
            const f = geo.flash[k];
            const fl = new Sprite(skin.flash[k]);
            fl.x = l.x + f.dx; fl.y = f.top; fl.width = f.w; fl.height = f.h;
            fl.blendMode = "add"; fl.alpha = 0;
            flashSprites.addChild(fl);
            flashByLane.set(l.lane, fl);
          }
        }
        if (skin.label) {
          label = new Sprite(skin.label);
          label.anchor.set(0.5);
          label.width = label.height = geo.label.size;
          label.x = geo.label.x + geo.label.size / 2;
          label.y = geo.label.y + geo.label.size / 2;
          flashSprites.addChild(label);
        }
      } else {
        geo = null;
        ({ lanes, judgeY } = laneLayout(s.side, width, height));
        bg.rect(0, 0, width, height).fill({ color: colors.bg });
        for (const l of lanes) bg.rect(l.x, 0, l.w, judgeY).fill({ color: colors.panel });
        bg.rect(0, judgeY - 2, width, 4).fill({ color: colors.scratch });
      }
    }

    async function refreshSkin(next: Settings) {
      const urls = skinUrls(next);
      const key = JSON.stringify([urls, next.side]);
      if (key === skinKey) return;
      skinKey = key;
      const result = await loadSkin(urls, next.side);
      if (destroyed || key !== skinKey) return;
      skin = result.textures;
      skinMissing.set(result.missing);
      relayout();
    }

    function render() {
      if (destroyed || !s) return;
      const now = performance.now();
      const dt = now - lastFrame;
      lastFrame = now;
      const k = skin && geo ? geo.scale : width / SKIN_W.total;
      const minH = 19 * k;
      const byLane = new Map<Lane, LaneGeom>(lanes.map(l => [l.lane, l]));
      const views = field.frame(now);

      // Notes.
      notesG.clear();
      let used = 0;
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

      // Beams, flashes, key highlights.
      fx.clear();
      keysG.clear();
      const flashes = new Map(field.flashes(now).map(f => [f.lane, f.alpha]));
      for (const l of lanes) {
        const held = field.isHeld(l.lane);
        if (skin) {
          const beam = beamByLane.get(l.lane);
          if (beam) {
            const rel = released.get(l.lane);
            beam.alpha = held ? 1 : rel === undefined ? 0 : Math.max(0, 1 - (now - rel) / BEAM_FADE_MS);
          }
          const fl = flashByLane.get(l.lane);
          if (fl) fl.alpha = held ? 1 : (flashes.get(l.lane) ?? 0);
        } else {
          const fa = flashes.get(l.lane);
          if (fa) fx.rect(l.x, judgeY * 0.55, l.w, judgeY * 0.45).fill({ color: colors.accent, alpha: 0.35 * fa });
          keysG.rect(l.x, judgeY + 6, l.w, height - judgeY - 6).fill({ color: colors[l.color], alpha: held ? 1 : 0.28 });
        }
      }
      if (label && !reduced.matches) label.rotation += scratchDir * (Math.PI * 2) * (dt / 1000);
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
    let ready = false;
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
        app.stage.addChild(bg, skinBack, beams, fx, notesG, noteSprites, flashSprites, keysG);
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
