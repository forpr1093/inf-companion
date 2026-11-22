<script lang="ts">
  import { nowPlaying, personalBest } from "../lib/stores";
  import { djBorder } from "../lib/score";

  const LAMP_VAR: Record<string, string> = {
    "FULLCOMBO CLEAR": "var(--accent)", "EX HARD CLEAR": "var(--diff-hyper)", "HARD CLEAR": "var(--text)",
    "CLEAR": "var(--diff-normal)", "EASY CLEAR": "var(--diff-beginner)", "ASSIST CLEAR": "var(--diff-leggendaria)",
    "FAILED": "var(--muted)",
  };
  const border = $derived($personalBest ? djBorder($personalBest.score, $personalBest.notes ?? $nowPlaying?.notes ?? null) : null);
</script>

<div class="panel"><div class="inner">
  <p class="kicker">Personal best</p>
  {#if !$nowPlaying}
    <p class="empty">No song selected</p>
  {:else if !$personalBest}
    <p class="empty">Not played yet</p>
  {:else}
    <div class="best">
      <div class="main">
        <span class="score">{$personalBest.score}</span>
        {#if border}<span class="border">{border.label}</span>{/if}
      </div>
      <div class="side">
        <span class="lamp" style:color={LAMP_VAR[$personalBest.lamp] ?? "var(--text)"}>{$personalBest.lamp}</span>
        {#if $personalBest.miss_count != null}
          <span class="meta">{$personalBest.miss_count} miss{$personalBest.miss_count === 1 ? "" : "es"}</span>
        {/if}
        {#if $personalBest.last_played}<span class="meta">last played {$personalBest.last_played}</span>{/if}
      </div>
    </div>
  {/if}
</div></div>

<style>
  /* The section around this panel is a size container: text scales with the cell. */
  .panel { height: 100%; }
  .inner { display: flex; flex-direction: column; }
  .kicker { margin: 0 0 6px; color: var(--muted); font-size: clamp(0.85rem, 6.5cqh, 1.05rem); font-stretch: 112%; }
  .empty { margin: auto 0; font-size: clamp(1.1rem, 10cqh, 1.8rem); color: var(--muted); }
  .best { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: space-between; gap: 24px; }
  .main { display: flex; align-items: baseline; gap: 0.5em; min-width: 0; }
  .score { font-size: clamp(2rem, min(34cqh, 9cqi), 5.5rem); font-weight: 700; font-stretch: 85%; line-height: 1; font-variant-numeric: tabular-nums; }
  .border { font-size: clamp(1.2rem, min(14cqh, 3.6cqi), 2.3rem); font-weight: 600; font-stretch: 90%; }
  .side { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; text-align: right; }
  .lamp { font-size: clamp(1rem, 9cqh, 1.5rem); font-weight: 600; font-stretch: 105%; }
  .meta { color: var(--muted); font-size: clamp(0.85rem, 7cqh, 1.15rem); }
</style>
