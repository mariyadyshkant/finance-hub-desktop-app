<script>
  import { Chart, registerables } from "chart.js";

  Chart.register(...registerables);

  let { type, data, options = {}, height = 260 } = $props();

  let canvasEl;
  let chartInstance;

  $effect(() => {
    // referenziati esplicitamente per far scattare l'effetto quando cambiano
    const _type = type;
    const _data = data;
    const _options = options;

    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(canvasEl, {
      type: _type,
      data: _data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        ..._options,
      },
    });

    return () => {
      chartInstance?.destroy();
      chartInstance = null;
    };
  });
</script>

<div class="chart-wrap" style="height: {height}px">
  <canvas bind:this={canvasEl}></canvas>
</div>

<style>
  .chart-wrap {
    position: relative;
    width: 100%;
  }
</style>
