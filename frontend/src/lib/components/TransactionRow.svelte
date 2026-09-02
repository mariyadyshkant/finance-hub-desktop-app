<script>
  import { api } from "../api.js";
  import Icon from "./Icon.svelte";

  let { tx, categories, colors, icons = {}, onchange } = $props();

  let action = $state("");
  let error = $state("");

  // modifica — popolati quando si apre il pannello, non alla creazione della riga
  let editDate = $state("");
  let editDesc = $state("");
  let editAmount = $state(0);
  let editCategory = $state("");
  let editNote = $state("");

  // spesa condivisa
  let totalAmt = $derived(Math.abs(tx.amount));
  let myQuota = $state(0);
  let fromPerson = $state("");
  let nPeople = $state(2);
  let rimbFromQuota = $derived(Math.round((totalAmt - myQuota) * 100) / 100);

  // rimborso diretto
  let rimbFrom = $state("");
  let rimbAmount = $state(0);
  let rimbNote = $state("");

  let isShared = $derived(tx.note && tx.note.toLowerCase().startsWith("condivisa"));
  let catColor = $derived(colors[tx.category] || "#6966a0");
  let icon = $derived(icons[tx.category] || "repeat");

  function openAction(a) {
    error = "";
    if (a === "edit") {
      editDate = tx.date;
      editDesc = tx.description;
      editAmount = tx.amount;
      editCategory = tx.category;
      editNote = tx.note || "";
    }
    if (a === "shared" && myQuota === 0) myQuota = Math.round((totalAmt / 2) * 100) / 100;
    if (a === "reimburse" && rimbAmount === 0) rimbAmount = totalAmt;
    action = action === a ? "" : a;
  }

  async function saveEdit(e) {
    e.preventDefault();
    try {
      await api.put(`/transactions/${tx.id}`, {
        date: editDate,
        description: editDesc,
        amount: Number(editAmount),
        category: editCategory,
        note: editNote,
      });
      action = "";
      onchange();
    } catch (err) {
      error = err.message;
    }
  }

  function splitEqually() {
    myQuota = Math.round((totalAmt / nPeople) * 100) / 100;
  }

  async function confirmShared(e) {
    e.preventDefault();
    if (rimbFromQuota <= 0) {
      error = "La quota da recuperare deve essere maggiore di zero.";
      return;
    }
    try {
      await api.put(`/transactions/${tx.id}`, {
        amount: -myQuota,
        note: `condivisa: pagato €${totalAmt.toFixed(2)}, mia quota €${myQuota.toFixed(2)}`,
      });
      await api.post("/reimbursements", {
        date: tx.date,
        description: tx.description,
        amount: rimbFromQuota,
        from_person: fromPerson || "da definire",
        note: `Spesa condivisa — quota mia €${myQuota.toFixed(2)} su €${totalAmt.toFixed(2)}`,
        transaction_id: tx.id,
      });
      action = "";
      onchange();
    } catch (err) {
      error = err.message;
    }
  }

  async function confirmReimburse(e) {
    e.preventDefault();
    try {
      await api.post("/reimbursements", {
        date: tx.date,
        description: tx.description,
        amount: Number(rimbAmount),
        from_person: rimbFrom,
        note: rimbNote,
        transaction_id: tx.id,
      });
      action = "";
      onchange();
    } catch (err) {
      error = err.message;
    }
  }

  async function confirmDelete() {
    try {
      await api.delete(`/transactions/${tx.id}`);
      onchange();
    } catch (err) {
      error = err.message;
    }
  }
</script>

