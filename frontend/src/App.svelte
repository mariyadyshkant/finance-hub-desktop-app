<script>
  import Sidebar from "./lib/components/Sidebar.svelte";
  import Dashboard from "./routes/Dashboard.svelte";
  import Transazioni from "./routes/Transazioni.svelte";
  import Rimborsi from "./routes/Rimborsi.svelte";
  import Splitwise from "./routes/Splitwise.svelte";
  import Stipendi from "./routes/Stipendi.svelte";
  import Risparmi from "./routes/Risparmi.svelte";
  import StoricoNotion from "./routes/StoricoNotion.svelte";
  import Pianificazione from "./routes/Pianificazione.svelte";
  import Impostazioni from "./routes/Impostazioni.svelte";

  const routes = [
    { id: "dashboard", label: "Dashboard", icon: "layout-dashboard", component: Dashboard },
    { id: "transazioni", label: "Transazioni", icon: "arrow-left-right", component: Transazioni },
    { id: "rimborsi", label: "Rimborsi", icon: "repeat", component: Rimborsi },
    { id: "splitwise", label: "Splitwise", icon: "landmark", component: Splitwise },
    { id: "stipendi", label: "Stipendi", icon: "trending-up", component: Stipendi },
    { id: "risparmi", label: "Risparmi", icon: "wallet", component: Risparmi },
    { id: "storico-notion", label: "Storico Notion", icon: "file-text", component: StoricoNotion },
    { id: "pianificazione", label: "Pianificazione", icon: "pie-chart", component: Pianificazione },
    { id: "impostazioni", label: "Impostazioni", icon: "settings", component: Impostazioni },
  ];

  let current = $state("dashboard");
  let CurrentComponent = $derived(routes.find((r) => r.id === current).component);
</script>

<main>
  <Sidebar {routes} {current} onNavigate={(id) => (current = id)} />
  <div class="content">
    <CurrentComponent />
  </div>
</main>

<style>
  main {
    display: flex;
  }

  .content {
    flex: 1;
    padding: var(--space-6);
    height: 100vh;
    overflow-y: auto;
  }
</style>
