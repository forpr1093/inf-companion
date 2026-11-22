<script lang="ts">
  import { onMount } from "svelte";
  import { counts, send, settings, subscribeKeys, subscribeReset } from "../stores";
  import type { Target } from "../events";
  import { counterTarget } from "./counts";

  const TOP: Target[] = ["2", "4", "6"];
  const BOTTOM: Target[] = ["1", "3", "5", "7"];

  let held = $state<Record<string, boolean>>({});

  onMount(() => {
    const unKeys = subscribeKeys(e => {
      const t = counterTarget(e);
      held = { ...held, [t]: e.type === "key_down" };
    });
    const unReset = subscribeReset(() => (held = {}));
    return () => { unKeys(); unReset(); };
  });

  const reset = () => send({ type: "counts_reset" });
</script>

<div class="counter" class:p2={$settings.side === "2P"}>
  <div class="disc" class:held-up={held.S_up} class:held-down={held.S_down} aria-label="Turntable presses">
    <span class="dir up" aria-label="scratch up">{$counts.S_up}</span>
    <span class="dir down" aria-label="scratch down">{$counts.S_down}</span>
  </div>
  <div class="keys">
    <div class="row top">
      {#each TOP as k}<span class="box" class:held={held[k]} aria-label="key {k}">{$counts[k]}</span>{/each}
    </div>
    <div class="row">
      {#each BOTTOM as k}<span class="box" class:held={held[k]} aria-label="key {k}">{$counts[k]}</span>{/each}
    </div>
  </div>
  <button class="reset" type="button" onclick={reset}>Reset counts</button>
</div>

<style>
  .counter {
    --box: clamp(44px, 9cqi, 92px);
    container-type: inline-size;
    width: 100%;
    display: grid;
    grid-template-columns: auto auto;
    grid-template-areas: "disc keys" ". reset";
    justify-content: center;
    align-items: center;
    column-gap: calc(var(--box) * 0.6);
    row-gap: 10px;
  }
  .counter.p2 { grid-template-areas: "keys disc" "reset ."; }

  .keys { grid-area: keys; display: grid; gap: calc(var(--box) * 0.18); }
  .row { display: flex; gap: calc(var(--box) * 0.18); }
  .row.top { padding-left: calc(var(--box) * 0.59); }

  .box {
    width: var(--box);
    height: calc(var(--box) * 1.32);
    display: grid;
    place-items: center;
    border: 3px solid var(--counter-idle);
    background: color-mix(in srgb, var(--panel) 70%, transparent);
    font-size: calc(var(--box) * 0.36);
    font-weight: 500;
    font-stretch: 85%;
    color: var(--counter-idle);
    font-variant-numeric: tabular-nums;
  }
  .box.held { border-color: var(--counter-held); color: var(--counter-held); }

  .disc {
    grid-area: disc;
    width: calc(var(--box) * 2.7);
    aspect-ratio: 1;
    border-radius: 50%;
    position: relative;
    display: grid;
    grid-template-rows: 1fr 1fr;
    border: calc(var(--box) * 0.14) solid var(--line-strong);
    box-shadow: inset 0 0 0 2px var(--line), 0 0 0 2px var(--line);
    background: linear-gradient(var(--panel) 0 50%, var(--bg) 50% 100%);
    overflow: hidden;
    font-variant-numeric: tabular-nums;
  }
  .disc::after {
    content: ""; position: absolute; left: 0; right: 0; top: 50%; height: 2px;
    background: var(--line-strong);
  }
  .dir {
    display: grid; place-items: center;
    font-size: calc(var(--box) * 0.42);
    font-weight: 500; font-stretch: 85%;
    color: var(--muted);
  }
  .dir.up { align-items: end; padding-bottom: 6%; }
  .dir.down { align-items: start; padding-top: 6%; }
  .held-up .up, .held-down .down { color: var(--counter-held); }
  .held-up { background: linear-gradient(color-mix(in srgb, var(--accent) 35%, var(--panel)) 0 50%, var(--bg) 50% 100%); }
  .held-down { background: linear-gradient(var(--panel) 0 50%, color-mix(in srgb, var(--accent) 35%, var(--bg)) 50% 100%); }

  .reset {
    grid-area: reset; justify-self: end;
    font: inherit; font-size: 0.85rem; color: var(--muted);
    background: none; border: 1px solid var(--line); padding: 4px 10px; cursor: pointer;
  }
  .counter.p2 .reset { justify-self: start; }
  .reset:hover { color: var(--text); border-color: var(--line-strong); }
</style>
