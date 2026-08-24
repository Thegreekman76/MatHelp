#!/usr/bin/env python3
# tools/e2e_funciones.py — E2E del juego "Funciones" (F7.5).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil común grado 11 -> GET /juegos muestra Funciones.
#   2. GET /funciones -> el SSR trae fórmula + gráfico SVG.
#   3. Abre WS /live/funciones, y en cada turno: parsea la FÓRMULA del frame vivo
#      (lineal / cuadrática / exponencial) + el punto x0 de la pregunta, evalúa
#      f(x0) y tipea la respuesta (que puede ser NEGATIVA). Verifica que la
#      fórmula (con <sup>) y el gráfico SVG SOBREVIVEN el diff en cada tick.
#   4. Verifica en Postgres: sesión mode='numpad' topic 'func', 10 attempts, TODOS
#      correctos, ended_at seteado.
#
# Requiere: requests, websocket-client, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_funciones.py --only build   (o --only run, o ambos)

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
MINUS = "−"   # − tipográfico que usa fmt_int


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
    email = f"e2e_{tag}@mathelp.test"
    s.post(BASE + "/registro", data={"familia": f"E2E {tag}", "email": email, "password": "clave-e2e-123"}, allow_redirects=True)
    nombre = f"FUNC-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    if not pid:
        raise RuntimeError("no se creó el perfil")
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


# --- resolver leyendo la FÓRMULA + el punto ----------------------------------

def _int(t):
    return int(t.replace(MINUS, "-").replace(" ", ""))


def extraer_formula(html):
    m = re.search(r'<div class="q-prompt fx-formula">(.*?)</div>', html, re.S)
    assert m, "no llegó la fórmula (.fx-formula) en el frame"
    return m.group(1).strip()


def extraer_x0(html):
    m = re.search(r'<div class="q-prompt fx-pregunta">(.*?)</div>', html, re.S)
    assert m, "no llegó la pregunta (.fx-pregunta)"
    fm = re.search(r"f\(([^)]+)\)", m.group(1))
    assert fm, f"no se pudo leer x0 de la pregunta: {m.group(1)!r}"
    return _int(fm.group(1))


def evaluar(formula, x0):
    # Exponencial: f(x) = [a·]base<sup>x</sup>
    if "<sup>x</sup>" in formula:
        m = re.search(r"=\s*(?:(\d+)·)?(\d+)<sup>x</sup>", formula)
        assert m, f"exp no parsea: {formula!r}"
        a = int(m.group(1)) if m.group(1) else 1
        base = int(m.group(2))
        return a * (base ** x0)
    f = formula.replace(MINUS, "-")
    # Cuadrática: f(x) = [a]x² [± b]  (chequear ANTES que la lineal)
    if "x²" in f:
        m = re.search(r"=\s*(-?\d*)x²\s*([+-]\s*\d+)?", f)
        assert m, f"cuad no parsea: {formula!r}"
        acoef = m.group(1)
        a = 1 if acoef == "" else int(acoef)
        b = _int(m.group(2)) if m.group(2) else 0
        return a * x0 * x0 + b
    # Lineal: f(x) = [a]x [± b]
    m = re.search(r"=\s*(-?\d*)x\s*([+-]\s*\d+)?", f)
    assert m, f"lin no parsea: {formula!r}"
    acoef = m.group(1)
    if acoef == "":
        a = 1
    elif acoef == "-":
        a = -1
    else:
        a = int(acoef)
    b = _int(m.group(2)) if m.group(2) else 0
    return a * x0 + b


def figura_ok(html):
    return "<svg" in html and 'class="fx-curve"' in html and "fx-formula" in html


# --- socket ------------------------------------------------------------------

def open_ws(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(
        BASE.replace("http", "ws") + "/live/funciones",
        header=[f"Cookie: {cookies}"], timeout=10,
    )
    first = json.loads(ws.recv())
    html = first.get("html", "")
    cid_m = re.search(r'data-flv-value-instance_id="([^"]+)"', html)
    assert cid_m, "no llegó el instance_id en el primer frame"
    return ws, cid_m.group(1), html


def digito(ws, cid, d):
    payload = {"d": str(d), "component_name": "funciones", "instance_id": cid}
    ws.send(json.dumps({"event": "digito", "payload": payload, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def answer(ws, cid, ei, valor):
    payload = {"v": str(valor), "ei": str(ei), "touched": "1", "component_name": "funciones", "instance_id": cid}
    ws.send(json.dumps({"event": "answer", "payload": payload, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def escenario():
    s = requests.Session()
    pid = setup_perfil(s, 11)

    r = s.get(BASE + "/juegos")
    assert r.status_code == 200, f"GET /juegos -> {r.status_code}"
    assert 'href="/funciones"' in r.text, "no aparece la carta Funciones"

    rp = s.get(BASE + "/funciones")
    assert rp.status_code == 200, f"GET /funciones -> {rp.status_code}"
    assert "<svg" in rp.text and "fx-formula" in rp.text, "el SSR no trae fórmula + gráfico"

    ws, cid, html = open_ws(s)
    for ei in range(LIMIT):
        assert figura_ok(html), f"turno {ei}: el diff corrompió la fórmula/gráfico"
        formula = extraer_formula(html)
        x0 = extraer_x0(html)
        sol = evaluar(formula, x0)
        digito(ws, cid, 1)          # marca touched
        html = answer(ws, cid, ei, sol)
        time.sleep(0.05)
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)

    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND mode='numpad' AND topic_code='func' ORDER BY id DESC LIMIT 1")
    assert sid, "no se creó la sesión de Funciones (numpad/func)"
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}"))
    n_ok = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND correct"))
    ended = psql(f"SELECT (ended_at IS NOT NULL) FROM sessions WHERE id={sid}")
    print(f"  perfil={pid} sesion={sid} mode=numpad/func attempts={n_att} correctos={n_ok} ended={ended}")
    assert n_att == LIMIT, f"esperaba {LIMIT} attempts, hubo {n_att}"
    assert n_ok == LIMIT, f"resolví todos pero solo {n_ok} quedaron correctos"
    assert ended == "t", "la sesión no cerró su ciclo (ended_at nulo)"

    return {"juegos_ve": True, "svg_sup_sobreviven": True, "attempts": n_att, "correctos": n_ok, "ended": ended == "t"}


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
    ap.add_argument("--only", choices=["run", "build"], help="correr sólo run o sólo build")
    ARGS = ap.parse_args()

    results = {}
    if ARGS.only in (None, "run"):
        results["run"] = run_server(["fitz", "run"], "fitz run")
    if ARGS.only in (None, "build"):
        results["build"] = run_server(["d:/MathHelp/target/release/mathelp.exe"], "binario")

    print("\n=== RESULTADO ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print("\nOK: Funciones E2E verde." if results else "nada que correr")
