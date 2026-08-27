// harness.mjs — E2E de BROWSER REAL (puppeteer + Chrome) para MatHelp.
//
// Por qué existe: los E2E por WebSocket (tools/e2e_*.py) verifican persistencia,
// pero NO detectan problemas VISUALES/de interacción del cliente de LiveViews —
// como el parpadeo del reloj (2026-08-27), donde el server mandaba patches finos
// que el cliente NO aplicaba (caía a outerHTML y recreaba los nodos cada segundo).
// Un test por WS no lo ve; solo un browser real lo detecta.
//
// Qué chequea:
//   1. Parpadeo (juegos cronometrados /jugar y /vf): marca el feedback y una opción
//      con __mark, responde, espera varios ticks del reloj y verifica que los nodos
//      SOBREVIVAN (no se recreen) y que el reloj IGUAL baje (countdown client-side).
//   2. Smoke (los 21 juegos): carga cada ruta, verifica que el LiveComponent monte
//      y que NO haya errores de página (excepciones JS).
//
// Asume el server andando en BASE (test-browser.bat lo arranca). Setea un perfil
// de grado alto + modalidad comercial para desbloquear el máximo de juegos.
//
// Uso:  node tools/browser/harness.mjs   (o via test-browser.bat)

import fs from "fs";
import { createRequire } from "module";

const BASE = process.env.MATHELP_BASE || "http://127.0.0.1:3000";

// --- localizar puppeteer-core + Chrome ---------------------------------------
const require = createRequire(import.meta.url);
let puppeteer;
try {
  puppeteer = (await import("puppeteer-core")).default;
} catch (e) {
  console.error("✗ Falta puppeteer-core. Corré:  cd tools/browser && npm install");
  process.exit(2);
}

function findChrome() {
  const cands = [
    process.env.CHROME_PATH,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    (process.env.LOCALAPPDATA || "") + "/Google/Chrome/Application/chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
  ].filter(Boolean);
  for (const c of cands) { try { if (fs.existsSync(c)) return c; } catch (e) {} }
  return null;
}

const GAMES = [
  "/jugar", "/vf", "/completa", "/escalera", "/problemas", "/fracciones",
  "/series", "/hora", "/geometria", "/memoria", "/enteros", "/ordenar",
  "/estimar", "/porcentaje", "/volumen", "/historia", "/potencias",
  "/ecuaciones", "/finanzas", "/trigonometria", "/funciones",
];
const TIMED = ["/jugar", "/vf"];   // los que tienen reloj (parpadeo)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function setupProfile(page) {
  const tag = Math.random().toString(36).slice(2, 10);
  // registro
  await page.goto(BASE + "/registro", { waitUntil: "networkidle2", timeout: 20000 });
  await page.type('input[name="familia"]', "E2E " + tag);
  await page.type('input[name="email"]', `e2e_${tag}@mathelp.test`);
  await page.type('input[name="password"]', "clave-e2e-123");
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), page.click('button[type="submit"], input[type="submit"]')]);
  // perfil (grado 13 + comercial desbloquea el máximo)
  await page.goto(BASE + "/perfiles/nuevo", { waitUntil: "networkidle2", timeout: 20000 });
  await page.type('input[name="nombre"]', "E2E-" + tag);
  await page.select('select[name="grado"]', "13").catch(() => {});
  await page.select('select[name="modalidad"]', "comercial").catch(() => {});
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), page.click('button[type="submit"], input[type="submit"]')]);
  // elegir el perfil recién creado (la tarjeta es un form submit)
  await page.goto(BASE + "/perfiles", { waitUntil: "networkidle2", timeout: 20000 });
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle2" }),
    page.click('form[action="/perfiles/elegir"] button[type="submit"], .mh-profile'),
  ]);
}

