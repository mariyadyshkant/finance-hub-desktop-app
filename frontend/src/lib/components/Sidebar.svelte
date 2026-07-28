<script>
  import Icon from "./Icon.svelte";
  import logo from "../assets/logo.png";

  let { routes, current, onNavigate } = $props();
</script>

<nav class="sidebar">
  <div class="brand">
    <img src={logo} alt="FinanceD" />
  </div>

  <ul>
    {#each routes as route}
      <li>
        <button
          class:active={current === route.id}
          onclick={() => onNavigate(route.id)}
        >
          <Icon name={route.icon} size={16} strokeWidth={2.5} />
          {route.label}
        </button>
      </li>
    {/each}
  </ul>

  <div class="footer">
    <div class="avatar">
      <Icon name="user" size={14} strokeWidth={3} />
    </div>
    <div class="footer-text">
      <span class="name">Mariya</span>
      <span class="sub">Uso personale</span>
    </div>
  </div>
</nav>

<style>
  .sidebar {
    width: 220px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    background: var(--surface);
    border-right: 1px solid var(--border);
    height: 100vh;
  }

  .brand {
    padding: var(--space-3) var(--space-2) var(--space-2);
  }

  .brand img {
    display: block;
    height: 70px;
    width: auto;
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0 var(--space-3);
    display: flex;
    flex-direction: column;
    gap: 1px;
    flex: 1;
    overflow-y: auto;
  }

  button {
    width: 90%;
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: 0.6rem var(--space-4);
    border: none;
    background: none;
    border-radius: var(--radius-lg);
    font-size: var(--text-sm);
    font-weight: 500;
    text-align: left;
    cursor: pointer;
    color: var(--nav-inactive);
    transition: background 0.12s ease, color 0.12s ease;
  }

  button:hover {
    background: var(--muted);
  }

  button.active {
    background: var(--accent);
    color: var(--accent-foreground);
  }

  .footer {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-4);
    border-top: 1px solid var(--border);
    margin-top: var(--space-4);
  }

  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 999px;
    background: var(--muted);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .footer-text {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .name {
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--text-primary);
  }

  .sub {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
</style>
