<script>
  import { api } from "../lib/api.js";

  let months = $state([]);
  let error = $state("");

  $effect(() => {
    api.get("/summaries/months").then((m) => (months = m)).catch((e) => (error = e.message));
  });
</script>

<section>
  <h2>📓 Storico Notion</h2>
  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else}
    <p>Mesi importati da Notion: {months.length ? months.join(", ") : "nessuno ancora"}</p>
  {/if}
</section>

<style>
  .error { color: #d85a30; }
</style>
