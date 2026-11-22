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
    /* Beside the lane: now playing, personal best, counter + GIF at 3 : 3 : 2. */
    grid-template-rows: minmax(0, 3fr) minmax(0, 3fr) minmax(0, 2fr) auto;
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
  /* Row heights come from fr ratios, never from content, so data never moves the layout. */
  .now { grid-area: now; min-width: 0; min-height: 0; container-type: size; }
  .pb { grid-area: pb; min-width: 0; min-height: 0; container-type: size; }
  .counter-area { grid-area: counter; min-height: 0; min-width: 0; display: grid; place-items: center; overflow: hidden; container-type: size; }
  .gif-area { grid-area: gif; height: min(100%, 22vw); aspect-ratio: 1; min-height: 0; align-self: center; }
  .recent { grid-area: recent; min-height: 0; min-width: 0; height: calc(36px + 2rem + 6 * 2.5rem); }

  /* Narrower windows: the counter row gets too tight beside the GIF, so the GIF moves
     into its own row above the counter (5 rows). */
  @media (max-width: 1440px) {
    .display {
      grid-template-columns: auto minmax(0, 1fr) minmax(0, 1fr);
      /* now playing, personal best, GIF, counter at 3 : 3 : 1 : 1 */
      grid-template-rows: minmax(0, 3fr) minmax(0, 3fr) minmax(0, 1fr) minmax(0, 1fr) auto;
      grid-template-areas:
        "lane now now"
        "lane pb pb"
        "lane gif gif"
        "lane counter counter"
        "recent recent recent";
    }
    .display.p2 {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
      grid-template-areas:
        "now now lane"
        "pb pb lane"
        "gif gif lane"
        "counter counter lane"
        "recent recent recent";
    }
    .gif-area { height: 100%; justify-self: center; }
  }

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
