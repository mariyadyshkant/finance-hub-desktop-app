const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");

const BACKEND_PORT = 8000;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

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

app.whenReady().then(() => {
  startBackend();
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
