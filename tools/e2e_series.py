#!/usr/bin/env python3
# tools/e2e_series.py — E2E del juego "Series" (patrones numéricos, F8).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil -> GET /juegos muestra "Series" (href="/series").
#   2. GET /series -> el SSR trae la secuencia.
#   3. Abre WS /live/series; en cada turno parsea los 4 términos del frame vivo,
#      DETECTA la regla (aritmética/geométrica/cuadrados/Fibonacci/×2+1/diferencias
#      crecientes), calcula el 5º término y lo tipea.
#   4. Verifica: data-fb-seq (sonido), q-racha, q-progress, estrellas, ronda
#      perfecta + confetti + mejor racha; y en Postgres: sesión mode='series'
#      topic 'patron', 10 attempts, TODOS correctos, ended_at seteado.
#
# Requiere: requests, websocket-client, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_series.py --only build   (o --only run, o ambos)

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
    nombre = f"SER-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creó el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


# --- resolver la secuencia -------------------------------------------------

def resolver(terms):
    a, b, c, d = terms
    # Fibonacci (cada término = suma de los dos anteriores)
    if c == a + b and d == b + c:
        return c + d
    # ×2+1
    if b == a * 2 + 1 and c == b * 2 + 1 and d == c * 2 + 1:
        return d * 2 + 1
    # geométrica (duplicar/triplicar)
    if a != 0 and b % a == 0:
        r = b // a
        if r >= 2 and c == b * r and d == c * r:
            return d * r
    # diferencias constantes o crecientes (aritmética, cuadrados, triangulares)
    d1, d2, d3 = b - a, c - b, d - c
    e = d2 - d1
    if d3 - d2 == e:
        return d + (d3 + e)
    # fallback aritmético
    return d + d3


def extraer_terms(html):
    m = re.search(r'<div class="q-prompt cg-eq series-eq">(.*?)</div>', html, re.S)
    assert m, "no llegó la secuencia (.series-eq)"
    antes = m.group(1).split("<span")[0]           # "2, 4, 6, 8, "
    nums = [int(x) for x in re.findall(r'-?\d+', antes)]
    assert len(nums) == 4, f"esperaba 4 términos, hubo {nums}"
    return nums


# --- socket ------------------------------------------------------------------

def open_ws(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(BASE.replace("http", "ws") + "/live/series", header=[f"Cookie: {cookies}"], timeout=10)
    html = json.loads(ws.recv()).get("html", "")
    cid = re.search(r'data-flv-value-instance_id="([^"]+)"', html).group(1)
    return ws, cid, html


def answer(ws, cid, ei, valor):
    # un dígito para marcar `touched` en el componente; el valor real va en `v`.
    ws.send(json.dumps({"event": "digito", "payload": {"d": "1", "component_name": "series", "instance_id": cid}, "html": "", "patches": []}))
    ws.recv()
    ws.send(json.dumps({"event": "answer", "payload": {"v": str(valor), "ei": str(ei), "touched": "1", "component_name": "series", "instance_id": cid}, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def jugar_ronda(grado):
    s = requests.Session()
    pid = setup_perfil(s, grado)
    rp = s.get(BASE + "/series")
    assert rp.status_code == 200, f"GET /series -> {rp.status_code}"
    assert 'series-eq' in rp.text, "el SSR no trae la secuencia"

    ws, cid, html = open_ws(s)
    fb_con_seq = False
    vio_racha = False
    for ei in range(LIMIT):
        terms = extraer_terms(html)
        sol = resolver(terms)
        html = answer(ws, cid, ei, sol)
        if 'class="q-fb' in html and "data-fb-seq" in html:
            fb_con_seq = True
        if "q-racha" in html:
            vio_racha = True
        if "q-done" not in html:
            assert "q-progress" in html, f"grade {grado} turno {ei}: falta la barra de progreso"
        time.sleep(0.05)
    assert fb_con_seq, f"grade {grado}: el feedback no emite data-fb-seq (sonido muerto)"
    assert vio_racha, f"grade {grado}: nunca apareció la insignia de racha (10 aciertos seguidos)"
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)
    assert "mh-estrellas" in html and 'class="mh-aliento"' in html, f"grade {grado}: la pantalla final no trae estrellas"
    assert "mh-estrellas perfect" in html, f"grade {grado}: 10/10 debería marcar ronda perfecta"
    assert "mh-confetti" in html, f"grade {grado}: 10/10 debería tirar confetti"
    assert "mh-mejor-racha" in html, f"grade {grado}: 10/10 debería mostrar la mejor racha"

    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND mode='series' AND topic_code='patron' ORDER BY id DESC LIMIT 1")
    assert sid, "no se creó la sesión de Series (series/patron)"
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}"))
    n_ok = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND correct"))
    print(f"  grade {grado}: perfil={pid} attempts={n_att} correctos={n_ok}")
    assert n_att == LIMIT, f"grade {grado}: esperaba {LIMIT} attempts, hubo {n_att}"
    assert n_ok == LIMIT, f"grade {grado}: resolví todos pero solo {n_ok} quedaron correctos"
    return n_ok


def escenario():
    s0 = requests.Session()
    setup_perfil(s0, 3)
    r = s0.get(BASE + "/juegos")
    assert r.status_code == 200, f"GET /juegos -> {r.status_code}"
    assert 'href="/series"' in r.text, "no aparece la carta Series"
    # Grado 2 (nivel 1, aritméticas) y grado 13 (hasta nivel 5, Fibonacci/potencias).
    g2 = jugar_ronda(2)
    g13 = jugar_ronda(13)
    return {"aparece": True, "g2_ok": g2, "g13_ok": g13}


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
    print("\nOK: Series E2E verde." if results else "nada que correr")
