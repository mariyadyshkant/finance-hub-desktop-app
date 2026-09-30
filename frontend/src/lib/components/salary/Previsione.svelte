<script>
  import Chart from "../Chart.svelte";
  import { CHART_COLORS, baseScales } from "../../chartTheme.js";

  let { shifts, salaryRecords, monthLabel, monthLabelShort } = $props();

  let shiftMonths = $derived(
    Array.from(new Set(shifts.map((s) => s.date.slice(0, 7)))).sort().reverse()
  );

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

<style>
  .metric-card {
    margin-bottom: var(--space-4);
  }

  .kpi-value {
    font-family: var(--font-heading);
    font-size: var(--text-xl);
    font-weight: 700;
    color: var(--text-primary);
  }

  .chart-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .chart-card h3, .metric-card > h3 {
    font-size: var(--text-base);
    font-weight: 600;
    margin: 0 0 var(--space-2);
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
</style>
