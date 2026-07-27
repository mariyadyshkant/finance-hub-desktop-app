<script>
  import { api } from "../lib/api.js";

  let transactions = $state([]);
  let error = $state("");

  $effect(() => {
    api.get("/transactions").then((t) => (transactions = t)).catch((e) => (error = e.message));
  });
</script>

<section>
  <h2>💳 Transazioni</h2>
  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if transactions.length === 0}
    <p>Nessuna transazione ancora.</p>
  {:else}
    <ul>
      {#each transactions as tx}
        <li>{tx.date} — {tx.description} — €{tx.amount} — {tx.category}</li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .error { color: #d85a30; }
</style>
