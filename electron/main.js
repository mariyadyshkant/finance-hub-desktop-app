const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");

const BACKEND_PORT = 8000;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const BACKEND_READY_TIMEOUT_MS = 20_000;
const BACKEND_POLL_INTERVAL_MS = 250;

let backendProcess;
let mainWindow;

function startBackend() {
  const backendDir = path.join(__dirname, "..", "backend");
  backendProcess = spawn(
    "python3",
    ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", String(BACKEND_PORT)],
    { cwd: backendDir, stdio: "inherit" }
  );
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
    title: "Finance Hub",
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

app.whenReady().then(async () => {
  startBackend();

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

// Espone l'URL del backend al resto del processo main, se servisse altrove.
module.exports = { BACKEND_URL };
