# Feature: verifica pagina portfolio e screenshot/video collegati dal README — issue-audit-5

## Obiettivo

Dall'audit del repo (30/09/2026, commit `3b56e4f`, vedi `AUDIT.md`): la pagina
portfolio `mariyadyshkant.com/progetti/financed` non è stata verificabile nel
contenuto in modo automatico (SPA renderizzata via JS). Il README dichiara
esplicitamente che non esiste una demo pubblica dell'app (dati finanziari
reali dell'autrice) — scelta legittima — ma questo rende quella pagina
portfolio l'unico modo per chi legge il repo di vedere l'app funzionare.
Serve verificare a mano che la pagina esista davvero, sia raggiungibile dal
link nel README, e contenga effettivamente screenshot/video dell'app.

## Dipendenze

- Nessuna.

## Stack

- N/A — verifica manuale nel browser, non è una modifica di codice
  dell'app desktop.

## Output atteso

- Aprire `mariyadyshkant.com/progetti/financed` in un browser reale e
  confermare che la pagina di dettaglio esiste e carica correttamente.
- Confermare che contiene screenshot e/o video effettivi dell'app FinanceD
  (non placeholder, non rotti).
- Confermare che il link dal README di questo repo porta effettivamente a
  quella pagina (URL corretto, nessun redirect rotto).
- Se mancano screenshot/video o il link è rotto: aggiungerli/sistemarli sul
  sito portfolio (fuori da questo repo) e solo poi chiudere l'issue.

## Status

[ ] Da fare
