<script>
  import { api } from "../lib/api.js";

  let plannedExpenses = $state([]);
  let error = $state("");

  $effect(() => {
    api.get("/planning/planned-expenses").then((p) => (plannedExpenses = p)).catch((e) => (error = e.message));
  });
</script>

<section>
  <h2>🎯 Pianificazione & Budget</h2>
  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if plannedExpenses.length === 0}
    <p>Nessuna spesa fissa ancora.</p>
  {:else}
    <ul>
      {#each plannedExpenses as p}
        <li>{p.description} — €{p.amount} — {p.category}</li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .error { color: var(--danger); }
</style>
