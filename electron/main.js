const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const net = require("net");
const path = require("path");
const fs = require("fs");

const DEFAULT_BACKEND_PORT = 8000;
const BACKEND_READY_TIMEOUT_MS = 20_000;
const BACKEND_POLL_INTERVAL_MS = 250;

let backendProcess;
let mainWindow;
let backendPort;
let BACKEND_URL;

// 8000 è spesso occupata da altri servizi di sviluppo sulla macchina
// dell'utente (es. `php artisan serve`, altri backend locali) — se il
// backend non riesce a partire su quella porta, le richieste finiscono
// silenziosamente su quel servizio altrui invece che sul nostro (visto in
// produzione: pagine d'errore Laravel/Werkzeug al posto delle risposte
// FastAPI). Proviamo quindi porte successive finché non ne troviamo una
// libera, invece di assumere che 8000 sia sempre disponibile.
function isPortFree(port) {
  return new Promise((resolve) => {
    const tester = net.createServer();
    tester.once("error", () => resolve(false));
    tester.once("listening", () => {
      tester.close(() => resolve(true));
    });
    tester.listen(port, "127.0.0.1");
  });
}

async function findFreePort(preferredPort, maxAttempts = 20) {
  for (let i = 0; i < maxAttempts; i++) {
    const candidate = preferredPort + i;
    if (await isPortFree(candidate)) return candidate;
  }
  throw new Error(`Nessuna porta libera trovata a partire da ${preferredPort}`);
}

// In sviluppo usiamo python3 dal venv locale (niente bisogno di rifare la
// build PyInstaller a ogni modifica). Il layout del venv differisce tra
// macOS/Linux (venv/bin/python3) e Windows (venv/Scripts/python.exe).
function resolvePython(backendDir) {
  const venvPython =
    process.platform === "win32"
      ? path.join(backendDir, "venv", "Scripts", "python.exe")
      : path.join(backendDir, "venv", "bin", "python3");
  if (fs.existsSync(venvPython)) return venvPython;
  return process.platform === "win32" ? "python" : "python3";
}

function startBackend(port) {
  if (app.isPackaged) {
    // Produzione: eseguibile PyInstaller autonomo (vedi .github/workflows/
    // release.yml) — non richiede Python installato sulla macchina di
    // destinazione. Un venv "normale" non è mai portabile: si appoggia
    // sempre all'installazione Python della macchina su cui è stato creato.
    const exeName = process.platform === "win32" ? "financed-backend.exe" : "financed-backend";
    const exePath = path.join(process.resourcesPath, "backend-dist", exeName);
    backendProcess = spawn(exePath, [], {
      cwd: path.dirname(exePath),
      stdio: "inherit",
      env: { ...process.env, PORT: String(port) },
    });
  } else {
    const backendDir = path.join(__dirname, "..", "backend");
    const pythonBin = resolvePython(backendDir);
    backendProcess = spawn(
      pythonBin,
      ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", String(port)],
      { cwd: backendDir, stdio: "inherit" }
    );
  }
  backendProcess.on("error", (err) => {
    console.error("Impossibile avviare il backend FastAPI:", err);
  });
}

// Il frontend prova a chiamare l'API non appena la finestra si carica: se il
// backend Python non è ancora su, la prima richiesta fallisce con un errore
// permanente (i componenti Svelte non ritentano da soli). Aspettiamo qui
// finché /health non risponde, così la finestra si apre solo quando l'API è
// davvero pronta.
function waitForBackend(timeoutMs = BACKEND_READY_TIMEOUT_MS) {
  const deadline = Date.now() + timeoutMs;

  return new Promise((resolve, reject) => {
    function attempt() {
      const req = http.get(`${BACKEND_URL}/health`, (res) => {
        res.resume();
        if (res.statusCode === 200) {
          resolve();
        } else {
          retry();
        }
      });
      req.on("error", retry);
    }

    function retry() {
      if (Date.now() > deadline) {
        reject(new Error("Timeout in attesa del backend FastAPI su " + BACKEND_URL));
        return;
      }
      setTimeout(attempt, BACKEND_POLL_INTERVAL_MS);
    }

    attempt();
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    title: "FinanceD",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const startUrl = process.env.ELECTRON_START_URL || `file://${path.join(__dirname, "..", "frontend", "dist", "index.html")}`;
  mainWindow.loadURL(startUrl);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

ipcMain.handle("get-backend-port", () => backendPort);

app.whenReady().then(async () => {
  backendPort = await findFreePort(DEFAULT_BACKEND_PORT);
  BACKEND_URL = `http://127.0.0.1:${backendPort}`;
  startBackend(backendPort);

  try {
    await waitForBackend();
  } catch (err) {
    console.error(err.message);
    // Meglio aprire comunque la finestra (mostrerà gli errori di rete nella UI)
    // che lasciare l'utente davanti a un'app che sembra non avviarsi mai.
  }

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProcess) backendProcess.kill();
});

// Espone la porta del backend al resto del processo main, se servisse altrove.
module.exports = { getBackendPort: () => backendPort };