async function testFlicker(browser, route) {
  const page = await browser.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e)));
  try {
    await page.goto(BASE + route, { waitUntil: "networkidle2", timeout: 20000 });
    // esperar a que el socket pinte un botón de acción del juego
    await page.waitForSelector("[data-flv-click]", { timeout: 12000 });
    await sleep(900);
    // responder (clickear la primera acción) → aparece el feedback
    await page.click("[data-flv-click]");
    await page.waitForSelector(".q-fbwrap", { timeout: 5000 }).catch(() => {});
    await sleep(400);
    const before = await page.evaluate(() => {
      const fb = document.querySelector(".q-fbwrap");
      const opt = document.querySelector("[data-flv-click]");
      if (fb) fb.__mark = "FB";
      if (opt) opt.__mark = "OPT";
      const t = document.querySelector(".q-tnum");
      return { fb: !!fb, opt: !!opt, secs: t ? t.textContent : null };
    });
    await sleep(3500); // varios ticks del reloj
    const after = await page.evaluate(() => {
      const fb = document.querySelector(".q-fbwrap");
      const opt = document.querySelector("[data-flv-click]");
      const t = document.querySelector(".q-tnum");
      return {
        fb_ok: fb ? fb.__mark === "FB" : false,
        opt_ok: opt ? opt.__mark === "OPT" : false,
        secs: t ? t.textContent : null,
      };
    });
    // El chequeo QUE IMPORTA (parpadeo): los nodos SOBREVIVEN. El del reloj es
    // secundario y a veces el read llega en 0 (timing del JS client-side): solo
    // exigimos que BAJE si se pudo leer un valor >1.
    const beforeN = parseInt(before.secs);
    const afterN = parseInt(after.secs);
    const legible = !isNaN(beforeN) && beforeN > 1;
    const bajo = legible ? afterN < beforeN : true;
    const ok = after.fb_ok && after.opt_ok && bajo && errs.length === 0;
    return {
      ok,
      detail: `feedback=${after.fb_ok ? "vive" : "RECREADO"} opcion=${after.opt_ok ? "vive" : "RECREADO"} reloj=${before.secs}->${after.secs}${legible ? "" : "(read flaky)"} errores=${errs.length}`,
    };
  } catch (e) {
    return { ok: false, detail: "excepcion: " + String(e).split("\n")[0] };
  } finally {
    await page.close();
  }
}

async function smokeGame(browser, route) {
  const page = await browser.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e)));
  try {
    await page.goto(BASE + route, { waitUntil: "networkidle2", timeout: 20000 });
    // el LiveComponent tiene que montar
    const mounted = await page.waitForSelector("[data-flv-component-name]", { timeout: 12000 }).then(() => true).catch(() => false);
    await sleep(600);
    // interaccion liviana: si hay una accion, clickearla (caza errores de handler)
    const hasAction = await page.$("[data-flv-click]");
    if (hasAction) { await page.click("[data-flv-click]").catch(() => {}); await sleep(400); }
    const ok = mounted && errs.length === 0;
    return { ok, detail: `${mounted ? "monta" : "NO MONTA"} errores=${errs.length}${errs[0] ? " · " + errs[0].slice(0, 80) : ""}` };
  } catch (e) {
    return { ok: false, detail: "excepcion: " + String(e).split("\n")[0] };
  } finally {
    await page.close();
  }
}

