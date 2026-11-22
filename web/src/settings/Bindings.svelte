<script lang="ts">
  import { bindProgress, bindings, devices, send } from "../lib/stores";
  import { TARGETS } from "../lib/events";
  import { bindPrompt, sourceText, targetName } from "./bindText";

  const start = () => send({ type: "bind_start" });
  const cancel = () => send({ type: "bind_cancel" });
</script>

<section class="block">
  <h2>Controller</h2>
  {#if $devices.length === 0}
    <p class="muted">No controller found. Plug it in; it shows up here without restarting.</p>
  {:else}
    <ul class="devices">
      {#each $devices as d (d.guid)}
        <li>
          <span class="name">{d.name || "Unnamed controller"}</span>
          <span class="badge" class:ok={d.bound}>{d.bound ? "Bound" : "Not bound"}</span>
        </li>
      {/each}
    </ul>
  {/if}

  {#if $bindProgress}
    <div class="prompt" role="status" aria-live="polite">
      <p class="step">Step {$bindProgress.index + 1} of {$bindProgress.total}</p>
      <p class="ask">{bindPrompt($bindProgress.target)}</p>
      <div class="mini" aria-hidden="true">
        {#each TARGETS as t, i}
          <span class:done={i < $bindProgress.index} class:now={t === $bindProgress.target}>{t === "S_up" ? "S↑" : t === "S_down" ? "S↓" : t}</span>
        {/each}
      </div>
      <button type="button" onclick={cancel}>Cancel</button>
    </div>
  {:else}
    <button type="button" class="primary" onclick={start} disabled={$devices.length === 0}>Bind controller</button>
    <p class="muted hint">You press each key in turn, then spin the turntable both ways. The first controller you touch is the one bound.</p>
  {/if}

  {#each Object.values($bindings) as b (b.device_guid)}
    <details>
      <summary>Saved binding: {b.name}</summary>
      <table>
        <tbody>
          {#each TARGETS as t}<tr><td>{targetName(t)}</td><td>{sourceText(b.map[t])}</td></tr>{/each}
        </tbody>
      </table>
    </details>
  {/each}
</section>

<style>
  .devices { list-style: none; padding: 0; margin: 0 0 14px; display: grid; gap: 8px; }
  .devices li { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border: 1px solid var(--line); }
  .badge { font-size: 0.85rem; color: var(--muted); border: 1px solid var(--line); padding: 1px 8px; }
  .badge.ok { color: var(--counter-idle); border-color: var(--counter-idle); }
  .prompt { border: 1px solid var(--accent); padding: 18px; margin-bottom: 14px; }
  .step { margin: 0; color: var(--muted); }
  .ask { margin: 6px 0 14px; font-size: 1.8rem; font-weight: 600; font-stretch: 90%; }
  .mini { display: flex; gap: 6px; margin-bottom: 14px; }
  .mini span { min-width: 2.2em; text-align: center; padding: 4px 0; border: 1px solid var(--line); color: var(--muted); }
  .mini span.done { color: var(--counter-idle); border-color: var(--counter-idle); }
  .mini span.now { color: var(--counter-held); border-color: var(--counter-held); }
  .hint { margin-top: 8px; }
  details { margin-top: 14px; }
  td { padding: 3px 14px 3px 0; }
  td:last-child { color: var(--muted); }
</style>
