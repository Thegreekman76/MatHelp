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

  function start() {
    // Cebá lastSeq con el banner que ya esté en pantalla (reanudar/SSR): no
    // queremos un beep espurio al cargar.
    var fb = document.querySelector(".q-fb[data-fb-seq]");
    if (fb) lastSeq = fb.getAttribute("data-fb-seq");
    refreshBtn();
    try {
      var mo = new MutationObserver(checkFeedback);
      mo.observe(document.body, {
        childList: true, subtree: true,
        attributes: true, attributeFilter: ["data-fb-seq", "class"],
      });
    } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
