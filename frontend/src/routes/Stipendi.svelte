<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";
  import Chart from "../lib/components/Chart.svelte";
  import { CHART_COLORS, baseScales } from "../lib/chartTheme.js";

  let activeTab = $state("ore");
  let shifts = $state([]);
  let salaryRecords = $state([]);
  let error = $state("");

  function monthLabel(m) {
    if (!m) return "";
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", { month: "long", year: "numeric" });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  function monthLabelShort(m) {
    const label = new Date(`${m}-01T00:00:00`).toLocaleDateString("it-IT", { month: "short", year: "2-digit" });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  async function loadAll() {
    try {
      const [s, sal] = await Promise.all([api.get("/shifts"), api.get("/salary")]);
      shifts = s;
      salaryRecords = sal;
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    loadAll();
  });

  // ─── Ore & Turni ──────────────────────────────────────────────────────────
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
      await loadAll();
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
      await loadAll();
    } catch (e2) {
      addShiftError = e2.message;
    }
  }

  async function deleteShift(id) {
    try {
      await api.delete(`/shifts/${id}`);
      await loadAll();
    } catch (e) {
      error = e.message;
    }
  }

  // ─── Stipendi ─────────────────────────────────────────────────────────────
  let addSalMonth = $state(new Date().toISOString().slice(0, 7));
  let addSalNet = $state("");
  let addSalGross = $state("");
  let addSalHours = $state("");
  let addSalNote = $state("");
  let addSalError = $state("");
  let showAddSalary = $state(false);

  let salarySorted = $derived(salaryRecords.slice().sort((a, b) => b.month.localeCompare(a.month)));
  let netValues = $derived(salaryRecords.map((s) => s.net));
  let avgNet = $derived(netValues.length ? netValues.reduce((s, v) => s + v, 0) / netValues.length : 0);
  let maxNet = $derived(netValues.length ? Math.max(...netValues) : 0);
  let minNet = $derived(netValues.length ? Math.min(...netValues) : 0);

  let salaryChartData = $derived({
    labels: salarySorted.slice().reverse().map((s) => monthLabelShort(s.month)),
    datasets: [
      {
        label: "Netto",
        data: salarySorted.slice().reverse().map((s) => s.net),
        backgroundColor: CHART_COLORS.accent,
        borderRadius: 4,
        maxBarThickness: 28,
      },
    ],
  });
  const salaryChartOptions = {
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `€${ctx.parsed.y.toFixed(2)}` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };

  async function submitAddSalary(e) {
    e.preventDefault();
    if (!addSalMonth || !addSalNet) {
      addSalError = "Mese e netto sono obbligatori.";
      return;
    }
    try {
      await api.post("/salary", {
        month: addSalMonth,
        net: Number(addSalNet),
        gross: addSalGross ? Number(addSalGross) : null,
        hours_worked: addSalHours ? Number(addSalHours) : null,
        note: addSalNote,
      });
      addSalNet = "";
      addSalGross = "";
      addSalHours = "";
      addSalNote = "";
      addSalError = "";
      showAddSalary = false;
      await loadAll();
    } catch (e2) {
      addSalError = e2.message;
    }
  }

  async function deleteSalary(id) {
    try {
      await api.delete(`/salary/${id}`);
      await loadAll();
    } catch (e) {
      error = e.message;
    }
  }

  // ─── Previsione ───────────────────────────────────────────────────────────
  let validSalary = $derived(
    salaryRecords
      .filter((s) => s.hours_worked && s.hours_worked > 0)
      .slice()
      .sort((a, b) => a.month.localeCompare(b.month))
  );

  let weightedRate = $derived.by(() => {
    if (validSalary.length === 0) return 0;
    let sumW = 0;
    let sumWR = 0;
    validSalary.forEach((s, i) => {
      const w = i + 1;
      const rate = s.net / s.hours_worked;
      sumW += w;
      sumWR += w * rate;
    });
    return sumWR / sumW;
  });

  let rateChartData = $derived({
    labels: validSalary.map((s) => monthLabelShort(s.month)),
    datasets: [
      {
        label: "Tariffa oraria",
        data: validSalary.map((s) => s.net / s.hours_worked),
        borderColor: CHART_COLORS.accent,
        backgroundColor: CHART_COLORS.accent,
        tension: 0.3,
        pointRadius: 3,
      },
      {
        label: "Media pesata",
        data: validSalary.map(() => weightedRate),
        borderColor: CHART_COLORS.textMuted,
        borderDash: [6, 4],
        pointRadius: 0,
        borderWidth: 1.5,
      },
    ],
  });
  const rateChartOptions = {
    plugins: {
      legend: { position: "bottom", labels: { color: CHART_COLORS.textSecondary } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: €${ctx.parsed.y.toFixed(2)}/h` } },
    },
    scales: baseScales({ y: { ticks: { callback: (v) => `€${v}` } } }),
  };

  let salaryMonthSet = $derived(new Set(salaryRecords.map((s) => s.month)));
  let forecastRows = $derived.by(() => {
    return shiftMonths
      .filter((m) => !salaryMonthSet.has(m))
      .map((m) => {
        const hours = shifts.filter((s) => s.date.slice(0, 7) === m).reduce((s, x) => s + x.hours, 0);
        return { month: m, hours, forecast: hours * weightedRate };
      })
      .sort((a, b) => b.month.localeCompare(a.month));
  });

  let customHours = $state(40);
  let customForecast = $derived(customHours * weightedRate);
</script>

<section>
  <div class="page-header">
    <h2>Stipendi & Ore lavorate</h2>
  </div>

  <div class="status-pill-group">
    <button class:active={activeTab === "ore"} onclick={() => (activeTab = "ore")}>Ore & Turni</button>
    <button class:active={activeTab === "stipendi"} onclick={() => (activeTab = "stipendi")}>Stipendi</button>
    <button class:active={activeTab === "previsione"} onclick={() => (activeTab = "previsione")}>Previsione</button>
  </div>

  {#if error}
    <p class="error">Backend non raggiungibile: {error}</p>
  {:else if activeTab === "ore"}
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
  {:else if activeTab === "stipendi"}
    <div class="toolbar">
      <button class="btn-secondary" onclick={() => (showAddSalary = !showAddSalary)}>
        <Icon name="plus" size={14} /> Aggiungi stipendio
      </button>
    </div>

    {#if showAddSalary}
      <form class="add-panel" onsubmit={submitAddSalary}>
        <div class="fields">
          <input type="month" bind:value={addSalMonth} />
          <input type="number" step="0.01" bind:value={addSalNet} placeholder="Netto €" />
          <input type="number" step="0.01" bind:value={addSalGross} placeholder="Lordo € (opz.)" />
          <input type="number" step="0.1" bind:value={addSalHours} placeholder="Ore lavorate (opz.)" />
          <input type="text" bind:value={addSalNote} placeholder="Note (opz.)" />
        </div>
        <button type="submit" class="btn-primary">Salva</button>
        {#if addSalError}<p class="error">{addSalError}</p>{/if}
      </form>
    {/if}

    {#if salaryRecords.length === 0}
      <p class="hint">Nessuno stipendio registrato ancora.</p>
    {:else}
      <div class="kpi-grid three">
        <div class="metric-card">
          <span class="eyebrow">Media netto</span>
          <span class="kpi-value">€{avgNet.toFixed(2)}</span>
        </div>
        <div class="metric-card">
          <span class="eyebrow">Massimo</span>
          <span class="kpi-value positive">€{maxNet.toFixed(2)}</span>
        </div>
        <div class="metric-card">
          <span class="eyebrow">Minimo</span>
          <span class="kpi-value">€{minNet.toFixed(2)}</span>
        </div>
      </div>

      <div class="metric-card chart-card">
        <h3>Netto per mese</h3>
        <Chart type="bar" data={salaryChartData} options={salaryChartOptions} height={260} />
      </div>

      <div class="metric-card">
        <h3>Storico</h3>
        <div class="list">
          {#each salarySorted as s (s.id)}
            <div class="row">
              <span class="date">{monthLabel(s.month)}</span>
              <span class="desc">
                netto €{s.net.toFixed(2)}
                {#if s.gross}· lordo €{s.gross.toFixed(2)}{/if}
                {#if s.hours_worked}· {s.hours_worked}h ({(s.net / s.hours_worked).toFixed(2)}€/h){/if}
              </span>
              <button class="icon-btn" title="Elimina" onclick={() => deleteSalary(s.id)}>
                <Icon name="trash-2" size={14} />
              </button>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  {:else}
    <!-- Previsione -->
    {#if validSalary.length === 0}
      <p class="hint">Servono almeno uno stipendio con ore lavorate registrate per calcolare la previsione.</p>
    {:else}
      <div class="metric-card">
        <span class="eyebrow">Tariffa oraria media pesata</span>
        <span class="kpi-value">€{weightedRate.toFixed(2)}/h</span>
        <p class="hint">I mesi più recenti pesano di più nel calcolo.</p>
      </div>

      <div class="metric-card chart-card">
        <h3>Andamento tariffa oraria</h3>
        <Chart type="line" data={rateChartData} options={rateChartOptions} height={260} />
      </div>

      {#if forecastRows.length > 0}
        <div class="metric-card">
          <h3>Mesi con turni ma senza stipendio registrato</h3>
          <div class="list">
            {#each forecastRows as r}
              <div class="row">
                <span class="date">{monthLabel(r.month)}</span>
                <span class="desc">{r.hours.toFixed(1)}h lavorate</span>
                <span class="hours">≈ €{r.forecast.toFixed(2)}</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <div class="metric-card">
        <h3>Calcolatore previsione</h3>
        <div class="calc-row">
          <label>
            Ore lavorate
            <input type="number" step="0.5" bind:value={customHours} />
          </label>
          <span class="calc-result">≈ €{customForecast.toFixed(2)}</span>
        </div>
      </div>
    {/if}
  {/if}
</section>

<style>
  .page-header {
    margin-bottom: var(--space-4);
  }

  .status-pill-group {
    display: flex;
    gap: var(--space-2);
    margin-bottom: var(--space-5);
  }

  .status-pill-group button {
    padding: 0.4rem var(--space-4);
    border: none;
    border-radius: var(--radius-md);
    background: var(--muted);
    color: var(--text-primary);
    font-size: var(--text-sm);
    font-weight: 500;
    cursor: pointer;
  }

  .status-pill-group button.active {
    background: var(--accent);
    color: var(--accent-foreground);
  }

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

  .kpi-value.positive { color: var(--success); }

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

  .calc-row {
    display: flex;
    align-items: center;
    gap: var(--space-4);
  }

  .calc-row label {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--text-secondary);
  }

  .calc-row input {
    width: 5rem;
    padding: 0.4rem var(--space-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }

  .calc-result {
    font-family: var(--font-heading);
    font-size: var(--text-lg);
    font-weight: 700;
    color: var(--accent);
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
