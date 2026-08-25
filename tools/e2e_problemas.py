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
    if "en total" in enun or "in total" in enun:              # total = N · X
        x = _monies(enun)[0]
        n = _plain_ints(enun)[0]
        return n * x
    if "unidades y pag" in enun or "units and pay" in enun:   # oferta = Y − N·X
        x, y = _monies(enun)
        n = _plain_ints(enun)[0]
        return y - n * x
    if "de vuelto" in enun or "change do you get" in enun:     # vuelto = Y − X
        x, y = _monies(enun)
        return y - x
    if "entre" in enun or "among" in enun:                     # reparto = T / N
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


def escenario():
    s = requests.Session()
    pid = setup_perfil(s, 7)

    r = s.get(BASE + "/juegos")
    assert r.status_code == 200, f"GET /juegos -> {r.status_code}"
    assert 'href="/problemas"' in r.text, "no aparece la carta Problemas"

    rp = s.get(BASE + "/problemas")
    assert rp.status_code == 200, f"GET /problemas -> {rp.status_code}"
    assert 'class="ki-preg"' in rp.text, "el SSR no trae el enunciado"

    ws, cid, html = open_ws(s)
    for ei in range(LIMIT):
        enun = extraer_enun(html)
        sol = resolver(enun)
        html = answer(ws, cid, ei, sol)
        time.sleep(0.05)
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)

    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND mode='kiosco' AND topic_code='problemas' ORDER BY id DESC LIMIT 1")
    assert sid, "no se creó la sesión de Problemas (kiosco/problemas)"
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}"))
    n_ok = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND correct"))
    skills = set(psql(f"SELECT DISTINCT skill_code FROM attempts WHERE session_id={sid}").split("\n"))
    print(f"  perfil={pid} sesion={sid} attempts={n_att} correctos={n_ok} skills={sorted(skills)}")
    assert n_att == LIMIT, f"esperaba {LIMIT} attempts, hubo {n_att}"
    assert n_ok == LIMIT, f"resolví todos pero solo {n_ok} quedaron correctos"
    # variedad real: un 7° ve más de un tipo de operación (no sólo vueltos).
    assert len(skills) >= 2, f"esperaba variedad de problemas, sólo hubo {skills}"

    return {"aparece": True, "attempts": n_att, "correctos": n_ok, "skills": sorted(skills)}


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
