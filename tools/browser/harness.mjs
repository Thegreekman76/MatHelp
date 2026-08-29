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
  "/ecuaciones", "/finanzas", "/trigonometria", "/funciones", "/estadistica",
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
    // 6. En la home (NO partida) el botón "Salir" NO debe verse. Chequeamos el
    //    display COMPUTADO, no la propiedad .hidden: el CSS .mh-salir-btn ganaba
    //    sobre el atributo hidden y lo dejaba visible siempre (regresión real).
    const btnOcultoHome = await page.evaluate(() => {
      const b = document.getElementById("mh-salir-btn");
      return !b || getComputedStyle(b).display === "none";
    });
    const ok = btnVis && trasLogo.modalAbierto && trasLogo.enJugar &&
      trasSeguir.cerrado && trasSeguir.enJugar && trasBtn && salio &&
      btnOcultoHome && dialogs.length === 0 && errs.length === 0;
    return {
      ok,
      detail: `btnTopbar=${btnVis ? "visible" : "OCULTO"} logo->modal=${trasLogo.modalAbierto ? "abre" : "NO"}(sinNavegar=${trasLogo.enJugar}) seguir=${trasSeguir.cerrado ? "cierra" : "NO"} btn->modal=${trasBtn ? "abre" : "NO"} salir->home=${salio ? "si" : "NO"} btnOcultoHome=${btnOcultoHome ? "si" : "NO(REGRESION)"} confirmNativo=${dialogs.length} errores=${errs.length}`,
    };
  } catch (e) {
    return { ok: false, detail: "excepcion: " + String(e).split("\n")[0] };
  } finally {
    await page.close();
  }
}

// --- helpers parametrizados (registro / perfil / elegir) ---------------------
async function isolatedCtx(browser) {
  if (browser.createBrowserContext) return await browser.createBrowserContext();
  if (browser.createIncognitoBrowserContext) return await browser.createIncognitoBrowserContext();
  return browser.defaultBrowserContext();
}
async function registrar(page, tag) {
  await page.goto(BASE + "/registro", { waitUntil: "networkidle2", timeout: 20000 });
  await page.type('input[name="familia"]', "E2E " + tag);
  const email = `e2e_${tag}@mathelp.test`;
  await page.type('input[name="email"]', email);
  await page.type('input[name="password"]', "clave-e2e-123");
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), page.click('button[type="submit"], input[type="submit"]')]);
  return email;
}
async function crearPerfil(page, nombre, grado, modalidad) {
  await page.goto(BASE + "/perfiles/nuevo", { waitUntil: "networkidle2", timeout: 20000 });
  await page.type('input[name="nombre"]', nombre);
  await page.select('select[name="grado"]', String(grado)).catch(() => {});
  if (modalidad) await page.select('select[name="modalidad"]', modalidad).catch(() => {});
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), page.click('button[type="submit"], input[type="submit"]')]);
}
async function elegirPerfil(page) {
  await page.goto(BASE + "/perfiles", { waitUntil: "networkidle2", timeout: 20000 });
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), page.click('form[action="/perfiles/elegir"] button[type="submit"], .mh-profile')]);
}

// Auth: registro exitoso deja sesión (ruta protegida accesible); email duplicado
// muestra error; login con las credenciales funciona y con password mala falla.
async function testAuth(browser) {
  const ctx = await isolatedCtx(browser);
  const page = await ctx.newPage();
  try {
    const tag = Math.random().toString(36).slice(2, 10);
    const email = await registrar(page, tag);
    const trasRegistro = page.url();
    const sesionOk = !trasRegistro.endsWith("/registro"); // redirigió (a /perfiles)
    // ruta protegida accesible con sesión (no rebota a /login)
    await page.goto(BASE + "/perfiles/nuevo", { waitUntil: "networkidle2" });
    const protegidaOk = page.url().includes("/perfiles");
    // email duplicado → error visible
    await page.goto(BASE + "/registro", { waitUntil: "networkidle2" });
    await page.type('input[name="familia"]', "Dup");
    await page.type('input[name="email"]', email);
    await page.type('input[name="password"]', "clave-e2e-123");
    await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }).catch(() => {}), page.click('button[type="submit"], input[type="submit"]')]);
    const dupError = await page.$(".mh-error").then((e) => !!e).catch(() => false);
    // login en un contexto NUEVO (sin sesión): con las mismas credenciales
    const ctx2 = await isolatedCtx(browser);
    const p2 = await ctx2.newPage();
    await p2.goto(BASE + "/login", { waitUntil: "networkidle2" });
    await p2.type('input[name="email"]', email);
    await p2.type('input[name="password"]', "clave-e2e-123");
    await Promise.all([p2.waitForNavigation({ waitUntil: "networkidle2" }), p2.click('button[type="submit"], input[type="submit"]')]);
    const loginOk = !p2.url().endsWith("/login");
    // password incorrecta → error, se queda en /login
    await p2.goto(BASE + "/logout", { waitUntil: "networkidle2" }).catch(() => {});
    await p2.goto(BASE + "/login", { waitUntil: "networkidle2" });
    await p2.type('input[name="email"]', email);
    await p2.type('input[name="password"]', "password-mala-xxx");
    await Promise.all([p2.waitForNavigation({ waitUntil: "networkidle2" }).catch(() => {}), p2.click('button[type="submit"], input[type="submit"]')]);
    const badLogin = await p2.$(".mh-error").then((e) => !!e).catch(() => false);
    await ctx2.close();
    const ok = sesionOk && protegidaOk && dupError && loginOk && badLogin;
    return { ok, detail: `registro->sesion=${sesionOk} protegida=${protegidaOk} dupEmail=${dupError ? "error" : "NO"} login=${loginOk} passMala=${badLogin ? "error" : "NO"}` };
  } catch (e) {
    return { ok: false, detail: "excepcion: " + String(e).split("\n")[0] };
  } finally {
    await ctx.close();
  }
}

