#!/usr/bin/env python3
# tools/e2e_ordenar.py — E2E del juego "Ordenar" (de menor a mayor, F9).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil -> GET /juegos muestra "Ordenar" (href="/ordenar").
#   2. GET /ordenar -> el SSR trae la grilla de cartas.
#   3. Abre WS /live/ordenar; parsea las cartas (pos + texto), calcula el VALOR de
#      cada una (natural / decimal "x,y" / fracción "n/d" / entero), las ORDENA
#      ascendente y las toca en ese orden.
#   4. Verifica: data-fb-seq, q-racha, q-progress, estrellas, ronda perfecta +
#      confetti + récord; y en Postgres: sesión mode='ordenar' topic 'ordenar', K
#      attempts TODOS correctos, best_streak=K en profile_game_stats.
#
# Requiere: requests, websocket-client, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_ordenar.py --only build   (o --only run, o ambos)

import argparse, json, os, re, subprocess, time, uuid
import requests
import websocket  # websocket-client

BASE = "http://127.0.0.1:3000"
PSQL = os.environ.get("FITZ_PSQL", r"C:\Program Files\PostgreSQL\15\bin\psql.exe")
PGUSER = os.environ.get("FITZ_PGUSER", "postgres")
PGPASS = os.environ.get("FITZ_PGPASS", "123mgp")
PGDB = os.environ.get("FITZ_PGDB", "mathelp")
PGENV = {**os.environ, "PGPASSWORD": PGPASS}


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
    nombre = f"ORD-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creó el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


# --- parsear + valuar las cartas --------------------------------------------

def valor(text):
    text = text.strip()
    if "/" in text:
        n, d = text.split("/")
        return int(n) / int(d)
    if "," in text:
        return float(text.replace(",", "."))
    return float(text)


def parse_cartas(html):
    cards = re.findall(r'ord-card[^"]*" type="button" data-flv-click="place" data-flv-value-pos="(\d+)">([^<]+)</button>', html)
    return [(int(pos), txt.strip()) for pos, txt in cards]


# --- socket ------------------------------------------------------------------

def open_ws(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(BASE.replace("http", "ws") + "/live/ordenar", header=[f"Cookie: {cookies}"], timeout=10)
    html = json.loads(ws.recv()).get("html", "")
    cid = re.search(r'data-flv-value-instance_id="([^"]+)"', html).group(1)
    return ws, cid, html


def place(ws, cid, pos):
    ws.send(json.dumps({"event": "place", "payload": {"pos": str(pos), "component_name": "ordenar", "instance_id": cid}, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def jugar_ronda(grado):
    s = requests.Session()
    pid = setup_perfil(s, grado)
    rp = s.get(BASE + "/ordenar")
    assert rp.status_code == 200, f"GET /ordenar -> {rp.status_code}"
    assert 'ord-grid' in rp.text, "el SSR no trae la grilla"

    ws, cid, html = open_ws(s)
    cartas = parse_cartas(html)
    assert len(cartas) >= 5, f"grade {grado}: esperaba >= 5 cartas, hubo {len(cartas)}"
    k = len(cartas)
    # ordenar las posiciones por valor ascendente.
    orden = sorted(cartas, key=lambda pt: valor(pt[1]))
    # sin empates (claves distintas).
    vals = [valor(t) for _, t in cartas]
    assert len(set(vals)) == k, f"grade {grado}: hay valores repetidos {vals}"

    fb_con_seq = False
    vio_racha = False
    for pos, _ in orden:
        html = place(ws, cid, pos)
        if 'class="q-fb' in html and "data-fb-seq" in html:
            fb_con_seq = True
        if "q-racha" in html:
            vio_racha = True
        if "q-done" not in html:
            assert "q-progress" in html, f"grade {grado}: falta la barra de progreso"
        time.sleep(0.05)

    assert fb_con_seq, f"grade {grado}: el feedback no emite data-fb-seq (sonido muerto)"
    assert vio_racha, f"grade {grado}: nunca apareció la insignia de racha"
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)
    assert "mh-estrellas" in html, f"grade {grado}: la pantalla final no trae estrellas"
    assert "mh-estrellas perfect" in html, f"grade {grado}: sin errores debería ser ronda perfecta"
    assert "mh-confetti" in html, f"grade {grado}: ronda perfecta debería tirar confetti"
    assert "mh-record" in html, f"grade {grado}: primera ronda debería ser NUEVO récord"

    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND mode='ordenar' AND topic_code='ordenar' ORDER BY id DESC LIMIT 1")
    assert sid, "no se creó la sesión de Ordenar (ordenar/ordenar)"
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}"))
    n_ok = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND correct"))
    rec = psql(f"SELECT best_streak FROM profile_game_stats WHERE profile_id={pid} AND game_code='ordenar'")
    assert rec == str(k), f"grade {grado}: récord debería ser {k}, fue '{rec}'"
    print(f"  grade {grado}: perfil={pid} cartas={k} attempts={n_att} correctos={n_ok} record={rec}")
    assert n_att == k, f"grade {grado}: esperaba {k} attempts, hubo {n_att}"
    assert n_ok == k, f"grade {grado}: ordené bien pero solo {n_ok} quedaron correctos"
    return k


def escenario():
    s0 = requests.Session()
    setup_perfil(s0, 3)
    r = s0.get(BASE + "/juegos")
    assert r.status_code == 200, f"GET /juegos -> {r.status_code}"
    assert 'href="/ordenar"' in r.text, "no aparece la carta Ordenar"
    # Grado 2 (naturales) y grado 13 (fracciones/decimales mezclados, 6 cartas).
    g2 = jugar_ronda(2)
    g13 = jugar_ronda(13)
    return {"aparece": True, "g2_cartas": g2, "g13_cartas": g13}


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
    print("\nOK: Ordenar E2E verde." if results else "nada que correr")
