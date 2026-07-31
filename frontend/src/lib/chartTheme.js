// Token condivisi per i grafici Chart.js — riprendono le variabili di
// app.css (Chart.js non legge le custom property CSS nei suoi config).
export const CHART_COLORS = {
  textPrimary: "#271d6b",
  textSecondary: "#2e4a83",
  textMuted: "#6b7794",
  grid: "#e5e0f5",
  accent: "#6966a0",
  accentSoft: "#a6a3c9",
  danger: "#ef4444",
  success: "#16a34a",
  // coppia fissa per "fonte dati" (Revolut/Notion) — 2 serie, non generata.
  // Non riusa --accent: validata con scripts/validate_palette.js della skill
  // dataviz (--accent da sola è sotto la soglia minima di chroma, legge
  // "grigia" invece che come colore identificativo in un grafico).
  sourceRevolut: "#2a78d6",
  sourceNotion: "#7e22ce",
};

export function hexToRgba(hex, alpha = 1) {
  const h = hex.replace("#", "");
  const bigint = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export const CHART_FONT = {
  family: "Geist, -apple-system, BlinkMacSystemFont, sans-serif",
};

export function baseScales(overrides = {}) {
  return {
    x: {
      grid: { display: false },
      ticks: { color: CHART_COLORS.textMuted, font: CHART_FONT },
      ...overrides.x,
    },
    y: {
      grid: { color: CHART_COLORS.grid },
      ticks: { color: CHART_COLORS.textMuted, font: CHART_FONT },
      ...overrides.y,
    },
  };
}
