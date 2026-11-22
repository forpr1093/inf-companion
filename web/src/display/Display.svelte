<script lang="ts">
  import { onMount } from "svelte";
  import { emitKey, settings, status } from "../lib/stores";
  import { devKeyboard, startDemo } from "../lib/demo";
  import { demoPanels } from "../lib/demoPanels";
  import Lane from "../lib/lane/Lane.svelte";
  import Counter from "../lib/counter/Counter.svelte";
  import NowPlaying from "./NowPlaying.svelte";
  import PersonalBest from "./PersonalBest.svelte";
  import RecentPlays from "./RecentPlays.svelte";

  const params = new URLSearchParams(location.search);
  const demo = params.has("demo");
  const dev = params.has("dev");

  onMount(() => {
    const stops: (() => void)[] = [];
    if (demo) { stops.push(startDemo(emitKey, { seed: 3, bpm: $settings.manual_bpm })); demoPanels(); }
    if (dev) stops.push(devKeyboard(emitKey));
    return () => stops.forEach(s => s());
  });
</script>

<div class="display" class:p2={$settings.side === "2P"}>
  <section class="lane-area" aria-label="Key lane"><Lane /></section>
  <section class="now"><NowPlaying /></section>
  <section class="pb"><PersonalBest /></section>
  <section class="counter-area" aria-label="Button counter"><Counter /></section>
  <section class="gif-area" aria-label="Loop"><div class="placeholder">GIF</div></section>
  <section class="recent"><RecentPlays /></section>
  <span class="conn" data-status={$status} title="Server connection: {$status}" aria-label="Server connection: {$status}"></span>
</div>

<style>
  .display {
    height: 100vh;
    display: grid;
    gap: 18px;
    padding: 18px;
    position: relative;
    grid-template-columns: auto minmax(0, 1fr) auto;
    grid-template-rows: auto auto minmax(0, 1fr) auto;
    grid-template-areas:
      "lane now now"
      "lane pb pb"
      "lane counter gif"
      "recent recent recent";
  }
  .display.p2 {
    grid-template-columns: minmax(0, 1fr) auto auto;
    grid-template-areas:
      "now now lane"
      "pb pb lane"
      "counter gif lane"
      "recent recent recent";
  }
  .lane-area { grid-area: lane; height: 100%; aspect-ratio: 0.62; min-height: 0; }
  .now { grid-area: now; min-width: 0; }
  .pb { grid-area: pb; min-width: 0; }
  .counter-area { grid-area: counter; min-height: 0; min-width: 0; display: grid; place-items: center; }
  .gif-area { grid-area: gif; height: 100%; aspect-ratio: 1; min-height: 0; }
  .recent { grid-area: recent; min-height: 0; min-width: 0; }

  .placeholder {
    width: 100%; height: 100%;
    border: 1px dashed var(--line); color: var(--muted);
    display: grid; place-items: center;
  }
  .conn {
    position: absolute; right: 6px; bottom: 6px;
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--counter-held);
  }
  .conn[data-status="open"] { background: var(--counter-idle); }
  .conn[data-status="closed"] { background: var(--danger); }
</style>
