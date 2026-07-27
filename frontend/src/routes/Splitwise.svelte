<script>
  import { api } from "../lib/api.js";

  let user = $state(null);
  let error = $state("");

  $effect(() => {
    api.get("/splitwise/user").then((u) => (user = u)).catch((e) => (error = e.message));
  });
</script>

<section>
  <h2>🏦 Splitwise</h2>
  {#if error}
    <p class="error">{error}</p>
  {:else if user}
    <p>Connessa come {user.first_name} {user.last_name}</p>
  {:else}
    <p>Configura la Splitwise API key in <code>backend/.env</code> per collegare l'account.</p>
  {/if}
</section>

<style>
  .error { color: #d85a30; }
</style>
