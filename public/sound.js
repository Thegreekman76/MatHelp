// sound.js — mejoras del cliente de MatHelp (F6): sonido de feedback opcional
// + registro del service worker (instalable). Cargado en todas las páginas.
//
// Sonido (cero assets: los beeps se sintetizan con Web Audio, funciona offline):
// - Toggle 🔊/🔇 en el topbar (#mh-sound-btn), preferencia en localStorage.
// - Un beep corto al acertar (sube) y otro al errar (baja), disparados cuando
//   aparece un feedback nuevo. El banner lleva data-fb-seq (índice del ejercicio,
//   único por respuesta): sonamos solo cuando ese valor cambia, así no se repite
//   ni suena de más aunque el runtime re-renderice el componente.
// - El audio se "desbloquea" con el primer gesto del usuario (política de
//   autoplay de los browsers): el primer tap sirve de gesto.
//
// PWA: registra /sw.js para que la app sea instalable y arranque rápido.

// --- service worker (instalable) ---
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").catch(function () {});
  });
}

(function () {
  "use strict";
  var KEY = "mathelp_sound";

  function isOn() {
    try { return localStorage.getItem(KEY) !== "off"; } catch (e) { return true; }
  }
  function setOn(v) {
    try { localStorage.setItem(KEY, v ? "on" : "off"); } catch (e) {}
    refreshBtn();
  }

  var ac = null;
  function ctx() {
    try {
      if (!ac) { var AC = window.AudioContext || window.webkitAudioContext; if (AC) ac = new AC(); }
      if (ac && ac.state === "suspended") ac.resume();
    } catch (e) {}
    return ac;
  }
  // Desbloqueo del audio en el primer gesto.
  document.addEventListener("pointerdown", ctx, { passive: true });

  function beep(good) {
    if (!isOn()) return;
    var c = ctx();
    if (!c) return;
    var o = c.createOscillator();
    var g = c.createGain();
    o.connect(g);
    g.connect(c.destination);
    var t = c.currentTime;
    if (good) {
      o.type = "sine";
      o.frequency.setValueAtTime(660, t);
      o.frequency.setValueAtTime(990, t + 0.10);
    } else {
      o.type = "triangle";
      o.frequency.setValueAtTime(320, t);
      o.frequency.setValueAtTime(180, t + 0.14);
    }
    var dur = good ? 0.24 : 0.34;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.20, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.start(t);
    o.stop(t + dur + 0.02);
  }

  // Acorde ascendente ("¡nivel!") para los hitos de racha. Cero assets: tres
  // ondas escalonadas (C5-E5-G5). No spamea: sólo suena en el hito, no en cada
  // acierto (eso ya lo cubre beep()).
  function chord() {
    if (!isOn()) return;
    var c = ctx();
    if (!c) return;
    var notes = [523.25, 659.25, 783.99];
    for (var i = 0; i < notes.length; i++) {
      var o = c.createOscillator();
      var g = c.createGain();
      o.connect(g);
      g.connect(c.destination);
      o.type = "sine";
      var t = c.currentTime + i * 0.08;
      o.frequency.setValueAtTime(notes[i], t);
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(0.16, t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.30);
      o.start(t);
      o.stop(t + 0.34);
    }
  }

  // --- toggle del topbar ---
  function refreshBtn() {
    var b = document.getElementById("mh-sound-btn");
    if (!b) return;
    var on = isOn();
    b.setAttribute("aria-pressed", on ? "true" : "false");
    var ico = b.querySelector(".mh-sound-ico");
    if (ico) ico.textContent = on ? "🔊" : "🔇";
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest ? e.target.closest("#mh-sound-btn") : null;
    if (!b) return;
    e.preventDefault();
    setOn(!isOn());
    ctx(); // el click cuenta como gesto: dejá el audio listo
    if (isOn()) beep(true); // pequeño feedback al activarlo
  });

  // --- sonido en cada feedback nuevo ---
  var lastSeq = null;
  function checkFeedback() {
    var fb = document.querySelector(".q-fb[data-fb-seq]");
    if (!fb) return;
    var seq = fb.getAttribute("data-fb-seq");
    if (seq === lastSeq) return;
    lastSeq = seq;
    if (fb.classList.contains("ok")) beep(true);
    else if (fb.classList.contains("bad")) beep(false);
  }

  // Toast efímero (aviso visual, se auto-oculta). Cero assets: un div que se
  // crea al vuelo y se reusa.
  function showToast(text) {
    try {
      var t = document.getElementById("mh-toast");
      if (!t) {
        t = document.createElement("div");
        t.id = "mh-toast";
        t.className = "mh-toast";
        t.setAttribute("aria-hidden", "true");
        document.body.appendChild(t);
      }
      t.textContent = text;
      t.classList.remove("show");
      void t.offsetWidth; // reflow: reinicia la animación
      t.classList.add("show");
      clearTimeout(t._hide);
      t._hide = setTimeout(function () { t.classList.remove("show"); }, 1800);
    } catch (e) {}
  }

  // --- acorde + toast en los hitos de racha (5, 10, ...) ---
  var lastRacha = 0;
  function checkStreak() {
    var el = document.querySelector(".q-racha[data-racha]");
    if (!el) { lastRacha = 0; return; } // la racha se cortó (o no hay)
    var n = parseInt(el.getAttribute("data-racha"), 10) || 0;
    if (n > lastRacha && n >= 5 && n % 5 === 0) { chord(); showToast("🔥 " + n); }
    lastRacha = n;
  }
  function tick() { checkFeedback(); checkStreak(); }

  function start() {
    // Cebá lastSeq con el banner que ya esté en pantalla (reanudar/SSR): no
    // queremos un beep espurio al cargar.
    var fb = document.querySelector(".q-fb[data-fb-seq]");
    if (fb) lastSeq = fb.getAttribute("data-fb-seq");
    var rc = document.querySelector(".q-racha[data-racha]");
    if (rc) lastRacha = parseInt(rc.getAttribute("data-racha"), 10) || 0;
    refreshBtn();
    try {
      var mo = new MutationObserver(tick);
      mo.observe(document.body, {
        childList: true, subtree: true,
        attributes: true, attributeFilter: ["data-fb-seq", "data-racha", "class"],
      });
    } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

// --- teclado físico (F8 pulido): en los juegos de TECLADO, mapear las teclas del
// teclado real a los botones. Sólo actúa si hay botones de dígito en pantalla (los
// juegos de opción múltiple no tienen), así no interfiere con V/F ni el menú. ---
(function () {
  "use strict";
  document.addEventListener("keydown", function (e) {
    var tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    // ¿estamos en un juego de teclado? (hay botones de dígito)
    if (!document.querySelector('[data-flv-click="digito"]')) return;
    var k = e.key, sel = null;
    if (k >= "0" && k <= "9") sel = '[data-flv-click="digito"][data-flv-value-d="' + k + '"]';
    else if (k === "Backspace" || k === "Delete") sel = '[data-flv-click="borrar"]';
    else if (k === "Enter") sel = '[data-flv-click="answer"]';
    else if (k === "-" || k === "+") sel = '[data-flv-click="signo"]';
    if (!sel) return;
    var btn = document.querySelector(sel);
    if (btn) { e.preventDefault(); btn.click(); }
  });
})();

// --- narración de "Historia" (Web Speech API): lee el cuento en voz alta para
// pre-lectores. El primer cuento no se auto-lee (política de autoplay: falta gesto);
// el chico toca "🔊 Escuchar". Tras responder (gesto), los siguientes se leen solos. ---
(function () {
  "use strict";
  if (!("speechSynthesis" in window)) return;
  var lastSeq = null;

  function speakStory(force) {
    var el = document.querySelector(".hist-text[data-hist-seq]");
    if (!el) return;
    var seq = el.getAttribute("data-hist-seq");
    if (!force && seq === lastSeq) return;
    lastSeq = seq;
    try {
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance((el.textContent || "").trim());
      u.lang = el.getAttribute("data-hist-lang") || "es-AR";
      u.rate = 0.95;
      window.speechSynthesis.speak(u);
    } catch (e) {}
  }

  document.addEventListener("click", function (e) {
    var b = e.target.closest ? e.target.closest("[data-hist-replay]") : null;
    if (b) { e.preventDefault(); speakStory(true); }
  });

  function start() {
    // Cebá con el cuento en pantalla: no lo leemos al cargar (falta gesto del usuario).
    var el = document.querySelector(".hist-text[data-hist-seq]");
    if (el) lastSeq = el.getAttribute("data-hist-seq");
    try {
      var mo = new MutationObserver(function () { speakStory(false); });
      mo.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-hist-seq"] });
    } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

// --- Reloj client-side del contrarreloj / Verdadero-Falso -------------------
// El server ya NO empuja un frame por segundo (eso re-renderizaba el componente
// entero y hacía parpadear las opciones y demás). El componente pinta el reloj
// con data-q-total (segundos totales, constante); acá bajamos el número en el DOM
// sin tocar el server. El server sigue siendo autoritativo del fin: cuando se
// agota, empuja el frame del resumen y el reloj desaparece.
(function () {
  var deadline = null;
  var lastTotal = null;
  function tick() {
    var timer = document.querySelector(".q-timer[data-q-total]");
    if (!timer) { deadline = null; lastTotal = null; return; }   // no cronometrado (o ya terminó)
    var total = parseInt(timer.getAttribute("data-q-total"), 10);
    if (isNaN(total) || total <= 0) { return; }
    // Arrancá (o re-sincronizá si el server cambió el total, p.ej. SSR -> socket).
    if (deadline === null || total !== lastTotal) {
      lastTotal = total;
      deadline = Date.now() + total * 1000;
    }
    var rem = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
    var num = timer.querySelector(".q-tnum");
    if (num && num.textContent !== String(rem)) { num.textContent = String(rem); }
  }
  setInterval(tick, 250);
})();

// --- No cambiar de idioma en medio de un juego --------------------------------
// Cambiar idioma recarga la página (setea la cookie + redirect), y eso arranca un
// socket/juego NUEVO: se pierde la partida en curso. En las páginas de juego (las
// que montan un LiveComponent, marcadas con data-flv-component-name) ocultamos el
// selector de idioma; se cambia desde el menú/home antes de jugar.
(function () {
  function apply() {
    var enJuego = document.querySelector("[data-flv-component-name]");
    var langs = document.querySelector(".mh-langs");
    if (enJuego && langs) { langs.style.display = "none"; }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
