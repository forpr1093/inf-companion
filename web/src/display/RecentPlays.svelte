<script lang="ts">
  import { recentPlays } from "../lib/stores";
  import { DIFF_VAR, djBorder } from "../lib/score";

  const MAX_ROWS = 6;
</script>

<div class="panel recent"><div class="inner">
  <p class="kicker">Recent plays</p>
  {#if $recentPlays.length === 0}
    <p class="empty">No plays yet</p>
  {:else}
    <table>
      <tbody>
        {#each $recentPlays.slice(0, MAX_ROWS) as p (p.played_at + p.title)}
          {@const b = djBorder(p.score, p.notes)}
          <tr style:--c={DIFF_VAR[p.difficulty]}>
            <td class="diff"><span>{p.difficulty}</span></td>
            <td class="title">{p.title}</td>
            <td class="num">{p.score}</td>
            <td class="border">{b?.label ?? ""}</td>
            <td class="opt">{p.option ?? ""}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div></div>

<style>
  .recent { height: 100%; }
  .recent .inner { overflow: hidden; }
  .kicker { margin: 0 0 6px; color: var(--muted); font-size: 0.95rem; font-stretch: 112%; }
  .empty { margin: 0; font-size: 1.2rem; color: var(--muted); }
  table { width: 100%; border-collapse: collapse; font-size: 1.15rem; }
  tr + tr td { border-top: 1px solid var(--line); }
  tr { height: 2.5rem; }
  td { padding: 0 10px; white-space: nowrap; }
  .diff { width: 1%; }
  .diff span {
    display: inline-block; min-width: 9.5em; text-align: center;
    color: var(--c); border: 1.5px solid var(--c); padding: 0 6px;
    font-size: 0.8rem; font-weight: 600; font-stretch: 110%; letter-spacing: 0.04em;
  }
  .title { color: var(--c); font-weight: 600; max-width: 0; width: 100%; overflow: hidden; text-overflow: ellipsis; }
  .num { text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; }
  .border { color: var(--text); font-stretch: 90%; }
  .opt { color: var(--muted); text-align: right; font-size: 0.95rem; }
</style>
