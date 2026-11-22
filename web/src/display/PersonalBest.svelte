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
      <span class="score">{$personalBest.score}</span>
      {#if border}<span class="border">{border.label}</span>{/if}
      <span class="lamp" style:color={LAMP_VAR[$personalBest.lamp] ?? "var(--text)"}>{$personalBest.lamp}</span>
      <span class="meta">
        {#if $personalBest.miss_count != null}{$personalBest.miss_count} miss{$personalBest.miss_count === 1 ? "" : "es"}{/if}
        {#if $personalBest.last_played}<span class="sep"></span>last played {$personalBest.last_played}{/if}
      </span>
    </div>
  {/if}
</div></div>

<style>
  .panel { height: 100%; }
  .kicker { margin: 0 0 6px; color: var(--muted); font-size: 0.95rem; font-stretch: 112%; }
  .empty { margin: 0; font-size: 1.35rem; color: var(--muted); }
  .best { display: flex; align-items: baseline; flex-wrap: wrap; gap: 6px 22px; }
  .score { font-size: clamp(2rem, 3.4vw, 3.2rem); font-weight: 700; font-stretch: 85%; line-height: 1; }
  .border { font-size: 1.5rem; font-weight: 600; font-stretch: 90%; }
  .lamp { font-size: 1.1rem; font-weight: 600; font-stretch: 105%; }
  .meta { color: var(--muted); font-size: 1rem; }
  .sep { display: inline-block; width: 14px; }
</style>
