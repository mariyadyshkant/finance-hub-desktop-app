<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";
  import { plannedApplies } from "../lib/planned.js";
  import ImportRevolut from "../lib/components/dashboard/ImportRevolut.svelte";
  import KpiRow from "../lib/components/dashboard/KpiRow.svelte";
  import CategoryBreakdownChart from "../lib/components/dashboard/CategoryBreakdownChart.svelte";
  import DailyTrendChart from "../lib/components/dashboard/DailyTrendChart.svelte";
  import ConfrontoMensileChart from "../lib/components/dashboard/ConfrontoMensileChart.svelte";
  import AndamentoCategoriaChart from "../lib/components/dashboard/AndamentoCategoriaChart.svelte";
  import MediaMensileChart from "../lib/components/dashboard/MediaMensileChart.svelte";

  const NON_SPESA = ["Entrata", "Rimborso ricevuto", "Altro"];
  // Sottoinsieme di NON_SPESA che non è mai una spesa in nessun contesto (a
  // differenza di "Altro", che è una categoria di spesa a tutti gli effetti —
  // è solo nascosta dai chip di filtro). Usato per escludere entrate/rimborsi
  // dai grafici "per categoria": l'aggregazione Revolut/Telegram li esclude
  // già guardando il segno dell'importo, ma un'entrata salvata per errore con
  // segno negativo (successo una volta col bot) altrimenti ci finirebbe dentro
  // comunque — qui si esclude per categoria, non per segno, così l'invariante
  // "niente Entrata/Rimborso nei grafici di spesa" non dipende dai dati.
  const NON_SPESA_CATEGORIE = ["Entrata", "Rimborso ricevuto"];

  let allTx = $state([]);
  let notionSummaries = $state([]);
  let revolutMonths = $state([]);
  let notionMonths = $state([]);
  let categories = $state([]);
  let colors = $state({});
  let selectedMonth = $state("");
  let error = $state("");

  // Spese pianificate (lista base + override del mese) — non entrano nella
  // lista transazioni, ma vanno conteggiate accanto al totale speso del mese.
  let plannedExpenses = $state([]);
  let plannedOverrides = $state({});

  let showImport = $state(false);

  function monthLabel(m) {
    if (!m) return "";
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", {
      month: "long",
      year: "numeric",
    });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  function monthLabelShort(m) {
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", {
      month: "short",
      year: "2-digit",
    });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  async function loadAll() {
    try {
      const [tx, summaries, rMonths, nMonths, planned] = await Promise.all([
        api.get("/transactions"),
        api.get("/summaries"),
        api.get("/transactions/months"),
        api.get("/summaries/months"),
        api.get("/planning/planned-expenses"),
      ]);
      allTx = tx;
      notionSummaries = summaries;
      revolutMonths = rMonths;
      notionMonths = nMonths;
      plannedExpenses = planned;
      error = "";
      if (!selectedMonth) {
        const all = Array.from(new Set([...rMonths, ...nMonths])).sort().reverse();
        if (all.length) selectedMonth = all[0];
      }
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

  $effect(() => {
    if (!selectedMonth) return;
    api
      .get(`/planning/overrides/${selectedMonth}`)
      .then((o) => (plannedOverrides = o))
      .catch(() => (plannedOverrides = {}));
  });

  let allMonths = $derived(
    Array.from(new Set([...revolutMonths, ...notionMonths])).sort().reverse()
  );

  let spendableCategories = $derived(categories.filter((c) => !NON_SPESA.includes(c)));

  // righe unificate: {month, category, amount (spesa, positivo), source}
  let unifiedRows = $derived.by(() => {
    const rows = [];
    for (const r of notionSummaries) {
      if (NON_SPESA_CATEGORIE.includes(r.category)) continue;
      rows.push({ month: r.month, category: r.category, amount: r.amount, source: "notion" });
    }
    const agg = {};
    for (const tx of allTx) {
      if (tx.amount >= 0) continue;
      if (NON_SPESA_CATEGORIE.includes(tx.category)) continue;
      const month = tx.date.slice(0, 7);
      const key = month + "||" + tx.category;
      if (!agg[key]) agg[key] = { month, category: tx.category, amount: 0, source: "revolut" };
      agg[key].amount += Math.abs(tx.amount);
    }
    rows.push(...Object.values(agg));
    return rows;
  });

  // Le spese pianificate del mese selezionato, nella stessa forma delle righe
  // unificate — così entrano in ogni calcolo e grafico del mese (tranne
  // l'andamento giornaliero, che non hanno una data). Rappresentano spesa
  // attesa non ancora a estratto conto: si sommano solo al mese selezionato,
  // non retroattivamente agli altri mesi del confronto.
  let plannedMonthRows = $derived(
    plannedApplies(selectedMonth)
      ? plannedExpenses.map((p) => ({
          month: selectedMonth,
          category: p.category,
          amount: plannedOverrides[p.id]?.amount ?? p.amount,
          source: "planned",
        }))
      : []
  );

  let rowsWithPlanned = $derived([...unifiedRows, ...plannedMonthRows]);

  let monthRows = $derived(rowsWithPlanned.filter((r) => r.month === selectedMonth));
  let isRevolutMonth = $derived(revolutMonths.includes(selectedMonth));
</script>

<section>
  <div class="page-header">
    <div>
      <h2>Dashboard</h2>
      <p class="subtitle">Panoramica mensile</p>
    </div>
    <button class="btn-secondary" onclick={() => (showImport = !showImport)}>
      <Icon name="file-text" size={14} />
      Importa estratto Revolut
    </button>
  </div>

  {#if showImport}
    <ImportRevolut onImported={async () => { await loadAll(); showImport = false; }} />
  {/if}

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if allMonths.length === 0}
    <p class="hint">Nessun dato ancora. Importa un estratto Revolut o aggiungi mesi storici da Notion.</p>
  {:else}
    <div class="toolbar">
      <select bind:value={selectedMonth}>
        {#each allMonths as m}<option value={m}>{monthLabel(m)}</option>{/each}
      </select>
      <span class="source-badge">
        {#if isRevolutMonth && notionMonths.includes(selectedMonth)}
          Dati da: Revolut + Notion
        {:else if isRevolutMonth}
          Dati da: Revolut
        {:else}
          Dati da: Notion (riepilogo mensile)
        {/if}
      </span>
    </div>

    <KpiRow {monthRows} {allTx} {selectedMonth} {isRevolutMonth} />

    <div class="charts-row" class:single={!isRevolutMonth}>
      <CategoryBreakdownChart {monthRows} {colors} />
      <DailyTrendChart {allTx} {selectedMonth} {isRevolutMonth} />
    </div>

    <ConfrontoMensileChart {rowsWithPlanned} {revolutMonths} {monthLabelShort} />

    <AndamentoCategoriaChart {rowsWithPlanned} {allMonths} {spendableCategories} {colors} {monthLabelShort} />

    <MediaMensileChart {rowsWithPlanned} {allMonths} {selectedMonth} {monthLabel} />
  {/if}
</section>

<style>
  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-6);
    margin-bottom: var(--space-5);
  }

  .subtitle {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 4px 0 0;
  }

  .btn-secondary {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 0.5rem var(--space-4);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface);
    color: var(--text-primary);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
  }

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 0;
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin-bottom: var(--space-5);
  }

  .toolbar select {
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--input-bg);
    font-size: var(--text-sm);
  }

  .source-badge {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .charts-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-4);
    margin-bottom: var(--space-4);
  }

  .charts-row.single {
    grid-template-columns: 1fr;
  }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
