<script>
  import { api } from "../lib/api.js";

  let reimbursements = $state([]);
  let error = $state("");

  $effect(() => {
    api.get("/reimbursements").then((r) => (reimbursements = r)).catch((e) => (error = e.message));
  });
</script>

<section>
  <h2>🔄 Rimborsi</h2>
  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if reimbursements.length === 0}
    <p>Nessun rimborso ancora.</p>
  {:else}
    <ul>
      {#each reimbursements as r}
        <li>{r.date} — {r.description} — €{r.amount} — {r.from_person} — {r.status}</li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .error { color: #d85a30; }
</style>
