<script>
  import { api } from "../lib/api.js";

  let months = $state([]);
  let error = $state("");

  $effect(() => {
    api.get("/transactions/months").then((m) => (months = m)).catch((e) => (error = e.message));
  });
</script>

<section>
  <h2>Dashboard</h2>
  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else}
    <p>Mesi disponibili: {months.length ? months.join(", ") : "nessuno ancora"}</p>
  {/if}
</section>

<style>
  .error { color: var(--danger); }
</style>
