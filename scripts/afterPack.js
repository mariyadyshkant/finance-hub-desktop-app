// Hook electron-builder "afterPack" — gira dopo che l'app è assemblata in
// <productName>.app ma PRIMA che venga compressa in dmg/zip.
//
// Perché serve: extraResources aggiunge backend-dist/financed-backend (un
// eseguibile Mach-O non firmato, prodotto da PyInstaller) dentro Resources/.
// Senza questo passaggio, electron-builder firma solo il bundle .app
// "esterno" con una firma ad-hoc che non copre in modo coerente le risorse
// annidate — macOS Gatekeeper poi rifiuta l'intero bundle con "code has no
// resources but signature indicates they must be present" (verificabile con
// `spctl -a -vv`), e questo può bloccare silenziosamente lo spawn del
// processo backend anche dopo che l'utente ha autorizzato l'app con
// "tasto destro > Apri" — sintomo osservato: l'app si apre (frontend
// visibile) ma il backend non risponde mai.
//
// Il fix: ri-firmare l'intero bundle con --deep (ad-hoc, "-" — nessun
// certificato/account Apple Developer necessario) DOPO che tutte le risorse
// sono al loro posto, così la firma è coerente su tutto l'albero.
const { execFileSync } = require("child_process");
const path = require("path");

exports.default = async function (context) {
  if (context.electronPlatformName !== "darwin") return;

  const appPath = path.join(
    context.appOutDir,
    `${context.packager.appInfo.productFilename}.app`
  );

  console.log(`[afterPack] Ri-firmo (ad-hoc, --deep) ${appPath}`);
  execFileSync("codesign", ["--deep", "--force", "--sign", "-", appPath], {
    stdio: "inherit",
  });
};
