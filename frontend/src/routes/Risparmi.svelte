<script>
  import { api } from "../lib/api.js";

  let savings = $state([]);
  let error = $state("");

  $effect(() => {
    api.get("/savings").then((s) => (savings = s)).catch((e) => (error = e.message));
  });
</script>

<section>
  <h2>🐷 Risparmi</h2>
  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if savings.length === 0}
    <p>Nessun dato ancora.</p>
  {:else}
    <ul>
      {#each savings as s}
        <li>{s.date} — €{s.amount} — {s.label}</li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .error { color: #d85a30; }
</style>
