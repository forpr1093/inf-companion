<script lang="ts">
  import { onMount } from "svelte";
  import { emitKey, settings, status } from "../lib/stores";
  import { devKeyboard, startDemo } from "../lib/demo";
  import Lane from "../lib/lane/Lane.svelte";
  import Counter from "../lib/counter/Counter.svelte";

  const params = new URLSearchParams(location.search);
  const demo = params.has("demo");
  const dev = params.has("dev");

  let portraitMedia = $state(false);
  const orientation = $derived(
    $settings.orientation === "auto" ? (portraitMedia ? "portrait" : "landscape") : $settings.orientation,
  );

  onMount(() => {
    const mq = window.matchMedia("(orientation: portrait)");
    portraitMedia = mq.matches;
    const onChange = () => (portraitMedia = mq.matches);
    mq.addEventListener("change", onChange);
    const stops: (() => void)[] = [() => mq.removeEventListener("change", onChange)];
    if (demo) stops.push(startDemo(emitKey, { seed: 3, bpm: $settings.manual_bpm }));
    if (dev) stops.push(devKeyboard(emitKey));
    return () => stops.forEach(s => s());
  });
</script>

<div class="display {orientation}" class:p2={$settings.side === "2P"}>
  <section class="lane-area" aria-label="Key lane">
    <Lane />
  </section>

  <section class="gif-area" aria-label="Loop">
    <div class="placeholder">gif</div>
  </section>

  <section class="counter-area" aria-label="Button counter">
    <Counter />
  </section>

  <aside class="cards">
    <div class="panel now"><div class="inner">
      <p class="kicker">Now playing</p>
      <p class="title">No song yet</p>
      <p class="meta"><span class="bpm">{$settings.manual_bpm}</span> BPM <span class="muted">(manual)</span></p>
    </div></div>
    <div class="panel result"><div class="inner">
      <p class="kicker">Last result</p>
      <p class="empty">Results show here after a song.</p>
    </div></div>
  </aside>

  <span class="conn" data-status={$status} title="Server connection: {$status}" aria-label="Server connection: {$status}"></span>
</div>

<style>
  .display {
    height: 100vh;
    display: grid;
    gap: 20px;
    padding: 20px;
    position: relative;
  }
  .landscape {
    grid-template-columns: auto minmax(0, 1fr) minmax(300px, 26rem);
    grid-template-rows: minmax(0, 1fr) auto;
    grid-template-areas: "lane gif cards" "lane counter cards";
  }
  .landscape.p2 {
    grid-template-columns: minmax(300px, 26rem) minmax(0, 1fr) auto;
    grid-template-areas: "cards gif lane" "cards counter lane";
  }
  .portrait {
    grid-template-columns: auto minmax(0, 1fr);
    grid-template-rows: minmax(0, 0.9fr) minmax(0, 1fr) auto;
    grid-template-areas: "gif gif" "lane counter" "cards cards";
  }
  .portrait.p2 { grid-template-areas: "gif gif" "counter lane" "cards cards"; }

  .lane-area { grid-area: lane; aspect-ratio: 685 / 1080; height: 100%; min-height: 0; }
  .gif-area { grid-area: gif; min-height: 0; display: grid; place-items: center; }
  .counter-area { grid-area: counter; min-height: 0; display: grid; place-items: center; }
  .cards { grid-area: cards; display: flex; flex-direction: column; gap: 20px; min-width: 0; }
  .portrait .cards { flex-direction: row; }
  .portrait .cards > * { flex: 1; }

  .placeholder {
    width: 100%; height: 100%; min-height: 120px;
    border: 1px dashed var(--line); color: var(--muted);
    display: grid; place-items: center;
  }

  p { margin: 0; }
  .kicker { color: var(--muted); font-size: 0.95rem; font-stretch: 112%; letter-spacing: 0.02em; margin-bottom: 10px; }
  .title { font-size: 1.9rem; font-weight: 600; font-stretch: 88%; line-height: 1.15; }
  .meta { margin-top: 8px; font-size: 1.05rem; }
  .bpm { font-weight: 700; font-size: 1.35rem; }
  .muted, .empty { color: var(--muted); }
  .result { flex: 1; }

  .conn {
    position: absolute; right: 10px; bottom: 10px;
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--counter-held);
  }
  .conn[data-status="open"] { background: var(--counter-idle); }
  .conn[data-status="closed"] { background: var(--danger); }
</style>
