<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";

  const NON_SPESA = ["Entrata", "Rimborso ricevuto", "Altro"];

  let months = $state([]);
  let summaries = $state([]);
  let categories = $state([]);
  let colors = $state({});
  let error = $state("");

  function monthLabel(m) {
    if (!m) return "";
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", { month: "long", year: "numeric" });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  async function loadAll() {
    try {
      const [m, s] = await Promise.all([api.get("/summaries/months"), api.get("/summaries")]);
      months = m;
      summaries = s;
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    api.get("/categories").then((c) => {
      categories = c.categories;
      colors = c.colors;
    });
    loadAll();
  });

  let spendableCategories = $derived(categories.filter((c) => !NON_SPESA.includes(c)));

  let monthTotals = $derived.by(() => {
    const byMonth = {};
    for (const s of summaries) byMonth[s.month] = (byMonth[s.month] || 0) + s.amount;
    return Object.entries(byMonth).sort((a, b) => b[0].localeCompare(a[0]));
  });

  // ─── Import da testo Notion ───────────────────────────────────────────────
  let importText = $state("");
  let importPreview = $state(null); // { month, categories }
  let importError = $state("");
  let parsing = $state(false);
  let importing = $state(false);

  async function parseNotionText() {
    if (!importText.trim()) return;
    parsing = true;
    importError = "";
    try {
      const res = await api.post("/summaries/parse", { text: importText });
      if (!res.month) {
        importError = "Non ho trovato un mese nel testo (riga 'Mese: ...'). Verifica il formato dell'export.";
        importPreview = null;
      } else {
        importPreview = res;
      }
    } catch (e) {
      importError = e.message;
    } finally {
      parsing = false;
    }
  }

  async function confirmImport() {
    if (!importPreview) return;
    importing = true;
    try {
      for (const [cat, amount] of Object.entries(importPreview.categories)) {
        if (!amount) continue;
        await api.post("/summaries", { month: importPreview.month, category: cat, amount: Number(amount), source: "notion" });
      }
      importText = "";
      importPreview = null;
      importError = "";
      await loadAll();
    } catch (e) {
      importError = e.message;
    } finally {
      importing = false;
    }
  }

  // ─── Inserimento manuale ──────────────────────────────────────────────────
  let manualMonth = $state(new Date().toISOString().slice(0, 7));
  let manualValues = $state({});
  let manualError = $state("");
  let manualSaving = $state(false);

  $effect(() => {
    const existing = summaries.filter((s) => s.month === manualMonth);
    const values = {};
    for (const s of existing) values[s.category] = s.amount;
    manualValues = values;
  });

  async function saveManual() {
    manualSaving = true;
    manualError = "";
    try {
      for (const cat of spendableCategories) {
        const val = manualValues[cat];
        if (val && Number(val) > 0) {
          await api.post("/summaries", { month: manualMonth, category: cat, amount: Number(val), source: "notion" });
        }
      }
      await loadAll();
    } catch (e) {
      manualError = e.message;
    } finally {
      manualSaving = false;
    }
  }

  async function deleteMonth(m) {
    try {
      await api.delete(`/summaries/${m}`);
      await loadAll();
    } catch (e) {
      error = e.message;
    }
  }
</script>

<section>
  <div class="page-header">
    <div>
      <h2>Storico Notion</h2>
      <p class="subtitle">Riepiloghi mensili importati da Notion, prima di passare a Revolut</p>
    </div>
  </div>

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else}
    <div class="metric-card">
      <h3><Icon name="upload" size={16} /> Importa export Notion</h3>
      <p class="hint">Incolla il testo del file .md esportato da Notion (deve contenere una riga "Mese: ...").</p>
      <textarea bind:value={importText} rows="6" placeholder="Incolla qui il testo dell'export..."></textarea>
      <button class="btn-secondary" onclick={parseNotionText} disabled={parsing}>
        {parsing ? "Analisi..." : "Analizza"}
      </button>
      {#if importError}<p class="error">{importError}</p>{/if}
      {#if importPreview}
        <div class="preview">
          <p class="hint">Mese riconosciuto: <strong>{monthLabel(importPreview.month)}</strong></p>
          <div class="preview-grid">
            {#each Object.entries(importPreview.categories) as [cat, amt]}
              <label>
                <span style="color:{colors[cat] || 'inherit'}">{cat}</span>
                <input type="number" step="0.01" bind:value={importPreview.categories[cat]} />
              </label>
            {/each}
          </div>
          <button class="btn-primary" onclick={confirmImport} disabled={importing}>
            {importing ? "Importazione..." : "Importa questo mese"}
          </button>
        </div>
      {/if}
    </div>

    <div class="metric-card">
      <h3>Inserimento manuale</h3>
      <p class="hint">Per mesi senza export, o per correggere valori.</p>
      <input type="month" bind:value={manualMonth} class="month-input" />
      <div class="preview-grid">
        {#each spendableCategories as cat}
          <label>
            <span style="color:{colors[cat] || 'inherit'}">{cat}</span>
            <input type="number" step="0.01" min="0" bind:value={manualValues[cat]} placeholder="0" />
          </label>
        {/each}
      </div>
      <button class="btn-primary" onclick={saveManual} disabled={manualSaving}>
        {manualSaving ? "Salvataggio..." : `Salva ${monthLabel(manualMonth)}`}
      </button>
      {#if manualError}<p class="error">{manualError}</p>{/if}
    </div>

    <div class="metric-card">
      <h3>Mesi importati</h3>
      {#if monthTotals.length === 0}
        <p class="hint">Nessun mese importato ancora.</p>
      {:else}
        <div class="list">
          {#each monthTotals as [m, total]}
            <div class="row">
              <span class="date">{monthLabel(m)}</span>
              <span class="desc">totale spese €{total.toFixed(2)}</span>
              <button class="icon-btn" title="Elimina mese" onclick={() => deleteMonth(m)}>
                <Icon name="trash-2" size={14} />
              </button>
            </div>
          {/each}
        </div>
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

  textarea {
    width: 100%;
    padding: var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
    font-family: inherit;
    resize: vertical;
  }

  .month-input {
    align-self: flex-start;
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .btn-primary, .btn-secondary {
    align-self: flex-start;
    padding: 0.5rem var(--space-4);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
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
  }

  .preview {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding-top: var(--space-2);
    border-top: 1px solid var(--border);
  }

  .preview-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-2) var(--space-4);
  }

  .preview-grid label {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    font-size: var(--text-sm);
  }

  .preview-grid input {
    width: 6rem;
    padding: 0.3rem var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
    text-align: right;
  }

  .list {
    display: flex;
    flex-direction: column;
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--border);
    font-size: var(--text-sm);
  }

  .row:last-child { border-bottom: none; }

  .row .date {
    width: 10rem;
    flex-shrink: 0;
    font-weight: 500;
    color: var(--text-primary);
  }

  .row .desc {
    flex: 1;
    color: var(--text-secondary);
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
    color: var(--danger);
  }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
