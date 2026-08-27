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
    const bajo = before.secs !== null && after.secs !== null && parseInt(before.secs) > parseInt(after.secs);
    const ok = after.fb_ok && after.opt_ok && bajo && errs.length === 0;
    return {
      ok,
      detail: `feedback=${after.fb_ok ? "vive" : "RECREADO"} opcion=${after.opt_ok ? "vive" : "RECREADO"} reloj=${before.secs}->${after.secs} errores=${errs.length}`,
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
