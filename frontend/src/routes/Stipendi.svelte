<script>
  import { api } from "../lib/api.js";

  let salaryRecords = $state([]);
  let error = $state("");

  $effect(() => {
    api.get("/salary").then((s) => (salaryRecords = s)).catch((e) => (error = e.message));
  });
</script>

<section>
  <h2>Stipendi & Ore lavorate</h2>
  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if salaryRecords.length === 0}
    <p>Nessuno stipendio registrato ancora.</p>
  {:else}
    <ul>
      {#each salaryRecords as s}
        <li>{s.month} — netto €{s.net}</li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .error { color: var(--danger); }
</style>
