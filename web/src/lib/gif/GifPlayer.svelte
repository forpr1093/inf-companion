<script lang="ts">
  import { onMount } from "svelte";
  import { decompressFrame, parseGIF } from "gifuct-js";
  import { gifVersion, hasGif, nowPlaying, settings } from "../stores";
  import { fitContain, frameAt, gifPlan, loopRate, normaliseDelays, phaseKeepingStart } from "./rate";

  type GifFrame = Parameters<typeof decompressFrame>[0];

  let host: HTMLDivElement;
  let canvas: HTMLCanvasElement;
  let error = $state<string | null>(null);

  // Speed follows the song's BPM once known, the manual BPM until then.
  const bpm = $derived($nowPlaying?.bpm ?? $settings.manual_bpm);
  const beats = $derived($settings.beats_per_loop);

  let frames: HTMLCanvasElement[] = [];
  let delays: number[] = [];
  let loopMs = 0;
  let gifW = 0;
  let gifH = 0;
  let start = performance.now();
  let rate = 1;
  let loadedVersion = -1;
  let raf = 0;

  /**
   * Decode and composite the GIF once (honouring disposal), storing each frame shrunk to
   * the budget from gifPlan. Frames are decoded one by one with pauses, so the lane keeps
   * running while a big GIF loads. A newer upload supersedes a load still in progress.
   */
  async function load(version: number) {
    loadedVersion = version;
    error = null;
    const stale = () => version !== loadedVersion;
    try {
      const r = await fetch(`/api/gif?v=${version}`, { cache: "no-store" });
      if (stale()) return;
      if (!r.ok) { frames = []; return; }
      const gif = parseGIF(await r.arrayBuffer());
      if (stale()) return;
      const raw = gif.frames.filter((f): f is GifFrame => "image" in f);
      if (raw.length === 0) throw new Error("The GIF has no frames.");
      const w = gif.lsd.width, h = gif.lsd.height;
      const plan = gifPlan(raw.length, w, h);
      if (!plan.ok) { frames = []; error = plan.reason; return; }
      const sw = Math.max(1, Math.round(w * plan.scale)), sh = Math.max(1, Math.round(h * plan.scale));
      const full = document.createElement("canvas");
      full.width = w; full.height = h;
      const ctx = full.getContext("2d")!;
      const patch = document.createElement("canvas");
      const pctx = patch.getContext("2d")!;
      const out: HTMLCanvasElement[] = [];
      const outDelays: number[] = [];
      for (let i = 0; i < raw.length; i++) {
        const f = decompressFrame(raw[i], gif.gct, true);
        const before = f.disposalType === 3 ? ctx.getImageData(0, 0, w, h) : null;
        patch.width = f.dims.width; patch.height = f.dims.height;
        pctx.putImageData(new ImageData(new Uint8ClampedArray(f.patch), f.dims.width, f.dims.height), 0, 0);
        ctx.drawImage(patch, f.dims.left, f.dims.top);
        const snap = document.createElement("canvas");
        snap.width = sw; snap.height = sh;
        snap.getContext("2d")!.drawImage(full, 0, 0, sw, sh);
        out.push(snap);
        outDelays.push(f.delay);
        if (f.disposalType === 2) ctx.clearRect(f.dims.left, f.dims.top, f.dims.width, f.dims.height);
        else if (before) ctx.putImageData(before, 0, 0);
        if (i % 8 === 7) {
          await new Promise(res => setTimeout(res, 0));
          if (stale()) return;
        }
      }
      frames = out;
      gifW = sw; gifH = sh;
      delays = normaliseDelays(outDelays);
      loopMs = delays.reduce((a, b) => a + b, 0);
      start = performance.now();
      rate = loopRate(bpm, beats, loopMs);
    } catch (e) {
      if (stale()) return;
      frames = [];
      error = (e as Error).message || "Couldn't read the GIF.";
    }
  }

  // Keep the loop phase when the BPM or beats change, so the speed changes without a jump.
  $effect(() => {
    const next = loopMs ? loopRate(bpm, beats, loopMs) : 1;
    if (loopMs && next !== rate) {
      const now = performance.now();
      start = phaseKeepingStart(now, start, rate, next, loopMs);
      rate = next;
    }
  });

  $effect(() => {
    if ($hasGif && $gifVersion !== loadedVersion) load($gifVersion);
  });

  onMount(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const draw = () => {
      raf = requestAnimationFrame(draw);
      const dpr = window.devicePixelRatio || 1;
      const cw = host.clientWidth, ch = host.clientHeight;
      if (canvas.width !== Math.round(cw * dpr) || canvas.height !== Math.round(ch * dpr)) {
        canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
      }
      const ctx = canvas.getContext("2d")!;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (frames.length === 0) return;
      const i = reduced.matches ? 0 : frameAt(performance.now() - start, delays, rate);
      const box = fitContain(gifW, gifH, canvas.width, canvas.height);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(frames[i], box.x, box.y, box.w, box.h);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  });
</script>

<div class="gif" bind:this={host}>
  <canvas bind:this={canvas}></canvas>
  {#if !$hasGif}
    <p class="empty">Upload a GIF in <a href="#/settings">settings</a></p>
  {:else if error}
    <p class="empty">{error}</p>
  {/if}
</div>

<style>
  .gif { position: relative; width: 100%; height: 100%; overflow: hidden; }
  canvas { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
  .empty {
    position: absolute; inset: 0; margin: 0; display: grid; place-items: center; text-align: center;
    padding: 12px; color: var(--muted); border: 1px dashed var(--line); font-size: 0.95rem;
  }
  .empty a { color: var(--accent); }
</style>
