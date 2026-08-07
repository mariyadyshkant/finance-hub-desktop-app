// Espone al renderer la porta scelta dinamicamente da main.js per il
// backend FastAPI (vedi electron/main.js: findFreePort) — il frontend non
// può più assumere una porta fissa, dato che 8000 può essere occupata da
// altri servizi sulla macchina dell'utente.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("financedAPI", {
  getBackendPort: () => ipcRenderer.invoke("get-backend-port"),
});
