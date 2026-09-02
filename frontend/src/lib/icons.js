// Set in stile Lucide (stroke-based), fedele al wireframe di riferimento
// (frontend/dist/assets/*). `BASE_ICONS` è il set scritto a mano usato dalla UI
// (nav, azioni…); `GENERATED_ICONS` è un catalogo Lucide vendorizzato come dati
// (icons.generated.js) per il selettore icona delle categorie. Nessuna libreria
// di icone come dipendenza runtime — solo dati, stesso formato.
import { GENERATED_ICONS, ICON_KEYWORDS } from "./icons.generated.js";

const BASE_ICONS = {
  "layout-dashboard": `<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>`,
  "arrow-left-right": `<path d="M8 3L4 7l4 4M4 7h16m-4 14l4-4l-4-4m4 4H4"/>`,
  "pie-chart": `<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>`,
  "trending-up": `<path d="M16 7h6v6"/><path d="m22 7l-8.5 8.5l-5-5L2 17"/>`,
  "trending-down": `<path d="M16 17h6v-6"/><path d="m22 17l-8.5-8.5l-5 5L2 7"/>`,
  "credit-card": `<rect width="20" height="14" x="2" y="5" rx="2"/><path d="M2 10h20"/>`,
  landmark: `<path d="M10 18v-7m1.119-8.795a2 2 0 0 1 1.762 0l7.84 3.846A.5.5 0 0 1 20.5 7h-17a.5.5 0 0 1-.22-.949zM14 18v-7m4 7v-7M3 22h18M6 18v-7"/>`,
  wallet: `<path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4"/><path d="M4 6v12c0 1.1.9 2 2 2h14v-4"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>`,
  "file-text": `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>`,
  target: `<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>`,
  user: `<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>`,
  search: `<path d="m21 21l-4.34-4.34"/><circle cx="11" cy="11" r="8"/>`,
  calendar: `<path d="M8 2v4m8-4v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>`,
  "chevron-down": `<path d="m6 9l6 6l6-6"/>`,
  "chevron-left": `<path d="m15 18l-6-6l6-6"/>`,
  "chevron-right": `<path d="m9 18l6-6l-6-6"/>`,
  list: `<path d="M3 5h.01M3 12h.01M3 19h.01M8 5h13M8 12h13M8 19h13"/>`,
  repeat: `<path d="m17 2l4 4l-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4l4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>`,
  utensils: `<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2M7 2v20m14-7V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2zm0 0v7"/>`,
  "arrow-down-left": `<path d="M17 7L7 17m10 0H7V7"/>`,
  plane: `<path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8L4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1l3 2l2 3l1-1v-3l3-2l3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2"/>`,
  "shopping-bag": `<path d="M16 10a4 4 0 0 1-8 0M3.103 6.034h17.794"/><path d="M3.4 5.467a2 2 0 0 0-.4 1.2V20a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6.667a2 2 0 0 0-.4-1.2l-2-2.667A2 2 0 0 0 17 2H7a2 2 0 0 0-1.6.8z"/>`,
  "heart-pulse": `<path d="M2 9.5a5.5 5.5 0 0 1 9.591-3.676a.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5"/><path d="M3.22 13H9.5l.5-1l2 4.5l2-7l1.5 3.5h5.27"/>`,
  pencil: `<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4Z"/>`,
  "trash-2": `<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>`,
  plus: `<path d="M12 5v14"/><path d="M5 12h14"/>`,
  check: `<path d="M20 6 9 17l-5-5"/>`,
  clock: `<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>`,
  "arrow-up-right": `<path d="M7 17 17 7"/><path d="M7 7h10v10"/>`,
  "trending-flat": `<path d="M22 12H2"/><path d="m17 7 5 5-5 5"/>`,
  link: `<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><path d="M8 12h8"/>`,
  "piggy-bank": `<path d="M19 5c-1.5 0-2.8 1.4-3.5 3.7-3-.5-6-.3-8 .3-1 .3-1.5 1-1.5 2v3c0 .6.4 1 1 1h1"/><path d="M2 9v6"/><path d="M7 14v2"/><path d="M13 14v2"/><path d="M16 8.5c1.5 0 3 1 3 3.5v3c0 1-.5 2-2 2h-1"/><path d="M17 8.5V6"/>`,
  download: `<path d="M12 15V3"/><path d="m7 10 5 5 5-5"/><path d="M4 21h16"/>`,
  upload: `<path d="M12 3v12"/><path d="m7 8 5-5 5 5"/><path d="M4 21h16"/>`,
  filter: `<path d="M22 3H2l8 9.46V19l4 2v-8.54z"/>`,
  info: `<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>`,
  settings: `<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>`,
  x: `<path d="M18 6 6 18"/><path d="m6 6 12 12"/>`,
};

// I nomi scritti a mano vincono sui duplicati del catalogo (icone rifinite a
// mano per la nav e il wireframe).
export const ICONS = { ...GENERATED_ICONS, ...BASE_ICONS };

// Nomi selezionabili nel picker (pagina Impostazioni), ordinati.
export const PICKABLE_ICONS = Object.keys(ICONS).sort();

// Ricerca del picker: match su nome + parole chiave Lucide.
export function iconMatches(name, query) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  if (name.includes(q)) return true;
  const kw = ICON_KEYWORDS[name];
  return kw ? kw.toLowerCase().includes(q) : false;
}
