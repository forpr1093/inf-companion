<script lang="ts">
  import { onMount } from "svelte";
  import "./lib/theme.css";
  import Display from "./display/Display.svelte";
  import Settings from "./settings/Settings.svelte";
  import { settings, startConnection } from "./lib/stores";

  let route = $state(location.hash || "#/");

  $effect(() => {
    document.documentElement.dataset.theme = $settings.theme;
  });

  onMount(() => {
    startConnection();
    const onHash = () => (route = location.hash || "#/");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  });
</script>

{#if route.startsWith("#/settings")}
  <Settings />
{:else}
  <Display />
{/if}
