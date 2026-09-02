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

  // ─── Categorie ────────────────────────────────────────────────────────────
  let cats = $state([]); // [{ name, color }]
  let catError = $state("");
  let newCatName = $state("");
  let newCatColor = $state("#0e7490");
  let editingCat = $state(null); // nome originale in modifica
  let editCatName = $state("");
  let editCatColor = $state("");
  let deletingCat = $state(null); // nome in attesa di conferma eliminazione
  let reassignTo = $state("");

  async function load() {
    try {
      const [s, c] = await Promise.all([api.get("/settings"), api.get("/categories")]);
      displayName = s.display_name || "";
      splitwiseConfigured = s.splitwise_configured;
      cats = c.categories.map((n) => ({ name: n, color: c.colors[n] || "#0e7490" }));
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  async function addCat(e) {
    e.preventDefault();
    if (!newCatName.trim()) {
      catError = "Inserisci un nome.";
      return;
    }
    try {
      await api.post("/categories", { name: newCatName.trim(), color: newCatColor });
      newCatName = "";
      newCatColor = "#0e7490";
      catError = "";
      await load();
    } catch (e2) {
      catError = e2.message;
    }
  }

  function startEditCat(c) {
    editingCat = c.name;
    editCatName = c.name;
    editCatColor = c.color;
    deletingCat = null;
  }

  async function saveCat(orig) {
    try {
      await api.put(`/categories/${encodeURIComponent(orig)}`, {
        name: editCatName.trim(),
        color: editCatColor,
      });
      editingCat = null;
      catError = "";
      await load();
    } catch (e) {
      catError = e.message;
    }
  }

  function startDeleteCat(c) {
    deletingCat = c.name;
    editingCat = null;
    reassignTo = (cats.find((x) => x.name !== c.name) || {}).name || "";
  }

  async function confirmDeleteCat() {
    if (!reassignTo) {
      catError = "Scegli una categoria di destinazione.";
      return;
    }
    try {
      await api.delete(
        `/categories/${encodeURIComponent(deletingCat)}?reassign_to=${encodeURIComponent(reassignTo)}`
      );
      deletingCat = null;
      catError = "";
      await load();
    } catch (e) {
      catError = e.message;
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

    <div class="metric-card wide">
      <h3><Icon name="pie-chart" size={16} /> Categorie</h3>
      <p class="hint">
        Aggiungi, rinomina o elimina le categorie di spesa. Rinominare aggiorna anche
        le transazioni esistenti; eliminando ne scegli la categoria di destinazione.
      </p>

      <div class="cat-list">
        {#each cats as c (c.name)}
          {#if editingCat === c.name}
            <div class="cat-row editing">
              <input type="color" bind:value={editCatColor} class="swatch" />
              <input type="text" bind:value={editCatName} class="cat-name-input" />
              <button class="btn-primary sm" onclick={() => saveCat(c.name)}>
                <Icon name="check" size={14} /> Salva
              </button>
              <button class="btn-secondary sm" onclick={() => (editingCat = null)}>Annulla</button>
            </div>
          {:else if deletingCat === c.name}
            <div class="cat-row deleting">
              <span class="swatch static" style="background:{c.color}"></span>
              <span class="cat-name">Elimina «{c.name}» — sposta le voci su</span>
              <select bind:value={reassignTo}>
                {#each cats.filter((x) => x.name !== c.name) as opt}
                  <option value={opt.name}>{opt.name}</option>
                {/each}
              </select>
              <button class="btn-danger sm" onclick={confirmDeleteCat}>
                <Icon name="trash-2" size={14} /> Elimina
              </button>
              <button class="btn-secondary sm" onclick={() => (deletingCat = null)}>Annulla</button>
            </div>
          {:else}
            <div class="cat-row">
              <span class="swatch static" style="background:{c.color}"></span>
              <span class="cat-name">{c.name}</span>
              <button class="icon-btn" title="Modifica" onclick={() => startEditCat(c)}>
                <Icon name="pencil" size={14} />
              </button>
              <button
                class="icon-btn"
                title="Elimina"
                disabled={cats.length <= 1}
                onclick={() => startDeleteCat(c)}
              >
                <Icon name="trash-2" size={14} />
              </button>
            </div>
          {/if}
        {/each}
      </div>

      <form class="cat-add" onsubmit={addCat}>
        <input type="color" bind:value={newCatColor} class="swatch" />
        <input type="text" bind:value={newCatName} placeholder="Nuova categoria" />
        <button type="submit" class="btn-primary sm"><Icon name="plus" size={14} /> Aggiungi</button>
      </form>
      {#if catError}<p class="error">{catError}</p>{/if}
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

  .metric-card.wide {
    max-width: 44rem;
  }

  .cat-list {
    display: flex;
    flex-direction: column;
  }

  .cat-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--border);
    font-size: var(--text-sm);
    flex-wrap: wrap;
  }

  .cat-row:last-child {
    border-bottom: none;
  }

  .cat-name {
    flex: 1;
    color: var(--text-primary);
  }

  .swatch {
    width: 22px;
    height: 22px;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: none;
    cursor: pointer;
    flex-shrink: 0;
  }

  .swatch.static {
    display: inline-block;
    border-radius: 999px;
  }

  .cat-name-input,
  .cat-row select {
    padding: 0.35rem var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .cat-name-input {
    flex: 1;
    min-width: 8rem;
  }

  .cat-add {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-top: var(--space-3);
    flex-wrap: wrap;
  }

  .cat-add input[type="text"] {
    flex: 1;
    min-width: 10rem;
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .icon-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 5px;
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    display: flex;
  }

  .icon-btn:hover {
    background: var(--muted);
    color: var(--accent);
  }

  .icon-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .btn-primary.sm,
  .btn-secondary.sm,
  .btn-danger.sm {
    padding: 0.35rem var(--space-3);
    font-size: var(--text-xs);
  }

  .btn-danger {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    border: none;
    border-radius: var(--radius-md);
    background: var(--danger);
    color: white;
    font-weight: 500;
    cursor: pointer;
  }
</style>
