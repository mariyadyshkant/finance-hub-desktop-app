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

  const routes = [
    { id: "dashboard", label: "Dashboard", icon: "📊", component: Dashboard },
    { id: "transazioni", label: "Transazioni", icon: "💳", component: Transazioni },
    { id: "rimborsi", label: "Rimborsi", icon: "🔄", component: Rimborsi },
    { id: "splitwise", label: "Splitwise", icon: "🏦", component: Splitwise },
    { id: "stipendi", label: "Stipendi", icon: "📅", component: Stipendi },
    { id: "risparmi", label: "Risparmi", icon: "🐷", component: Risparmi },
    { id: "storico-notion", label: "Storico Notion", icon: "📓", component: StoricoNotion },
    { id: "pianificazione", label: "Pianificazione", icon: "🎯", component: Pianificazione },
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
    padding: 2rem;
    height: 100vh;
    overflow-y: auto;
  }
</style>
