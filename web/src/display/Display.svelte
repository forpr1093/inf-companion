<script lang="ts">
  import { onMount } from "svelte";
  import { captureStatus, emitKey, screen, settings, status } from "../lib/stores";
  import { devKeyboard, startDemo } from "../lib/demo";
  import { demoPanels } from "../lib/demoPanels";
  import Lane from "../lib/lane/Lane.svelte";
  import Counter from "../lib/counter/Counter.svelte";
  import NowPlaying from "./NowPlaying.svelte";
  import PersonalBest from "./PersonalBest.svelte";
  import RecentPlays from "./RecentPlays.svelte";
  import GifPlayer from "../lib/gif/GifPlayer.svelte";

  const params = new URLSearchParams(location.search);
  const demo = params.has("demo");
  const dev = params.has("dev");
  const debug = params.has("debug");

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
  <section class="gif-area" aria-label="Loop"><GifPlayer /></section>
  <section class="recent"><RecentPlays /></section>
  {#if debug}
    <span class="screen-debug">screen: {$screen ?? "—"} · capture: {$captureStatus.state}{$captureStatus.message ? ` (${$captureStatus.message})` : ""}</span>
  {/if}
  <a class="to-settings" href="#/settings" aria-label="Settings">Settings</a>
  <span class="conn" data-status={$status} title="Server connection: {$status}" aria-label="Server connection: {$status}"></span>
</div>

<style>
  /* One layout for every screen size (user, 2026-11-23): 3 columns × 5 rows.
       col 1: lane (rows 1–4), button counter (row 5)
       cols 2–3: now playing (row 1), GIF + personal best 3 : 5 (row 2),
                 recent plays (rows 3–5)
     Row heights are ratios, never content, so data never moves the layout. */
  .display {
    height: 100vh;
    display: grid;
    gap: 18px;
    padding: 18px;
    position: relative;
    grid-template-columns: auto minmax(0, 3fr) minmax(0, 5fr);
    grid-template-rows: minmax(0, 2fr) minmax(0, 3fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 2fr);
    grid-template-areas:
      "lane now now"
      "lane gif pb"
      "lane recent recent"
      "lane recent recent"
      "counter recent recent";
  }
  .display.p2 {
    grid-template-columns: minmax(0, 3fr) minmax(0, 5fr) auto;
    grid-template-areas:
      "now now lane"
      "gif pb lane"
      "recent recent lane"
      "recent recent lane"
      "recent recent counter";
  }
  .lane-area { grid-area: lane; height: 100%; aspect-ratio: 0.62; min-height: 0; }
  .now { grid-area: now; min-width: 0; min-height: 0; container-type: size; }
  .pb { grid-area: pb; min-width: 0; min-height: 0; }
  .counter-area { grid-area: counter; min-height: 0; min-width: 0; display: grid; place-items: center; overflow: hidden; container-type: size; }
  .gif-area { grid-area: gif; min-height: 0; min-width: 0; }
  .recent { grid-area: recent; min-height: 0; min-width: 0; }

  .screen-debug {
    position: absolute; left: 18px; bottom: 0; font-size: 0.75rem; color: var(--muted);
    max-width: 60vw; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .to-settings {
    position: absolute; right: 20px; bottom: 0; font-size: 0.75rem; color: var(--muted);
    text-decoration: none; opacity: 0.4;
  }
  .to-settings:hover, .to-settings:focus-visible { opacity: 1; color: var(--text); }
  .conn {
    position: absolute; right: 6px; bottom: 6px;
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--counter-held);
  }
  .conn[data-status="open"] { background: var(--counter-idle); }
  .conn[data-status="closed"] { background: var(--danger); }
</style>
