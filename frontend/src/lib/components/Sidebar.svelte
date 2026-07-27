<script>
  let { routes, current, onNavigate } = $props();
</script>

<nav class="sidebar">
  <h1>💶 Finance Hub</h1>
  <ul>
    {#each routes as route}
      <li>
        <button
          class:active={current === route.id}
          onclick={() => onNavigate(route.id)}
        >
          <span class="icon">{route.icon}</span>
          {route.label}
        </button>
      </li>
    {/each}
  </ul>
</nav>

<style>
  .sidebar {
    width: 220px;
    flex-shrink: 0;
    background: #ffffff;
    border-right: 1px solid #ececea;
    padding: 1.25rem 0.75rem;
    height: 100vh;
    overflow-y: auto;
  }

  h1 {
    font-size: 1.1rem;
    margin: 0 0.5rem 1.5rem;
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  button {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.5rem 0.6rem;
    border: none;
    background: none;
    border-radius: 8px;
    font-size: 0.9rem;
    text-align: left;
    cursor: pointer;
    color: #2a2a28;
  }

  button:hover {
    background: #f5f5f3;
  }

  button.active {
    background: #eef3fb;
    color: #185fa5;
    font-weight: 500;
  }

  .icon {
    width: 1.2rem;
    text-align: center;
  }
</style>