// Modal de salir (reemplaza el window.confirm): tocar el logo DURANTE la partida
// abre el modal de la app (no un confirm nativo); el botón "Salir" de la topbar
// aparece solo en partida; "Seguir jugando" cierra; "Salir igual" navega.
async function testModal(browser) {
  const page = await browser.newPage();
  const errs = [];
  const dialogs = [];
  page.on("pageerror", (e) => errs.push(String(e)));
  page.on("dialog", (d) => { dialogs.push(d.type()); d.dismiss().catch(() => {}); });
  try {
    await page.goto(BASE + "/jugar", { waitUntil: "networkidle2", timeout: 20000 });
    await page.waitForSelector("[data-flv-click]", { timeout: 12000 });
    await sleep(600);
    // 1. El botón "Salir" de la topbar es visible durante la partida.
    const btnVis = await page.evaluate(() => {
      const b = document.getElementById("mh-salir-btn");
      return !!b && !b.hidden;
    });
    // 2. Tocar el logo → abre el modal (NO navega, NO confirm nativo).
    await page.click(".mh-topbar-home");
    await sleep(300);
    const trasLogo = await page.evaluate(() => ({
      modalAbierto: (function () { var m = document.getElementById("mh-salir-modal"); return !!m && !m.hidden; })(),
      enJugar: location.pathname === "/jugar",
    }));
    // 3. "Seguir jugando" cierra el modal.
    await page.click("[data-mh-salir-seguir]");
    await sleep(200);
    const trasSeguir = await page.evaluate(() => {
      const m = document.getElementById("mh-salir-modal");
      return { cerrado: !!m && m.hidden, enJugar: location.pathname === "/jugar" };
    });
    // 4. El botón "Salir" de la topbar reabre el modal.
    await page.click("#mh-salir-btn");
    await sleep(200);
    const trasBtn = await page.evaluate(() => { var m = document.getElementById("mh-salir-modal"); return !!m && !m.hidden; });
    // 5. "Salir igual" navega al inicio.
    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle2", timeout: 8000 }).catch(() => {}),
      page.click(".mh-salir-ir"),
    ]);
    await sleep(300);
    const salio = await page.evaluate(() => location.pathname === "/");
    const ok = btnVis && trasLogo.modalAbierto && trasLogo.enJugar &&
      trasSeguir.cerrado && trasSeguir.enJugar && trasBtn && salio &&
      dialogs.length === 0 && errs.length === 0;
    return {
      ok,
      detail: `btnTopbar=${btnVis ? "visible" : "OCULTO"} logo->modal=${trasLogo.modalAbierto ? "abre" : "NO"}(sinNavegar=${trasLogo.enJugar}) seguir=${trasSeguir.cerrado ? "cierra" : "NO"} btn->modal=${trasBtn ? "abre" : "NO"} salir->home=${salio ? "si" : "NO"} confirmNativo=${dialogs.length} errores=${errs.length}`,
    };
  } catch (e) {
    return { ok: false, detail: "excepcion: " + String(e).split("\n")[0] };
  } finally {
    await page.close();
  }
}

(async () => {
  const chrome = findChrome();
  if (!chrome) { console.error("✗ No encontré Chrome. Seteá CHROME_PATH."); process.exit(2); }
  const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  let fails = 0;
  try {
    const setup = await browser.newPage();
    await setupProfile(setup);
    // pasar cookies de sesión a las demás páginas: comparten el mismo browser context
    await setup.close();

    console.log("\n=== Parpadeo (juegos cronometrados) ===");
    for (const route of TIMED) {
      const r = await testFlicker(browser, route);
      console.log(`  ${r.ok ? "✓" : "✗"} ${route.padEnd(12)} ${r.detail}`);
      if (!r.ok) fails++;
    }

    console.log("\n=== Modal de salir (reemplaza el confirm nativo) ===");
    {
      const r = await testModal(browser);
      console.log(`  ${r.ok ? "✓" : "✗"} /jugar       ${r.detail}`);
      if (!r.ok) fails++;
    }

    console.log("\n=== Smoke (montan + sin errores JS) ===");
    for (const route of GAMES) {
      const r = await smokeGame(browser, route);
      console.log(`  ${r.ok ? "✓" : "✗"} ${route.padEnd(14)} ${r.detail}`);
      if (!r.ok) fails++;
    }
  } finally {
    await browser.close();
  }
  console.log(`\n${fails === 0 ? "OK: browser E2E verde" : "FALLARON " + fails + " chequeos"}`);
  process.exit(fails === 0 ? 0 : 1);
})();
