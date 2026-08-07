<script>
  import { api } from "../lib/api.js";
  import Icon from "../lib/components/Icon.svelte";

  let user = $state(null);
  let friends = $state([]);
  let groups = $state([]);
  let expenses = $state([]);
  let notConfigured = $state(false);
  let error = $state("");
  let loading = $state(true);

  $effect(() => {
    (async () => {
      loading = true;
      try {
        user = await api.get("/splitwise/user");
        notConfigured = false;
        error = "";
        const [f, g, e] = await Promise.all([
          api.get("/splitwise/friends"),
          api.get("/splitwise/groups"),
          api.get("/splitwise/expenses"),
        ]);
        friends = f;
        groups = g;
        expenses = e;
      } catch (e) {
        if (e.message.startsWith("400")) {
          notConfigured = true;
        } else {
          error = e.message;
        }
      } finally {
        loading = false;
      }
    })();
  });

  let owedToMe = $derived.by(() => {
    const rows = [];
    for (const f of friends) {
      const name = `${f.first_name || ""} ${f.last_name || ""}`.trim();
      for (const bal of f.balance || []) {
        const amt = parseFloat(bal.amount);
        if (amt > 0) rows.push({ name, amount: amt });
      }
    }
    return rows.sort((a, b) => b.amount - a.amount);
  });

  let iOwe = $derived.by(() => {
    const rows = [];
    for (const f of friends) {
      const name = `${f.first_name || ""} ${f.last_name || ""}`.trim();
      for (const bal of f.balance || []) {
        const amt = parseFloat(bal.amount);
        if (amt < 0) rows.push({ name, amount: Math.abs(amt) });
      }
    }
    return rows.sort((a, b) => b.amount - a.amount);
  });

  let totalOwedToMe = $derived(owedToMe.reduce((s, r) => s + r.amount, 0));
  let totalIOwe = $derived(iOwe.reduce((s, r) => s + r.amount, 0));

  function groupBalance(g) {
    if (!user) return null;
    const me = (g.members || []).find((m) => m.id === user.id);
    if (!me) return null;
    for (const bal of me.balance || []) {
      return parseFloat(bal.amount);
    }
    return 0;
  }

  let expenseRows = $derived.by(() => {
    if (!user) return [];
    return expenses.map((e) => {
      let myShare = 0;
      for (const u of e.users || []) {
        if (u.user_id === user.id) {
          myShare = parseFloat(u.owed_share) - parseFloat(u.paid_share);
        }
      }
      return {
        date: (e.date || "").slice(0, 10),
        description: e.description || "—",
        cost: parseFloat(e.cost || 0),
        myShare,
      };
    });
  });
</script>

