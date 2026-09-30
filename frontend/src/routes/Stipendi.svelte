<script>
  import { api } from "../lib/api.js";
  import OreTurni from "../lib/components/salary/OreTurni.svelte";
  import StoricoStipendi from "../lib/components/salary/StoricoStipendi.svelte";
  import Previsione from "../lib/components/salary/Previsione.svelte";

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
    <OreTurni {shifts} {monthLabel} onchange={loadAll} onerror={(msg) => (error = msg)} />
  {:else if activeTab === "stipendi"}
    <StoricoStipendi {salaryRecords} {monthLabel} {monthLabelShort} onchange={loadAll} onerror={(msg) => (error = msg)} />
  {:else}
    <Previsione {shifts} {salaryRecords} {monthLabel} {monthLabelShort} />
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

  .error {
    color: var(--danger);
    font-size: var(--text-sm);
  }
</style>
