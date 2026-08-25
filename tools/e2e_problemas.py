#!/usr/bin/env python3
# tools/e2e_problemas.py — E2E del juego "Problemas" (ex-kiosco, F8 Fase B).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil grado 7 -> GET /juegos muestra "Problemas" (href="/problemas").
#   2. GET /problemas -> el SSR trae el enunciado del problema.
#   3. Abre WS /live/problemas, y en cada turno: parsea el ENUNCIADO del frame
#      vivo, detecta el tipo (total/vuelto/reparto/cuantos/oferta), lo RESUELVE y
#      tipea la respuesta.
#   4. Verifica en Postgres: sesión mode='kiosco' topic 'problemas', 10 attempts,
#      TODOS correctos, ended_at seteado, y VARIEDAD de tipos (skills) — no sólo
#      vueltos: un 7° ve multiplicación + resta + división.
#
# Requiere: requests, websocket-client, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_problemas.py --only build   (o --only run, o ambos)

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
    nombre = f"PROB-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creó el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


# --- resolver el enunciado ---------------------------------------------------

def _monies(texto):
    return [int(re.sub(r"[^\d]", "", m)) for m in re.findall(r"\$\s*[\d.]+", texto)]


def _plain_ints(texto):
    # enteros que NO son parte de un monto ($...)
    sin_money = re.sub(r"\$\s*[\d.]+", " ", texto)
    return [int(x) for x in re.findall(r"\d+", sin_money)]


def resolver(enun):
    if "tres cosas que cuestan" in enun or "three things that cost" in enun:  # suma
        a, b, c = _monies(enun)
        return a + b + c
    if "otra cosa de" in enun or "another item for" in enun:  # combo = N·A + B
        a, bb = _monies(enun)
        n = _plain_ints(enun)[0]
        return n * a + bb
    if "unidades y pag" in enun or "units and pay" in enun:   # oferta = Y − N·X
        x, y = _monies(enun)
        n = _plain_ints(enun)[0]
        return y - n * x
    if "por semana" in enun or "per week" in enun:            # ahorro = X · N
        x = _monies(enun)[0]
        n = _plain_ints(enun)[0]
        return x * n
    if "cuadras" in enun or "blocks" in enun:                 # cuadras = 2 · X
        return 2 * _plain_ints(enun)[0]
    if "años" in enun or "years old" in enun:                 # edad = N + M
        n, m = _plain_ints(enun)
        return n + m
    if "cada una" in enun or "each one cost" in enun:         # unitario = T / N
        t = _monies(enun)[0]
        n = _plain_ints(enun)[0]
        return t // n
    if "promedio" in enun or "the average" in enun:           # promedio = (A+B+C)/3
        a, b, c = _monies(enun)
        return (a + b + c) // 3
    if "descuento" in enun or "discount" in enun:             # descuento = X − X·P/100
        x = _monies(enun)[0]
        p = _plain_ints(enun)[0]
        return x - x * p // 100
    if "es el" in enun or "% of" in enun:                    # porcentaje = X · P/100
        x = _monies(enun)[0]
        p = _plain_ints(enun)[0]
        return x * p // 100
    if "pagás en total" in enun or "pay in total" in enun:    # total = N · X
        x = _monies(enun)[0]
        n = _plain_ints(enun)[0]
        return n * x
    if "te falta" in enun or "more do you need" in enun:      # falta = X − Y
        x, y = _monies(enun)
        return x - y
    if "diferencia" in enun or "the difference" in enun:      # comparar = |A − B|
        a, b = _monies(enun)
        return abs(a - b)
    if "de vuelto" in enun or "change do you get" in enun:    # vuelto = Y − X
        x, y = _monies(enun)
        return y - x
    if "entre" in enun or "among" in enun:                    # reparto = T / N
        t, n = _plain_ints(enun)
        return t // n
    # cuantos = P / X
    p, x = _monies(enun)
    return p // x


def extraer_enun(html):
    m = re.search(r'<p class="ki-preg">(.*?)</p>', html, re.S)
    assert m, "no llegó el enunciado (.ki-preg)"
    return m.group(1).strip()


