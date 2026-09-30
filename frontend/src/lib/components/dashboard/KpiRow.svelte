<script>
  let { monthRows, allTx, selectedMonth, isRevolutMonth } = $props();

  let txSpese = $derived(
    monthRows.filter((r) => r.source !== "planned").reduce((s, r) => s + r.amount, 0)
  );
  let totSpese = $derived(monthRows.reduce((s, r) => s + r.amount, 0));
  let plannedTotal = $derived(totSpese - txSpese);
  let totEntrate = $derived(
    isRevolutMonth
      ? allTx
          .filter((tx) => tx.date.slice(0, 7) === selectedMonth && tx.amount > 0)
          .reduce((s, tx) => s + tx.amount, 0)
      : 0
  );
  let saldo = $derived(totEntrate - totSpese);
  let affittoMese = $derived(
    monthRows.filter((r) => r.category === "Affitto").reduce((s, r) => s + r.amount, 0)
  );
  let senzaAffitto = $derived(totSpese - affittoMese);
</script>

<div class="kpi-grid">
  <div class="metric-card">
    <span class="eyebrow">Totale spese</span>
    <span class="kpi-value negative">−€{totSpese.toFixed(2)}</span>
    {#if plannedTotal > 0}
      <span class="kpi-addon">
        €{txSpese.toFixed(2)} transazioni + €{plannedTotal.toFixed(2)} pianificate
      </span>
    {/if}
  </div>
  <div class="metric-card">
    <span class="eyebrow">Entrate</span>
    <span class="kpi-value" class:positive={totEntrate > 0}>
      {isRevolutMonth ? `+€${totEntrate.toFixed(2)}` : "n/d"}
    </span>
  </div>
  <div class="metric-card">
    <span class="eyebrow">Saldo</span>
    <span class="kpi-value" class:positive={saldo >= 0} class:negative={saldo < 0}>
      {isRevolutMonth ? `${saldo >= 0 ? "+" : ""}€${saldo.toFixed(2)}` : "n/d"}
    </span>
  </div>
  <div class="metric-card">
    <span class="eyebrow">Senza affitto</span>
    <span class="kpi-value negative">−€{senzaAffitto.toFixed(2)}</span>
  </div>
</div>

<style>
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--space-3);
    margin-bottom: var(--space-5);
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

  .kpi-value.negative { color: var(--danger); }
  .kpi-value.positive { color: var(--success); }

  .kpi-addon {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
</style>
