<script>
  import { api } from "../../api.js";
  import Icon from "../Icon.svelte";
  import { PICKABLE_ICONS, iconMatches } from "../../icons.js";

  let { cats, onchange } = $props();

  let iconQuery = $state("");
  let filteredIcons = $derived(PICKABLE_ICONS.filter((n) => iconMatches(n, iconQuery)));

  let catError = $state("");
  let newCatName = $state("");
  let newCatColor = $state("#0e7490");
  let newCatIcon = $state("repeat");
  let newIconPickerOpen = $state(false);
  let editingCat = $state(null); // nome originale in modifica
  let editCatName = $state("");
  let editCatColor = $state("");
  let editCatIcon = $state("repeat");
  let editIconPickerOpen = $state(false);
  let deletingCat = $state(null); // nome in attesa di conferma eliminazione
  let reassignTo = $state("");

  async function addCat(e) {
    e.preventDefault();
    if (!newCatName.trim()) {
      catError = "Inserisci un nome.";
      return;
    }
    try {
      await api.post("/categories", {
        name: newCatName.trim(),
        color: newCatColor,
        icon: newCatIcon,
      });
      newCatName = "";
      newCatColor = "#0e7490";
      newCatIcon = "repeat";
      newIconPickerOpen = false;
      catError = "";
      await onchange();
    } catch (e2) {
      catError = e2.message;
    }
  }

  function startEditCat(c) {
    editingCat = c.name;
    editCatName = c.name;
    editCatColor = c.color;
    editCatIcon = c.icon;
    editIconPickerOpen = false;
    deletingCat = null;
  }

  async function saveCat(orig) {
    try {
      await api.put(`/categories/${encodeURIComponent(orig)}`, {
        name: editCatName.trim(),
        color: editCatColor,
        icon: editCatIcon,
      });
      editingCat = null;
      catError = "";
      await onchange();
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
      await onchange();
    } catch (e) {
      catError = e.message;
    }
  }
</script>

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
          <div class="cat-row-main">
            <input type="color" bind:value={editCatColor} class="swatch" title="Colore" />
            <button
              type="button"
              class="icon-preview"
              style="color:{editCatColor}"
              title="Cambia icona"
              onclick={() => {
                editIconPickerOpen = !editIconPickerOpen;
                iconQuery = "";
              }}
            >
              <Icon name={editCatIcon} size={16} />
            </button>
            <input type="text" bind:value={editCatName} class="cat-name-input" />
            <button class="btn-primary sm" onclick={() => saveCat(c.name)}>
              <Icon name="check" size={14} /> Salva
            </button>
            <button class="btn-secondary sm" onclick={() => (editingCat = null)}>Annulla</button>
          </div>
          {#if editIconPickerOpen}
            <div class="icon-picker">
              <input class="icon-search" type="text" placeholder="Cerca icona…" bind:value={iconQuery} />
              <div class="icon-grid">
                {#each filteredIcons as ic (ic)}
                  <button
                    type="button"
                    class="icon-choice"
                    class:selected={editCatIcon === ic}
                    title={ic}
                    onclick={() => {
                      editCatIcon = ic;
                      editIconPickerOpen = false;
                    }}
                  >
                    <Icon name={ic} size={16} />
                  </button>
                {/each}
                {#if filteredIcons.length === 0}<span class="icon-empty">Nessuna icona</span>{/if}
              </div>
            </div>
          {/if}
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
          <span class="icon-preview static" style="color:{c.color}">
            <Icon name={c.icon} size={16} />
          </span>
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
    <div class="cat-row-main">
      <input type="color" bind:value={newCatColor} class="swatch" title="Colore" />
      <button
        type="button"
        class="icon-preview"
        style="color:{newCatColor}"
        title="Scegli icona"
        onclick={() => {
          newIconPickerOpen = !newIconPickerOpen;
          iconQuery = "";
        }}
      >
        <Icon name={newCatIcon} size={16} />
      </button>
      <input type="text" bind:value={newCatName} placeholder="Nuova categoria" />
      <button type="submit" class="btn-primary sm"><Icon name="plus" size={14} /> Aggiungi</button>
    </div>
    {#if newIconPickerOpen}
      <div class="icon-picker">
        <input class="icon-search" type="text" placeholder="Cerca icona…" bind:value={iconQuery} />
        <div class="icon-grid">
          {#each filteredIcons as ic (ic)}
            <button
              type="button"
              class="icon-choice"
              class:selected={newCatIcon === ic}
              title={ic}
              onclick={() => {
                newCatIcon = ic;
                newIconPickerOpen = false;
              }}
            >
              <Icon name={ic} size={16} />
            </button>
          {/each}
          {#if filteredIcons.length === 0}<span class="icon-empty">Nessuna icona</span>{/if}
        </div>
      </div>
    {/if}
  </form>
  {#if catError}<p class="error">{catError}</p>{/if}
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

  .cat-row.editing {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-2);
  }

  .cat-row-main {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    flex-wrap: wrap;
  }

  .cat-name {
    flex: 1;
    color: var(--text-primary);
  }

  .icon-preview {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--surface);
    cursor: pointer;
    flex-shrink: 0;
  }

  .icon-preview.static {
    border-color: transparent;
    background: none;
    cursor: default;
  }

  .icon-picker {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .icon-search {
    padding: 0.4rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .icon-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(30px, 1fr));
    gap: 4px;
    max-height: 220px;
    overflow-y: auto;
    padding: var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
  }

  .icon-empty {
    grid-column: 1 / -1;
    padding: var(--space-2);
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .icon-choice {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 30px;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    background: none;
    color: var(--text-secondary);
    cursor: pointer;
  }

  .icon-choice:hover {
    background: var(--muted);
    color: var(--accent);
  }

  .icon-choice.selected {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--muted);
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
    flex-direction: column;
    gap: var(--space-2);
    margin-top: var(--space-3);
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
