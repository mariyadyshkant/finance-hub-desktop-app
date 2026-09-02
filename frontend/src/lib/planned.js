// Le "spese pianificate" sono diventate una regola dell'app da agosto 2026 in
// poi. I mesi importati dalla vecchia web app (fino a luglio 2026) sono
// precedenti a questa logica: sommare lì le pianificate mostrerebbe spese
// duplicate o mai avvenute. Quindi le pianificate entrano nei totali e nei
// grafici solo per i mesi >= PLANNED_EXPENSES_FROM.
export const PLANNED_EXPENSES_FROM = "2026-08";

export const plannedApplies = (month) => !!month && month >= PLANNED_EXPENSES_FROM;
