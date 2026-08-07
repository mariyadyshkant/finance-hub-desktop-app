<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";

  let displayName = $state("");
  let splitwiseConfigured = $state(false);
  let splitwiseKeyInput = $state("");
  let error = $state("");

  let nameSaving = $state(false);
  let nameSaved = $state(false);
  let splitwiseSaving = $state(false);
  let splitwiseSaved = $state(false);
  let splitwiseError = $state("");

  async function load() {
    try {
      const s = await api.get("/settings");
      displayName = s.display_name || "";
      splitwiseConfigured = s.splitwise_configured;
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    load();
  });

  async function saveName() {
    nameSaving = true;
    nameSaved = false;
    try {
      await api.post("/settings/profile", { display_name: displayName });
      nameSaved = true;
      setTimeout(() => (nameSaved = false), 2000);
    } catch (e) {
      error = e.message;
    } finally {
      nameSaving = false;
    }
  }

  async function saveSplitwiseKey(e) {
    e.preventDefault();
    if (!splitwiseKeyInput.trim()) {
      splitwiseError = "Inserisci una chiave API.";
      return;
    }
    splitwiseSaving = true;
    splitwiseError = "";
    try {
      await api.post("/settings/splitwise", { api_key: splitwiseKeyInput });
      splitwiseKeyInput = "";
      splitwiseConfigured = true;
      splitwiseSaved = true;
      setTimeout(() => (splitwiseSaved = false), 2000);
    } catch (e2) {
      splitwiseError = e2.message;
    } finally {
      splitwiseSaving = false;
    }
  }

  async function disconnectSplitwise() {
    try {
      await api.delete("/settings/splitwise");
      splitwiseConfigured = false;
    } catch (e) {
      error = e.message;
    }
  }
</script>

<section>
  <div class="page-header">
    <h2>Impostazioni</h2>
    <p class="subtitle">Preferenze e servizi collegati — restano su questo database, non nel codice.</p>
  </div>

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else}
    <div class="metric-card">
      <h3>Profilo</h3>
      <p class="hint">Il nome mostrato nella barra laterale.</p>
      <div class="row-input">
        <input type="text" bind:value={displayName} placeholder="Il tuo nome" />
        <button class="btn-primary" onclick={saveName} disabled={nameSaving}>
          {nameSaving ? "Salvataggio..." : "Salva"}
        </button>
        {#if nameSaved}<span class="saved"><Icon name="check" size={14} /> Salvato</span>{/if}
      </div>
    </div>

    <div class="metric-card">
      <h3><Icon name="landmark" size={16} /> Splitwise</h3>
      {#if splitwiseConfigured}
        <p class="status connected"><Icon name="check" size={14} /> Collegato</p>
        <p class="hint">Per cambiare account, disconnetti e inserisci una nuova chiave.</p>
        <button class="btn-secondary" onclick={disconnectSplitwise}>
          <Icon name="x" size={14} /> Disconnetti
        </button>
      {:else}
        <p class="status">Non configurato</p>
        <p class="hint">
          Vai su <a href="https://secure.splitwise.com/oauth_clients" target="_blank" rel="noreferrer">splitwise.com/oauth_clients</a>,
          crea una nuova app (nome e URL qualsiasi) e incolla qui l'<strong>API Key</strong>.
        </p>
        <form class="row-input" onsubmit={saveSplitwiseKey}>
          <input type="password" bind:value={splitwiseKeyInput} placeholder="API key Splitwise" />
          <button type="submit" class="btn-primary" disabled={splitwiseSaving}>
            {splitwiseSaving ? "Salvataggio..." : "Collega"}
          </button>
          {#if splitwiseSaved}<span class="saved"><Icon name="check" size={14} /> Collegato</span>{/if}
        </form>
        {#if splitwiseError}<p class="error">{splitwiseError}</p>{/if}
      {/if}
    </div>
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

  .metric-card {
    margin-bottom: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    max-width: 32rem;
  }

  .metric-card h3 {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-base);
    font-weight: 600;
    margin: 0;
  }

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0;
  }

  .hint a {
    color: var(--accent);
  }

  .status {
    font-size: var(--text-sm);
    color: var(--text-muted);
    margin: 0;
  }

  .status.connected {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--success);
    font-weight: 500;
  }

  .row-input {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .row-input input {
    flex: 1;
    min-width: 12rem;
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .btn-primary, .btn-secondary {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 0.5rem var(--space-4);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
    white-space: nowrap;
  }

  .btn-primary {
    border: none;
    background: var(--accent);
    color: var(--accent-foreground);
  }

  .btn-secondary {
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-primary);
    align-self: flex-start;
  }

  .saved {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: var(--text-xs);
    color: var(--success);
  }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
