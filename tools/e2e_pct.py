#!/usr/bin/env python3
# tools/e2e_pct.py — E2E del juego "Porcentaje" (descuentos/IVA/recargo, F9).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil -> GET /juegos muestra "Porcentaje" (href="/porcentaje").
#   2. GET /porcentaje -> el SSR trae el enunciado (.pct-eq) con data-*.
#   3. Abre WS /live/porcentaje; en cada turno LEE kind/p/n/p2, RECOMPUTA el
#      resultado (simple / descuento / IVA / recargo / sucesivos) y lo tipea.
#   4. Verifica: data-fb-seq, q-racha, q-progress, estrellas, ronda perfecta +
#      confetti + récord; y en Postgres: sesión mode='pct' topic 'pct', 10 attempts
#      TODOS correctos, best_streak=10 en profile_game_stats.
#
# Requiere: requests, websocket-client, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_pct.py --only build   (o --only run, o ambos)

import argparse, json, os, re, subprocess, time, uuid
import requests
import websocket  # websocket-client

BASE = "http://127.0.0.1:3000"
PSQL = os.environ.get("FITZ_PSQL", r"C:\Program Files\PostgreSQL\15\bin\psql.exe")
PGUSER = os.environ.get("FITZ_PGUSER", "postgres")
PGPASS = os.environ.get("FITZ_PGPASS", "123mgp")
PGDB = os.environ.get("FITZ_PGDB", "mathelp")
PGENV = {**os.environ, "PGPASSWORD": PGPASS}
LIMIT = 10


def psql(sql):
    out = subprocess.run(
        [PSQL, "-h", "localhost", "-U", PGUSER, "-d", PGDB, "-tAc", sql],
        capture_output=True, text=True, env=PGENV,
    )
    if out.returncode != 0:
        raise RuntimeError(f"psql fallo: {out.stderr}")
    return out.stdout.strip()


def wait_up(timeout=40):
    for _ in range(timeout * 2):
        try:
            requests.get(BASE + "/", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def setup_perfil(s, grado):
    tag = uuid.uuid4().hex[:10]
    s.post(BASE + "/registro", data={"familia": f"E2E {tag}", "email": f"e2e_{tag}@mathelp.test", "password": "clave-e2e-123"}, allow_redirects=True)
    nombre = f"PCT-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creó el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


# --- resolver el enunciado ---------------------------------------------------

def resolver(html):
    m = re.search(r'pct-eq[^"]*" data-kind="(\w+)" data-p="(\d+)" data-n="(\d+)" data-p2="(\d+)"', html)
    assert m, "no llegó el enunciado (.pct-eq con data-*)"
    kind, p, n, p2 = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    if kind == "simple":
        return n * p // 100
    if kind == "descuento":
        return n - n * p // 100
    if kind == "iva":
        return n + n * 21 // 100
    if kind == "recargo":
        return n + n * p // 100
    if kind == "sucesivos":
        n1 = n - n * p // 100
        return n1 - n1 * p2 // 100
    raise AssertionError(f"kind desconocido: {kind}")


# --- socket ------------------------------------------------------------------

def open_ws(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(BASE.replace("http", "ws") + "/live/porcentaje", header=[f"Cookie: {cookies}"], timeout=10)
    html = json.loads(ws.recv()).get("html", "")
    cid = re.search(r'data-flv-value-instance_id="([^"]+)"', html).group(1)
    return ws, cid, html


def answer(ws, cid, ei, valor):
    ws.send(json.dumps({"event": "digito", "payload": {"d": "1", "component_name": "porcentaje", "instance_id": cid}, "html": "", "patches": []}))
    ws.recv()
    ws.send(json.dumps({"event": "answer", "payload": {"v": str(valor), "ei": str(ei), "touched": "1", "component_name": "porcentaje", "instance_id": cid}, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def jugar_ronda(grado):
    s = requests.Session()
    pid = setup_perfil(s, grado)
    rp = s.get(BASE + "/porcentaje")
    assert rp.status_code == 200, f"GET /porcentaje -> {rp.status_code}"
    assert 'pct-eq' in rp.text, "el SSR no trae el enunciado"

    ws, cid, html = open_ws(s)
    fb_con_seq = False
    vio_racha = False
    for ei in range(LIMIT):
        sol = resolver(html)
        html = answer(ws, cid, ei, sol)
        if 'class="q-fb' in html and "data-fb-seq" in html:
            fb_con_seq = True
        if "q-racha" in html:
            vio_racha = True
        if "q-done" not in html:
            assert "q-progress" in html, f"grade {grado} turno {ei}: falta la barra de progreso"
        time.sleep(0.05)
    assert fb_con_seq, f"grade {grado}: el feedback no emite data-fb-seq (sonido muerto)"
    assert vio_racha, f"grade {grado}: nunca apareció la insignia de racha"
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)
    assert "mh-estrellas" in html and 'class="mh-aliento"' in html, f"grade {grado}: la pantalla final no trae estrellas"
    assert "mh-estrellas perfect" in html, f"grade {grado}: 10/10 debería marcar ronda perfecta"
    assert "mh-confetti" in html, f"grade {grado}: 10/10 debería tirar confetti"
    assert "mh-record" in html, f"grade {grado}: primera ronda 10/10 debería ser NUEVO récord"

    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND mode='pct' AND topic_code='pct' ORDER BY id DESC LIMIT 1")
    assert sid, "no se creó la sesión de Porcentaje (pct/pct)"
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}"))
    n_ok = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND correct"))
    rec = psql(f"SELECT best_streak FROM profile_game_stats WHERE profile_id={pid} AND game_code='porcentaje'")
    assert rec == "10", f"grade {grado}: récord guardado debería ser 10, fue '{rec}'"
    print(f"  grade {grado}: perfil={pid} attempts={n_att} correctos={n_ok} record={rec}")
    assert n_att == LIMIT, f"grade {grado}: esperaba {LIMIT} attempts, hubo {n_att}"
    assert n_ok == LIMIT, f"grade {grado}: calculé todo pero solo {n_ok} quedaron correctos"
    return n_ok


def escenario():
    s0 = requests.Session()
    setup_perfil(s0, 8)
    r = s0.get(BASE + "/juegos")
    assert r.status_code == 200, f"GET /juegos -> {r.status_code}"
    assert 'href="/porcentaje"' in r.text, "no aparece la carta Porcentaje"
    # Grado 6 (% simple/descuento) y grado 13 (descuentos sucesivos, nivel 5).
    g6 = jugar_ronda(6)
    g13 = jugar_ronda(13)
    return {"aparece": True, "g6_ok": g6, "g13_ok": g13}


def run_server(cmd, label):
    print(f"[{label}] arrancando: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd="d:/MathHelp", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_up():
            raise RuntimeError(f"[{label}] el server no levantó")
        time.sleep(2.5)
        return escenario()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        time.sleep(1.0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["run", "build"])
    ARGS = ap.parse_args()
    results = {}
    if ARGS.only in (None, "run"):
        results["run"] = run_server(["fitz", "run"], "fitz run")
    if ARGS.only in (None, "build"):
        results["build"] = run_server(["d:/MathHelp/target/release/mathelp.exe"], "binario")
    print("\n=== RESULTADO ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print("\nOK: Porcentaje E2E verde." if results else "nada que correr")