<div class="row-wrap">
  <div class="row" style="--cat-color: {catColor}">
    <div class="icon-cell" style="color: {catColor}">
      <Icon name={icon} size={16} strokeWidth={2.2} />
    </div>

    <div class="desc-cell">
      <span class="desc">{tx.description}</span>
      {#if isShared}
        <span class="note-inline">Spesa condivisa</span>
      {:else if tx.note}
        <span class="note-inline">{tx.note}</span>
      {/if}
    </div>

    <div class="cat-cell">
      <span class="cat" style="background:{catColor}1f; color:{catColor}">{tx.category}</span>
    </div>

    <div class="date-cell">{tx.date}</div>

    <div class="amount-cell" class:income={tx.amount >= 0}>
      {tx.amount < 0 ? "−" : "+"}€{Math.abs(tx.amount).toFixed(2)}
    </div>

    <div class="actions-cell">
      <button title="Modifica" onclick={() => openAction("edit")}><Icon name="pencil" size={14} /></button>
      <button title="Spesa condivisa" onclick={() => openAction("shared")}><Icon name="arrow-left-right" size={14} /></button>
      <button title="Rimborso" onclick={() => openAction("reimburse")}><Icon name="repeat" size={14} /></button>
      <button title="Elimina" onclick={() => openAction("delete")}><Icon name="trash-2" size={14} /></button>
    </div>
  </div>

  {#if error}<p class="error">{error}</p>{/if}

  {#if action === "edit"}
    <form class="panel" onsubmit={saveEdit}>
      <div class="fields">
        <input type="date" bind:value={editDate} />
        <input type="text" bind:value={editDesc} />
        <input type="number" step="0.01" bind:value={editAmount} />
        <select bind:value={editCategory}>
          {#each categories as c}<option value={c}>{c}</option>{/each}
        </select>
        <input type="text" bind:value={editNote} placeholder="note" />
      </div>
      <button type="submit" class="primary">Salva modifiche</button>
    </form>
  {:else if action === "shared"}
    <form class="panel" onsubmit={confirmShared}>
      <p class="hint">Spesa condivisa — indica la tua quota. Importo totale pagato: €{totalAmt.toFixed(2)}</p>
      <label>
        La mia quota €
        <input type="number" step="0.01" min="0.01" max={totalAmt} bind:value={myQuota} />
      </label>
      <label>
        Chi deve restituirti la differenza?
        <input type="text" bind:value={fromPerson} placeholder="es. Marco, Giulia, coinquilini..." />
      </label>
      <label class="split">
        Oppure dividi equamente tra
        <input type="number" min="2" max="10" bind:value={nPeople} />
        persone
        <button type="button" class="ghost" onclick={splitEqually}>Calcola quota</button>
      </label>
      <p class="hint">La tua quota: <strong>€{myQuota.toFixed(2)}</strong> · Da recuperare: <strong>€{rimbFromQuota.toFixed(2)}</strong></p>
      <button type="submit" class="primary">Conferma e crea rimborso</button>
    </form>
  {:else if action === "reimburse"}
    <form class="panel" onsubmit={confirmReimburse}>
      <label>
        Da chi aspetti il rimborso?
        <input type="text" bind:value={rimbFrom} />
      </label>
      <label>
        Importo da rimborsare
        <input type="number" step="0.01" bind:value={rimbAmount} />
      </label>
      <label>
        Note
        <input type="text" bind:value={rimbNote} />
      </label>
      <button type="submit" class="primary">Crea rimborso</button>
    </form>
  {:else if action === "delete"}
    <div class="panel">
      <p>Eliminare questa transazione?</p>
      <button class="danger" onclick={confirmDelete}>Conferma eliminazione</button>
      <button class="ghost" onclick={() => (action = "")}>Annulla</button>
    </div>
  {/if}
</div>

<style>
  .row-wrap {
    border-bottom: 1px solid var(--border);
  }

  .row-wrap:last-child {
    border-bottom: none;
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-3) var(--space-5);
    transition: background 0.12s ease;
  }

  .row:hover {
    background: var(--muted);
  }

  .row:hover .actions-cell {
    opacity: 1;
  }

  .icon-cell {
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);
    background: var(--muted);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .desc-cell {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    padding: var(--space-2) 0;
  }

  .desc {
    font-size: var(--text-base);
    font-weight: 500;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: var(--space-2) 0;
  }

  .note-inline {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .cat-cell {
    width: 150px;
    text-align: center;
    flex-shrink: 0;
  }

  .cat {
    display: inline-block;
    padding: 3px 10px;
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    font-weight: 500;
  }

  .date-cell {
    width: 150px;
    text-align: center;
    font-size: var(--text-sm);
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .amount-cell {
    width: 150px;
    text-align: center;
    font-family: var(--font-heading);
    font-weight: 600;
    font-size: var(--text-base);
    color: var(--text-primary);
    flex-shrink: 0;
  }

  .amount-cell.income {
    color: var(--accent);
  }

  .actions-cell {
    width: 104px;
    display: flex;
    justify-content: flex-end;
    gap: 2px;
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.12s ease;
  }

  .actions-cell button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 5px;
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    display: flex;
  }

  .actions-cell button:hover {
    background: var(--surface);
    color: var(--accent);
  }

  .panel {
    margin: 0 var(--space-5) var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--input-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .panel .fields {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .panel label {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: var(--text-sm);
    color: var(--text-secondary);
  }

  .panel input, .panel select {
    padding: 0.35rem 0.5rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--surface);
    font-size: var(--text-sm);
  }

  .panel button.primary {
    align-self: flex-start;
    padding: 0.4rem 0.9rem;
    border: none;
    border-radius: var(--radius-sm);
    background: var(--accent);
    color: var(--accent-foreground);
    font-weight: 500;
    cursor: pointer;
    font-size: var(--text-sm);
  }

  .panel button.primary:hover {
    background: var(--accent-hover);
  }

  .panel button.ghost {
    align-self: flex-start;
    padding: 0.4rem 0.9rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--text-secondary);
    cursor: pointer;
    font-size: var(--text-sm);
  }

  .panel button.danger {
    align-self: flex-start;
    padding: 0.4rem 0.9rem;
    border: none;
    border-radius: var(--radius-sm);
    background: var(--danger);
    color: white;
    font-weight: 500;
    cursor: pointer;
    font-size: var(--text-sm);
  }

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0;
  }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
    margin: 0 var(--space-5);
  }
</style>
