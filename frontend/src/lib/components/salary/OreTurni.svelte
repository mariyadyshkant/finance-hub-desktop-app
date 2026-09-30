<script>
  import { api } from "../../api.js";
  import Icon from "../Icon.svelte";
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";

  let { shifts, monthLabel, onchange, onerror } = $props();

  let noteText = $state("");
  let parsedShifts = $state([]);
  let parseError = $state("");
  let parsing = $state(false);

  let shiftMonths = $derived(
    Array.from(new Set(shifts.map((s) => s.date.slice(0, 7)))).sort().reverse()
  );
  let selectedOreMonth = $state("");
  $effect(() => {
    if (!selectedOreMonth && shiftMonths.length) selectedOreMonth = shiftMonths[0];
  });

  let monthShifts = $derived(
    shifts.filter((s) => s.date.slice(0, 7) === selectedOreMonth).sort((a, b) => a.date.localeCompare(b.date))
  );
  let totHoursMonth = $derived(monthShifts.reduce((s, x) => s + x.hours, 0));
  let nShiftsMonth = $derived(monthShifts.length);
  let avgPerShift = $derived(nShiftsMonth ? totHoursMonth / nShiftsMonth : 0);

  let hoursChartData = $derived({
    labels: monthShifts.map((s) => new Date(s.date + "T00:00:00").toLocaleDateString("it-IT", { day: "2-digit", month: "short" })),
    datasets: [
      {
        data: monthShifts.map((s) => s.hours),
        backgroundColor: CHART_COLORS.accent,
        borderRadius: 4,
        maxBarThickness: 24,
      },
    ],
  });
  const hoursChartOptions = {
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y}h` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `${v}h` } } }),
  };

  async function parseNoteText() {
    if (!noteText.trim()) return;
    parsing = true;
    parseError = "";
    try {
      const res = await api.post("/shifts/parse", { text: noteText });
      parsedShifts = res.shifts || [];
      if (parsedShifts.length === 0) parseError = "Nessun turno riconosciuto nel testo.";
    } catch (e) {
      parseError = e.message;
    } finally {
      parsing = false;
    }
  }

  async function importParsedShifts() {
    try {
      await api.post("/shifts/import", parsedShifts);
      parsedShifts = [];
      noteText = "";
      await onchange();
    } catch (e) {
      parseError = e.message;
    }
  }

  let addDate = $state(new Date().toISOString().slice(0, 10));
  let addStart = $state("");
  let addEnd = $state("");
  let addNote = $state("");
  let addShiftError = $state("");
  let showAddShift = $state(false);

  function computeHours(start, end) {
    if (!start || !end) return 0;
    const parseTime = (s) => {
      s = s.trim();
      if (!s.includes(":")) s = s + ":00";
      const [h, m] = s.split(":").map(Number);
      return h * 60 + (m || 0);
    };
    let diff = parseTime(end) - parseTime(start);
    if (diff < 0) diff += 24 * 60;
    return Math.round((diff / 60) * 100) / 100;
  }

  async function submitAddShift(e) {
    e.preventDefault();
    const hours = computeHours(addStart, addEnd);
    if (hours <= 0) {
      addShiftError = "Orario di inizio/fine non valido.";
      return;
    }
    try {
      await api.post("/shifts", { date: addDate, hours, start_time: addStart, end_time: addEnd, note: addNote });
      addStart = "";
      addEnd = "";
      addNote = "";
      addShiftError = "";
      showAddShift = false;
      await onchange();
    } catch (e2) {
      addShiftError = e2.message;
    }
  }

  async function deleteShift(id) {
    try {
      await api.delete(`/shifts/${id}`);
      await onchange();
    } catch (e) {
      onerror(e.message);
    }
  }
</script>

<div class="toolbar">
  <button class="btn-secondary" onclick={() => (showAddShift = !showAddShift)}>
    <Icon name="plus" size={14} /> Aggiungi turno
  </button>
</div>

{#if showAddShift}
  <form class="add-panel" onsubmit={submitAddShift}>
    <div class="fields">
      <input type="date" bind:value={addDate} />
      <input type="text" bind:value={addStart} placeholder="Inizio (es. 17:30)" />
      <input type="text" bind:value={addEnd} placeholder="Fine (es. 22:00)" />
      <input type="text" bind:value={addNote} placeholder="Note (opzionale)" />
    </div>
    <button type="submit" class="btn-primary">Salva turno</button>
    {#if addShiftError}<p class="error">{addShiftError}</p>{/if}
  </form>
{/if}

<div class="metric-card import-panel">
  <h3>Importa da Note Apple</h3>
  <p class="hint">Incolla il testo copiato dalla nota con i turni (formati supportati: "1. 05/05 17:31-20:16 (2 ore e 45)", "10.01 21:15-01:45", ecc.)</p>
  <textarea bind:value={noteText} rows="4" placeholder="Incolla qui..."></textarea>
  <button class="btn-secondary" onclick={parseNoteText} disabled={parsing}>
    {parsing ? "Analisi..." : "Analizza testo"}
  </button>
  {#if parseError}<p class="error">{parseError}</p>{/if}
  {#if parsedShifts.length > 0}
    <p class="hint">Trovati <strong>{parsedShifts.length}</strong> turni:</p>
    <ul class="preview-list">
      {#each parsedShifts as p}
        <li>{p.date} · {p.start_time}–{p.end_time} · {p.hours}h</li>
      {/each}
    </ul>
    <button class="btn-primary" onclick={importParsedShifts}>Importa tutti</button>
  {/if}
</div>

{#if shiftMonths.length > 0}
  <div class="toolbar">
    <select bind:value={selectedOreMonth}>
      {#each shiftMonths as m}<option value={m}>{monthLabel(m)}</option>{/each}
    </select>
  </div>

  <div class="kpi-grid three">
    <div class="metric-card">
      <span class="eyebrow">Ore totali</span>
      <span class="kpi-value">{totHoursMonth.toFixed(1)}h</span>
    </div>
    <div class="metric-card">
      <span class="eyebrow">Turni</span>
      <span class="kpi-value">{nShiftsMonth}</span>
    </div>
    <div class="metric-card">
      <span class="eyebrow">Media a turno</span>
      <span class="kpi-value">{avgPerShift.toFixed(1)}h</span>
    </div>
  </div>

  <div class="metric-card chart-card">
    <h3>Ore per giorno — {monthLabel(selectedOreMonth)}</h3>
    <Chart type="bar" data={hoursChartData} options={hoursChartOptions} height={240} />
  </div>

  <div class="metric-card">
    <h3>Turni del mese</h3>
    <div class="list">
      {#each monthShifts as s (s.id)}
        <div class="row">
          <span class="date">{s.date}</span>
          <span class="desc">{s.start_time || "?"}–{s.end_time || "?"}{s.note ? ` · ${s.note}` : ""}</span>
          <span class="hours">{s.hours}h</span>
          <button class="icon-btn" title="Elimina" onclick={() => deleteShift(s.id)}>
            <Icon name="trash-2" size={14} />
          </button>
        </div>
      {/each}
    </div>
  </div>
{:else}
  <p class="hint">Nessun turno registrato ancora.</p>
{/if}

<style>
  .toolbar {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .toolbar select {
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
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

  .add-panel, .import-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    margin-bottom: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .add-panel .fields {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .add-panel input, .import-panel textarea {
    padding: 0.5rem var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--input-bg);
    font-size: var(--text-sm);
    font-family: inherit;
  }

  .import-panel textarea {
    width: 100%;
    resize: vertical;
  }

  .preview-list {
    margin: 0;
    padding-left: 1.2rem;
    font-size: var(--text-sm);
    color: var(--text-secondary);
  }

  .kpi-grid {
    display: grid;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .kpi-grid.three {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .kpi-grid .metric-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .kpi-value {
    font-family: var(--font-heading);
    font-size: var(--text-xl);
    font-weight: 700;
    color: var(--text-primary);
  }

  .chart-card {
    margin-bottom: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .chart-card h3, .metric-card > h3 {
    font-size: var(--text-base);
    font-weight: 600;
    margin: 0 0 var(--space-2);
  }

  .metric-card {
    margin-bottom: var(--space-4);
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
    color: var(--text-muted);
    font-size: var(--text-xs);
    width: 7rem;
    flex-shrink: 0;
  }

  .row .desc {
    flex: 1;
    color: var(--text-primary);
  }

  .row .hours {
    font-family: var(--font-heading);
    font-weight: 600;
    color: var(--text-primary);
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

  .hint {
    font-size: var(--text-sm);
    color: var(--text-secondary);
  }

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
