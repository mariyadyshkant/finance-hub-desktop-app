<script>
  import { api, apiBaseUrl } from "../../api.js";

  let { onImported } = $props();

  let importRecords = $state([]);
  let importError = $state("");
  let importBusy = $state(false);

  async function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    importBusy = true;
    importError = "";
    try {
      const formData = new FormData();
      formData.append("file", file);
      const base = await apiBaseUrl();
      const res = await fetch(`${base}/api/transactions/parse-revolut`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      importRecords = data.records || [];
      if (importRecords.length === 0) importError = "Nessuna transazione trovata nel file.";
    } catch (err) {
      importError = err.message;
      importRecords = [];
    } finally {
      importBusy = false;
    }
  }

  async function confirmImport() {
    try {
      await api.post("/transactions/import", importRecords);
      importRecords = [];
      await onImported();
    } catch (err) {
      importError = err.message;
    }
  }

  let importSpese = $derived(
    importRecords.filter((r) => r.amount < 0).reduce((s, r) => s + Math.abs(r.amount), 0)
  );
  let importEntrate = $derived(
    importRecords.filter((r) => r.amount > 0).reduce((s, r) => s + r.amount, 0)
  );
</script>

<div class="import-panel">
  <p class="hint">Carica il PDF (estratto conto) o il CSV esportato da Revolut.</p>
  <input type="file" accept=".pdf,.csv" onchange={handleFileSelect} />
  {#if importBusy}<p class="hint">Analisi in corso...</p>{/if}
  {#if importError}<p class="error">{importError}</p>{/if}
  {#if importRecords.length > 0}
    <p class="hint">
      Trovate <strong>{importRecords.length}</strong> transazioni — spese €{importSpese.toFixed(2)}, entrate €{importEntrate.toFixed(2)}
    </p>
    <button class="btn-primary" onclick={confirmImport}>Importa tutto nel database</button>
  {/if}
</div>

<style>
  .btn-primary {
    padding: 0.5rem var(--space-4);
    border: none;
    border-radius: var(--radius-md);
    background: var(--accent);
    color: var(--accent-foreground);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
  }

  .import-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    margin-bottom: var(--space-5);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0;
  }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
