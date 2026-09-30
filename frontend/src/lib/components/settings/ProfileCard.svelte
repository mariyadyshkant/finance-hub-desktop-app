<script>
  import { api } from "../../api.js";
  import Icon from "../Icon.svelte";

  let { displayName = $bindable(""), onerror } = $props();

  let nameSaving = $state(false);
  let nameSaved = $state(false);

  async function saveName() {
    nameSaving = true;
    nameSaved = false;
    try {
      await api.post("/settings/profile", { display_name: displayName });
      nameSaved = true;
      setTimeout(() => (nameSaved = false), 2000);
    } catch (e) {
      onerror(e.message);
    } finally {
      nameSaving = false;
    }
  }
</script>

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

<style>
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

  .btn-primary {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 0.5rem var(--space-4);
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
    white-space: nowrap;
    border: none;
    background: var(--accent);
    color: var(--accent-foreground);
  }

  .saved {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: var(--text-xs);
    color: var(--success);
  }
</style>
