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
    <p class="title">{$nowPlaying.title}</p>
  {:else}
    <div class="row">
      <span class="tag empty">No song selected</span>
      <span class="bpm"><b>{$settings.manual_bpm}</b> BPM <span class="muted">(manual)</span></span>
    </div>
    <p class="title muted">Pick a song in INFINITAS</p>
  {/if}
</div></div>

<style>
  .panel { height: 100%; }
  .row { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
  .tag {
    font-size: 0.95rem; font-weight: 600; font-stretch: 110%; letter-spacing: 0.04em;
    border: 1.5px solid; padding: 2px 10px;
  }
  .tag.empty { color: var(--muted); border-color: var(--line); }
  .bpm { font-size: 1.05rem; color: var(--muted); }
  .bpm b { color: var(--text); font-size: 1.5rem; font-weight: 700; }
  .title { margin: 10px 0 0; font-size: clamp(1.6rem, 2.6vw, 2.6rem); font-weight: 600; font-stretch: 85%; line-height: 1.1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .muted { color: var(--muted); }
</style>
