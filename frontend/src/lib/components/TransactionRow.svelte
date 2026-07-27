<script>
  import { api } from "../api.js";

  let { tx, categories, colors, onchange } = $props();

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

<div class="row">
  <div class="main">
    <span class="date">{tx.date}</span>
    <span class="desc">
      {tx.description}
      {#if isShared}<span title="Spesa condivisa">🔀</span>{/if}
      {#if tx.note && !isShared}<span class="note-inline">— {tx.note}</span>{/if}
    </span>
    <span class="cat" style="background:{(colors[tx.category] || '#888')}22; color:{colors[tx.category] || '#888'}">
      {tx.category}
    </span>
    <span class="amount" class:negative={tx.amount < 0} class:positive={tx.amount >= 0}>
      {tx.amount < 0 ? "−" : "+"}€{Math.abs(tx.amount).toFixed(2)}
    </span>
    <div class="actions">
      <button title="Modifica" onclick={() => openAction("edit")}>✏️</button>
      <button title="Spesa condivisa" onclick={() => openAction("shared")}>🔀</button>
      <button title="Rimborso" onclick={() => openAction("reimburse")}>🔄</button>
      <button title="Elimina" onclick={() => openAction("delete")}>🗑️</button>
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
      <button type="submit">Salva modifiche</button>
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
        <button type="button" onclick={splitEqually}>🔁 Calcola quota</button>
      </label>
      <p class="hint">💡 La tua quota: <strong>€{myQuota.toFixed(2)}</strong> · Da recuperare: <strong>€{rimbFromQuota.toFixed(2)}</strong></p>
      <button type="submit">✅ Conferma e crea rimborso</button>
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
      <button type="submit">Crea rimborso</button>
    </form>
  {:else if action === "delete"}
    <div class="panel">
      <p>Eliminare questa transazione?</p>
      <button class="danger" onclick={confirmDelete}>Conferma eliminazione</button>
      <button onclick={() => (action = "")}>Annulla</button>
    </div>
  {/if}
</div>

<style>
  .row {
    background: #fff;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
  }

  .main {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .date {
    color: #888;
    font-size: 0.8rem;
    width: 6rem;
    flex-shrink: 0;
  }

  .desc {
    flex: 1;
    min-width: 0;
  }

  .note-inline {
    color: #888;
    font-size: 0.8rem;
  }

  .cat {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    flex-shrink: 0;
  }

  .amount {
    font-weight: 500;
    width: 5.5rem;
    text-align: right;
    flex-shrink: 0;
  }

  .amount.negative { color: #d85a30; }
  .amount.positive { color: #1d9e75; }

  .actions {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }

  .actions button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px 6px;
    border-radius: 6px;
    font-size: 0.9rem;
  }

  .actions button:hover {
    background: #f5f5f3;
  }

  .panel {
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid #ececea;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .panel .fields {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .panel label {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.85rem;
  }

  .panel input, .panel select {
    padding: 0.35rem 0.5rem;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 0.85rem;
  }

  .panel button[type="submit"], .panel button.danger {
    align-self: flex-start;
    padding: 0.4rem 0.9rem;
    border: none;
    border-radius: 6px;
    background: #185fa5;
    color: white;
    cursor: pointer;
    font-size: 0.85rem;
  }

  .panel button.danger {
    background: #d85a30;
  }

  .hint {
    font-size: 0.85rem;
    color: #555;
    margin: 0;
  }

  .error {
    color: #d85a30;
    font-size: 0.85rem;
  }
</style>