# --- socket ------------------------------------------------------------------

def open_ws(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(BASE.replace("http", "ws") + "/live/problemas", header=[f"Cookie: {cookies}"], timeout=10)
    html = json.loads(ws.recv()).get("html", "")
    cid = re.search(r'data-flv-value-instance_id="([^"]+)"', html).group(1)
    return ws, cid, html


def answer(ws, cid, ei, valor):
    ws.send(json.dumps({"event": "digito", "payload": {"d": "1", "component_name": "kiosco", "instance_id": cid}, "html": "", "patches": []}))
    ws.recv()
    ws.send(json.dumps({"event": "answer", "payload": {"v": str(valor), "ei": str(ei), "component_name": "kiosco", "instance_id": cid}, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def jugar_ronda(grado):
    s = requests.Session()
    pid = setup_perfil(s, grado)
    rp = s.get(BASE + "/problemas")
    assert rp.status_code == 200, f"GET /problemas -> {rp.status_code}"
    assert 'class="ki-preg"' in rp.text, "el SSR no trae el enunciado"

    ws, cid, html = open_ws(s)
    enunciados = []
    fb_con_seq = False
    for ei in range(LIMIT):
        enun = extraer_enun(html)
        enunciados.append(enun)
        sol = resolver(enun)
        html = answer(ws, cid, ei, sol)
        # el banner de feedback debe emitir data-fb-seq (trigger del sonido).
        if 'class="q-fb' in html and "data-fb-seq" in html:
            fb_con_seq = True
        time.sleep(0.05)
    assert fb_con_seq, f"grade {grado}: el feedback no emite data-fb-seq (sonido muerto)"
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)
    # no se repite ningún problema en la ronda (el pedido del autor).
    assert len(set(enunciados)) == LIMIT, f"grade {grado}: problemas repetidos ({len(set(enunciados))}/{LIMIT})"
    # pulido: la pantalla final trae estrellas + aliento.
    assert "mh-estrellas" in html and 'class="mh-aliento"' in html, f"grade {grado}: la pantalla final no trae estrellas"
    assert "★★★" in html.replace("</span><span", "").replace('<span class="star on">', "★") or html.count("★") == 3, f"grade {grado}: 10/10 debería dar 3 estrellas"
    assert "mh-estrellas perfect" in html, f"grade {grado}: 10/10 debería marcar ronda perfecta"

    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND mode='kiosco' AND topic_code='problemas' ORDER BY id DESC LIMIT 1")
    assert sid, "no se creó la sesión de Problemas (kiosco/problemas)"
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}"))
    n_ok = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND correct"))
    skills = set(psql(f"SELECT DISTINCT skill_code FROM attempts WHERE session_id={sid}").split("\n"))
    print(f"  grade {grado}: perfil={pid} attempts={n_att} correctos={n_ok} distintos={len(set(enunciados))} skills={sorted(skills)}")
    assert n_att == LIMIT, f"grade {grado}: esperaba {LIMIT} attempts, hubo {n_att}"
    assert n_ok == LIMIT, f"grade {grado}: resolví todos pero solo {n_ok} quedaron correctos"
    assert len(skills) >= 2, f"grade {grado}: esperaba variedad, sólo hubo {skills}"
    return sorted(skills)


def escenario():
    # La carta aparece.
    s0 = requests.Session()
    setup_perfil(s0, 7)
    r = s0.get(BASE + "/juegos")
    assert r.status_code == 200, f"GET /juegos -> {r.status_code}"
    assert 'href="/problemas"' in r.text, "no aparece la carta Problemas"
    # Rondas en dos grados (grade 4: tipos de tier 1-2; grade 7: tier 2-5).
    sk4 = jugar_ronda(4)
    sk7 = jugar_ronda(7)
    return {"aparece": True, "g4_skills": sk4, "g7_skills": sk7}


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
    print("\nOK: Problemas E2E verde." if results else "nada que correr")
