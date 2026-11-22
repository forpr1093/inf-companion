<script lang="ts">
  import { nowPlaying, personalBest } from "../lib/stores";
  import { djBorder, djLevel } from "../lib/score";

  const LAMP_VAR: Record<string, string> = {
    "FULLCOMBO CLEAR": "var(--accent)", "EX HARD CLEAR": "var(--diff-hyper)", "HARD CLEAR": "var(--text)",
    "CLEAR": "var(--diff-normal)", "EASY CLEAR": "var(--diff-beginner)", "ASSIST CLEAR": "var(--diff-leggendaria)",
    "FAILED": "var(--muted)",
  };
  const notes = $derived($personalBest?.notes ?? $nowPlaying?.notes ?? null);
  const grade = $derived($personalBest && notes ? djLevel($personalBest.score, notes) : null);
  const border = $derived($personalBest ? djBorder($personalBest.score, notes) : null);
</script>

<!--
  Stack (user, 2026-11-23): clear type (small) / grade (large) / score (medium) with the
  border difference beside it (small) / misses and last played (small).
-->
<div class="panel"><div class="inner">
  {#if !$nowPlaying || !$personalBest}
    <p class="label">Personal best</p>
    <p class="empty">{$nowPlaying ? "Not played yet" : "No song selected"}</p>
  {:else}
    <p class="clear">
      <span style:color={LAMP_VAR[$personalBest.lamp] ?? "var(--text)"}>{$personalBest.lamp}</span>
      <span class="label">Personal best</span>
    </p>
    <p class="grade">{grade ?? "—"}</p>
    <p class="score">{$personalBest.score}{#if border}<span class="diff">{border.label}</span>{/if}</p>
    <div class="meta">
      {#if $personalBest.miss_count != null}<p>{$personalBest.miss_count} miss{$personalBest.miss_count === 1 ? "" : "es"}</p>{/if}
      {#if $personalBest.last_played}<p>Last played {$personalBest.last_played}</p>{/if}
    </div>
  {/if}
</div></div>

<style>
  /* The section around this panel is a size container: text scales with the cell. */
  .panel { height: 100%; }
  .inner { display: flex; flex-direction: column; justify-content: center; gap: 0.2em; }
  p { margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .label { color: var(--muted); font-size: clamp(0.8rem, 5.5cqh, 1rem); font-weight: 400; font-stretch: 112%; }
  .empty { margin-top: 0.3em; font-size: clamp(1.1rem, 10cqh, 1.8rem); color: var(--muted); }
  .clear { display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
    font-size: clamp(0.85rem, 7cqh, 1.25rem); font-weight: 600; font-stretch: 105%; }
  .grade { font-size: clamp(2.2rem, min(30cqh, 14cqi), 6rem); font-weight: 700; font-stretch: 90%; line-height: 1; }
  .score { font-size: clamp(1.3rem, min(15cqh, 7cqi), 3rem); font-weight: 600; font-stretch: 88%; line-height: 1.1;
    font-variant-numeric: tabular-nums; }
  .diff { margin-left: 0.6em; font-size: 0.5em; font-weight: 500; color: var(--muted); }
  .meta { display: flex; flex-direction: column; gap: 0.15em; margin-top: 0.3em;
    font-size: clamp(0.8rem, 6cqh, 1.1rem); color: var(--muted); }
</style>
