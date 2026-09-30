<script>
  import { api } from "../lib/api.js";
  import ProfileCard from "../lib/components/settings/ProfileCard.svelte";
  import SplitwiseCard from "../lib/components/settings/SplitwiseCard.svelte";
  import CategorieCard from "../lib/components/settings/CategorieCard.svelte";

  let displayName = $state("");
  let splitwiseConfigured = $state(false);
  let cats = $state([]); // [{ name, color, icon }]
  let error = $state("");

  async function load() {
    try {
      const [s, c] = await Promise.all([api.get("/settings"), api.get("/categories")]);
      displayName = s.display_name || "";
      splitwiseConfigured = s.splitwise_configured;
      cats = c.categories.map((n) => ({
        name: n,
        color: c.colors[n] || "#0e7490",
        icon: (c.icons && c.icons[n]) || "repeat",
      }));
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    load();
  });
</script>

<section>
  <div class="page-header">
    <h2>Impostazioni</h2>
    <p class="subtitle">Preferenze e servizi collegati — restano su questo database, non nel codice.</p>
  </div>

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else}
    <ProfileCard bind:displayName onerror={(msg) => (error = msg)} />
    <SplitwiseCard bind:splitwiseConfigured onerror={(msg) => (error = msg)} />
    <CategorieCard {cats} onchange={load} />
  {/if}
</section>

<style>
  .page-header {
    margin-bottom: var(--space-5);
  }

  .subtitle {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 4px 0 0;
  }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
