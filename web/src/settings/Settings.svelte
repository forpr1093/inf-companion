<script lang="ts">
  import { hasGif, patchSettings, settings, uploadGif } from "../lib/stores";
  import type { Settings } from "../lib/events";
  import Bindings from "./Bindings.svelte";

  let errors = $state<Record<string, string>>({});
  let gifMsg = $state<string | null>(null);
  let gifErr = $state(false);

  async function save(patch: Partial<Settings>, field: string) {
    try {
      await patchSettings(patch);
      errors = { ...errors, [field]: "" };
    } catch (e) {
      errors = { ...errors, [field]: (e as Error).message };
    }
  }

  async function onGif(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    if (!file) return;
    try {
      await uploadGif(file);
      gifErr = false; gifMsg = `Uploaded ${file.name}`;
    } catch (e) {
      gifErr = true; gifMsg = (e as Error).message;
    }
  }
</script>

<main class="settings">
  <header>
    <h1>Settings</h1>
    <a href="#/">Back to display</a>
  </header>

  <section class="block">
    <h2>Play</h2>
    <fieldset>
      <legend>Side</legend>
      {#each ["1P", "2P"] as side}
        <label><input type="radio" name="side" value={side} checked={$settings.side === side}
          onchange={() => save({ side: side as Settings["side"] }, "side")} /> {side}</label>
      {/each}
    </fieldset>
    <fieldset>
      <legend>Theme</legend>
      {#each ["dark", "light"] as theme}
        <label><input type="radio" name="theme" value={theme} checked={$settings.theme === theme}
          onchange={() => save({ theme: theme as Settings["theme"] }, "theme")} /> {theme === "dark" ? "Dark" : "Light"}</label>
      {/each}
    </fieldset>
  </section>

  <section class="block">
    <h2>GIF</h2>
    <label class="field">GIF file
      <input type="file" accept="image/gif" onchange={onGif} />
    </label>
    {#if gifMsg}<p class:error={gifErr} class:muted={!gifErr}>{gifMsg}</p>{:else if $hasGif}<p class="muted">A GIF is uploaded.</p>{/if}
    <label class="field">Beats per loop
      <input type="number" min="1" max="64" step="1" value={$settings.beats_per_loop}
        onchange={e => save({ beats_per_loop: Number((e.target as HTMLInputElement).value) }, "beats_per_loop")} />
    </label>
    {#if errors.beats_per_loop}<p class="error">{errors.beats_per_loop}</p>{/if}
    <label class="field">Manual BPM <span class="muted">(used until the song's BPM is known)</span>
      <input type="number" min="30" max="999" step="1" value={$settings.manual_bpm}
        onchange={e => save({ manual_bpm: Number((e.target as HTMLInputElement).value) }, "manual_bpm")} />
    </label>
    {#if errors.manual_bpm}<p class="error">{errors.manual_bpm}</p>{/if}
  </section>

  <Bindings />
</main>

<style>
  .settings { max-width: 760px; margin: 0 auto; padding: 32px 20px 64px; }
  header { display: flex; justify-content: space-between; align-items: baseline; }
  h1 { font-size: 2rem; font-stretch: 90%; margin: 0 0 8px; }
  a { color: var(--accent); }
  :global(.settings .block) { border-top: 1px solid var(--line); padding: 20px 0; }
  :global(.settings h2) { font-size: 1.2rem; font-weight: 600; margin: 0 0 14px; }
  :global(.settings .muted) { color: var(--muted); }
  :global(.settings button) { font: inherit; color: var(--text); background: var(--panel); border: 1px solid var(--line-strong); padding: 8px 16px; cursor: pointer; }
  :global(.settings button.primary) { border-color: var(--accent); color: var(--accent); }
  :global(.settings button:disabled) { opacity: 0.5; cursor: default; }
  fieldset { border: none; padding: 0; margin: 0 0 14px; display: flex; gap: 18px; align-items: center; }
  legend { float: left; width: 7rem; color: var(--muted); }
  .field { display: grid; gap: 6px; margin-bottom: 14px; }
  input[type="number"] { font: inherit; width: 8rem; padding: 6px 8px; background: var(--panel); color: var(--text); border: 1px solid var(--line-strong); }
  .error { color: var(--danger); margin: -6px 0 14px; }
</style>