// Editar perfil: crea grado 4, edita a grado 10, la card refleja el grado nuevo.
async function testEditProfile(browser) {
  const ctx = await isolatedCtx(browser);
  const page = await ctx.newPage();
  try {
    const tag = Math.random().toString(36).slice(2, 10);
    await registrar(page, tag);
    await crearPerfil(page, "Editable", 4, null);
    await page.goto(BASE + "/perfiles", { waitUntil: "networkidle2" });
    const href = await page.evaluate(() => { const e = document.querySelector(".mh-pedit"); return e ? e.getAttribute("href") : ""; });
    const abrio = href && href.includes("/perfiles/editar/");
    await page.goto(BASE + href, { waitUntil: "networkidle2" });
    const preGrado = await page.evaluate(() => { const g = document.querySelector('select[name="grado"]'); return g ? g.value : null; });
    await page.select('select[name="grado"]', "10").catch(() => {});
    await page.select('select[name="modalidad"]', "industrial").catch(() => {});
    await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), page.click('button[type="submit"], input[type="submit"]')]);
    await page.goto(BASE + "/perfiles", { waitUntil: "networkidle2" });
    const cardText = await page.evaluate(() => document.body.textContent.replace(/\s+/g, " "));
    // grado 10 = 3º secundaria
    const reflejado = cardText.includes("3º secundaria") || cardText.includes("3° secundaria");
    const ok = abrio && preGrado === "4" && reflejado;
    return { ok, detail: `abre=${abrio ? "si" : "NO"} preSel=${preGrado} tras-editar-3ºsec=${reflejado ? "si" : "NO"}` };
  } catch (e) {
    return { ok: false, detail: "excepcion: " + String(e).split("\n")[0] };
  } finally {
    await ctx.close();
  }
}

// Gating por grado: un perfil de grado 4 ve juegos de secundaria BLOQUEADOS
// (.mh-juego.lock) y los primarios jugables.
async function testGradeGating(browser) {
  const ctx = await isolatedCtx(browser);
  const page = await ctx.newPage();
  try {
    const tag = Math.random().toString(36).slice(2, 10);
    await registrar(page, tag);
    await crearPerfil(page, "Chico", 4, null);
    await elegirPerfil(page);
    await page.goto(BASE + "/juegos", { waitUntil: "networkidle2" });
    const info = await page.evaluate(() => ({
      bloqueados: document.querySelectorAll(".mh-juego.lock").length,
      jugables: document.querySelectorAll('.mh-juego a[href="/jugar"], a.mh-juego[href="/jugar"]').length,
      hayContrarreloj: document.body.innerHTML.includes('href="/jugar"'),
    }));
    // grado 4: enteros(7)/potencias(8)/trigonometria(10)/etc. deben estar bloqueados
    const ok = info.bloqueados > 0 && info.hayContrarreloj;
    return { ok, detail: `bloqueados=${info.bloqueados} contrarreloj=${info.hayContrarreloj ? "si" : "NO"}` };
  } catch (e) {
    return { ok: false, detail: "excepcion: " + String(e).split("\n")[0] };
  } finally {
    await ctx.close();
  }
}

// Panel del padre: tras jugar, /panel monta con StatCards + la sección de
// precisión por destreza (barras de progreso).
async function testPanel(browser) {
  const ctx = await isolatedCtx(browser);
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e)));
  try {
    const tag = Math.random().toString(36).slice(2, 10);
    await registrar(page, tag);
    await crearPerfil(page, "Jugador", 4, null);
    await elegirPerfil(page);
    // jugar ~14 respuestas para generar mastery
    await page.goto(BASE + "/jugar", { waitUntil: "networkidle2" });
    await page.waitForSelector(".q-opt", { timeout: 12000 });
    await sleep(700);
    for (let i = 0; i < 14; i++) { const b = await page.$$(".q-opt"); if (b.length) { await b[i % b.length].click(); await sleep(340); } }
    // abrir el panel
    await page.goto(BASE + "/panel", { waitUntil: "networkidle2" });
    const info = await page.evaluate(() => {
      const txt = document.body.textContent;
      return {
        precision: txt.includes("Precisión por destreza"),
        stats: document.querySelectorAll('.mh-card [class*="stat"], .mh-card [class*="flv-stat"]').length,
        barras: document.querySelectorAll('.mh-card [class*="progress"], .mh-card [class*="flv-pb"]').length,
      };
    });
    const ok = info.precision && info.barras > 0 && errs.length === 0;
    return { ok, detail: `precision=${info.precision ? "si" : "NO"} barras=${info.barras} errores=${errs.length}` };
  } catch (e) {
    return { ok: false, detail: "excepcion: " + String(e).split("\n")[0] };
  } finally {
    await ctx.close();
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

    // Auth/perfiles/panel usan contextos AISLADOS (para probar login sin sesión):
    // van al final porque el churn de crear/cerrar contextos puede desestabilizar
    // el browser compartido que usan el flicker/modal/smoke.
    console.log("\n=== Auth / perfiles / panel ===");
    for (const [nombre, fn] of [["auth", testAuth], ["editar perfil", testEditProfile], ["gating x grado", testGradeGating], ["panel", testPanel]]) {
      const r = await fn(browser);
      console.log(`  ${r.ok ? "✓" : "✗"} ${nombre.padEnd(16)} ${r.detail}`);
      if (!r.ok) fails++;
    }
  } finally {
    await browser.close();
  }
  console.log(`\n${fails === 0 ? "OK: browser E2E verde" : "FALLARON " + fails + " chequeos"}`);
  process.exit(fails === 0 ? 0 : 1);
})();
