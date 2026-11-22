<script lang="ts">
  import { nowPlaying, settings } from "../lib/stores";
  import { DIFF_VAR } from "../lib/score";
</script>

<div class="panel"><div class="inner">
  {#if $nowPlaying}
    <div class="row">
      <span class="tag" style:color={DIFF_VAR[$nowPlaying.difficulty]} style:border-color={DIFF_VAR[$nowPlaying.difficulty]}>
        {$nowPlaying.difficulty} {$nowPlaying.level}
      </span>
      <span class="bpm"><b>{$nowPlaying.bpm ?? $settings.manual_bpm}</b> BPM{#if $nowPlaying.bpm == null}<span class="muted"> (manual)</span>{/if}</span>
    </div>
    <div class="song">
      <p class="title">{$nowPlaying.title}</p>
      {#if $nowPlaying.artist}<p class="artist">{$nowPlaying.artist}</p>{/if}
    </div>
  {:else}
    <div class="row">
      <span class="tag empty">No song selected</span>
      <span class="bpm"><b>{$settings.manual_bpm}</b> BPM <span class="muted">(manual)</span></span>
    </div>
    <div class="song">
      <p class="title muted">Pick a song in INFINITAS</p>
    </div>
  {/if}
</div></div>

<style>
  /* The section around this panel is a size container: text scales with the cell. */
  .panel { height: 100%; }
  .inner { display: flex; flex-direction: column; }
  .row { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
  .tag {
    font-size: clamp(0.8rem, 7cqh, 1.15rem); font-weight: 600; font-stretch: 110%; letter-spacing: 0.04em;
    border: 1.5px solid; padding: 2px 10px;
  }
  .tag.empty { color: var(--muted); border-color: var(--line); }
  .bpm { font-size: clamp(0.9rem, 7cqh, 1.2rem); color: var(--muted); }
  .bpm b { color: var(--text); font-size: 1.5em; font-weight: 700; }
  .song { flex: 1; display: flex; flex-direction: column; justify-content: center; min-height: 0; }
  p { margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .title { font-size: clamp(1.4rem, min(19cqh, 5.5cqi), 3.4rem); font-weight: 600; font-stretch: 85%; line-height: 1.12; }
  .artist { margin-top: 0.35em; font-size: clamp(0.95rem, min(9cqh, 2.6cqi), 1.6rem); color: var(--muted); font-stretch: 95%; }
  .muted { color: var(--muted); }
</style>