<section>
  <div class="page-header">
    <div>
      <h2>Splitwise</h2>
      <p class="subtitle">Conti condivisi</p>
    </div>
  </div>

  {#if loading}
    <p class="hint">Connessione a Splitwise...</p>
  {:else if notConfigured}
    <div class="setup-panel">
      <Icon name="link" size={20} />
      <h3>Collega Splitwise</h3>
      <p class="hint">
        Vai su <a href="https://secure.splitwise.com/oauth_clients" target="_blank" rel="noreferrer">splitwise.com/oauth_clients</a>,
        crea una nuova app (nome e URL qualsiasi) e copia l'<strong>API Key</strong>.
      </p>
      <p class="hint">
        Aggiungila in <code>backend/.env</code>:
      </p>
      <pre>SPLITWISE_API_KEY=la-tua-chiave</pre>
      <p class="hint">Poi riavvia l'app.</p>
    </div>
  {:else if error}
    <p class="error">Errore di connessione a Splitwise: {error}</p>
  {:else}
    <p class="connected">
      <Icon name="check" size={14} />
      Connessa come <strong>{user.first_name} {user.last_name}</strong>{user.email ? ` (${user.email})` : ""}
    </p>

    <div class="kpi-grid">
      <div class="metric-card">
        <span class="eyebrow">Mi devono</span>
        <span class="kpi-value positive">€{totalOwedToMe.toFixed(2)}</span>
      </div>
      <div class="metric-card">
        <span class="eyebrow">Devo io</span>
        <span class="kpi-value negative">€{totalIOwe.toFixed(2)}</span>
      </div>
    </div>

    <div class="balance-columns">
      <div class="metric-card">
        <h3>💚 Mi devono</h3>
        {#if owedToMe.length === 0}
          <p class="hint">Nessuno ti deve niente.</p>
        {:else}
          {#each owedToMe as r}
            <div class="balance-row"><span>{r.name}</span><span class="positive">€{r.amount.toFixed(2)}</span></div>
          {/each}
        {/if}
      </div>
      <div class="metric-card">
        <h3>🔴 Devo io</h3>
        {#if iOwe.length === 0}
          <p class="hint">Non devi niente a nessuno.</p>
        {:else}
          {#each iOwe as r}
            <div class="balance-row"><span>{r.name}</span><span class="negative">€{r.amount.toFixed(2)}</span></div>
          {/each}
        {/if}
      </div>
    </div>

    <div class="metric-card">
      <h3>Gruppi</h3>
      {#if groups.length === 0}
        <p class="hint">Nessun gruppo attivo.</p>
      {:else}
        {#each groups as g}
          {@const bal = groupBalance(g)}
          <div class="group-row">
            <div class="group-name">
              <Icon name="landmark" size={14} />
              {g.name || "Gruppo"}
            </div>
            {#if bal !== null}
              <span class:positive={bal > 0} class:negative={bal < 0}>
                {bal === 0 ? "In pari" : `${bal > 0 ? "+" : ""}€${bal.toFixed(2)}`}
              </span>
            {/if}
            <span class="members">{(g.members || []).map((m) => m.first_name).join(", ")}</span>
          </div>
        {/each}
      {/if}
    </div>

    <div class="metric-card">
      <h3>Ultime spese condivise</h3>
      {#if expenseRows.length === 0}
        <p class="hint">Nessuna spesa recente.</p>
      {:else}
        <div class="expense-list">
          {#each expenseRows as e}
            <div class="expense-row">
              <span class="date">{e.date}</span>
              <span class="desc">{e.description}</span>
              <span class="cost">€{e.cost.toFixed(2)}</span>
              <span class:positive={e.myShare > 0} class:negative={e.myShare < 0}>
                {e.myShare > 0 ? "+" : ""}€{e.myShare.toFixed(2)}
              </span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .page-header {
    margin-bottom: var(--space-5);
  }

  .subtitle {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin: 4px 0 0;
  }

  .setup-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    max-width: 32rem;
    color: var(--accent);
  }

  .setup-panel h3 {
    color: var(--text-primary);
    margin: var(--space-3) 0;
  }

  .setup-panel a {
    color: var(--accent);
  }

  .setup-panel pre {
    background: var(--input-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: var(--space-3);
    font-size: var(--text-sm);
    color: var(--text-primary);
  }

  .connected {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--success);
    font-size: var(--text-sm);
    margin-bottom: var(--space-5);
  }

  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
  }

  .positive { color: var(--success); }
  .negative { color: var(--danger); }

  .balance-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-4);
    margin-bottom: var(--space-4);
  }

  .balance-columns h3, .metric-card > h3 {
    font-size: var(--text-base);
    font-weight: 600;
    margin: 0 0 var(--space-3);
  }

  .balance-row {
    display: flex;
    justify-content: space-between;
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--border);
    font-size: var(--text-sm);
  }

  .balance-row:last-child { border-bottom: none; }

  .metric-card {
    margin-bottom: var(--space-4);
  }

  .group-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--border);
    font-size: var(--text-sm);
  }

  .group-row:last-child { border-bottom: none; }

  .group-name {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-weight: 500;
    flex-shrink: 0;
  }

  .members {
    color: var(--text-muted);
    font-size: var(--text-xs);
    margin-left: auto;
  }

  .expense-list {
    display: flex;
    flex-direction: column;
  }

  .expense-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--border);
    font-size: var(--text-sm);
  }

  .expense-row:last-child { border-bottom: none; }

  .expense-row .date {
    color: var(--text-muted);
    font-size: var(--text-xs);
    width: 5.5rem;
    flex-shrink: 0;
  }

  .expense-row .desc {
    flex: 1;
  }

  .expense-row .cost {
    color: var(--text-secondary);
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
