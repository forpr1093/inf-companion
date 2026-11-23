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
  Stack (user, 2026-11-23): "Personal best" header / clear type (small) / grade (large) / score (medium) with the
  border difference beside it (small) / misses (small) / last played (small, bottom right).
-->
<div class="panel"><div class="inner">
  {#if !$nowPlaying || !$personalBest}
    <p class="panel-title">Personal best</p>
    <p class="empty">{$nowPlaying ? "Not played yet" : "No song selected"}</p>
  {:else}
    <p class="panel-title">Personal best</p>
    <p class="clear" style:color={LAMP_VAR[$personalBest.lamp] ?? "var(--text)"}>{$personalBest.lamp}</p>
    <p class="grade">{grade ?? "—"}</p>
    <p class="score">{$personalBest.score}{#if border}<span class="diff">{border.label}</span>{/if}</p>
    {#if $personalBest.miss_count != null}
      <p class="meta">{$personalBest.miss_count} miss{$personalBest.miss_count === 1 ? "" : "es"}</p>
    {/if}
    {#if $personalBest.last_played}<p class="meta last">Last played {$personalBest.last_played}</p>{/if}
  {/if}
</div></div>

<style>
  /* Fixed text sizes (user, 2026-11-23): resizing the window moves things, never resizes them. */
  .panel { height: 100%; }
  .inner { display: flex; flex-direction: column; gap: 0.2em; }
  p { margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .empty { margin-top: 0.3em; font-size: 1.4rem; color: var(--muted); }
  .clear { font-size: 1.1rem; font-weight: 600; font-stretch: 105%; }
  .grade { font-size: 4.5rem; font-weight: 700; font-stretch: 90%; line-height: 1; }
  .score { font-size: 2.2rem; font-weight: 600; font-stretch: 88%; line-height: 1.1;
    font-variant-numeric: tabular-nums; }
  .diff { margin-left: 0.6em; font-size: 0.5em; font-weight: 500; color: var(--muted); }
  .meta { margin-top: 0.3em; font-size: 1rem; color: var(--muted); }
  /* Last played sits at the very end of the panel, on the right. */
  .last { margin-top: auto; align-self: flex-end; }
</style>
