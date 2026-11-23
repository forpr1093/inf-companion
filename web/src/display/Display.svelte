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
  <footer class="status-bar">
    <span class="stat"><span class="k">Screen:</span> {$screen ?? "—"}</span>
    <span class="stat" class:ok={$captureStatus.state === "running"} class:bad={$captureStatus.state !== "running"} title={$captureStatus.message ?? ""}>
      <span class="k">Capture:</span> {$captureStatus.state}
    </span>
    <a class="to-settings" href="#/settings">
      <svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
      Settings
    </a>
    <span class="conn" data-status={$status} title="Server connection: {$status}" aria-label="Server connection: {$status}"></span>
  </footer>
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
    padding: 18px 18px 64px;  /* bottom: room for the status bar */
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

  /* Bottom-right status bar: Screen · Capture · Settings (user, 2026-11-23). */
  .status-bar {
    position: absolute; right: 18px; bottom: 12px; height: 40px;
    display: flex; align-items: center; gap: 20px;
    font-size: 1rem; color: var(--text); white-space: nowrap;
  }
  .stat .k { color: var(--muted); margin-right: 4px; }
  .stat.ok { color: var(--counter-idle); }
  .stat.bad { color: var(--danger); }
  .stat.bad .k { color: var(--danger); opacity: 0.8; }
  .to-settings {
    height: 40px; padding: 0 16px; display: inline-flex; align-items: center; gap: 8px;
    border: 1px solid var(--line-strong); border-radius: 8px; background: var(--panel);
    color: var(--text); text-decoration: none; font-weight: 600;
  }
  .to-settings:hover, .to-settings:focus-visible { border-color: var(--accent); color: var(--accent); }
  .conn {
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--counter-held);
  }
  .conn[data-status="open"] { background: var(--counter-idle); }
  .conn[data-status="closed"] { background: var(--danger); }
</style>
