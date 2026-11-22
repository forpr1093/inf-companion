<script lang="ts">
  import { onMount } from "svelte";
  import { startConnection, status } from "./lib/stores";

  let route = $state(location.hash || "#/");
  onMount(() => {
    startConnection();
    const onHash = () => (route = location.hash || "#/");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  });
</script>

{#if route.startsWith("#/settings")}
  <main><h1>Settings</h1><p>coming soon</p></main>
{:else}
  <main><h1>Display</h1></main>
{/if}
<p class="status" data-status={$status}>{$status}</p>
