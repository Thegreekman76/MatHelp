#!/usr/bin/env python3
# tools/e2e_trig.py — E2E del juego "Trigonometría" (F7.4).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil común grado 10 -> GET /juegos muestra Trigonometría.
#   2. GET /trigonometria -> el SSR trae la figura SVG (triángulo).
#   3. Abre WS /live/trigonometria, y en cada turno: parsea la FIGURA SVG del
#      frame vivo (etiquetas de los lados + ángulo), la RESUELVE (Pitágoras /
#      razón 30°) y tipea la respuesta. **Verifica que el SVG SOBREVIVE el diff de
#      LiveView en cada tick (FLV-02): las 3 <text class="tg-lbl"> siguen ahí.**
#   4. Verifica en Postgres: sesión mode='numpad' topic 'trig', 10 attempts, TODOS
#      correctos, ended_at seteado.
#
# Requiere: requests, websocket-client, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_trig.py --only build   (o --only run, o ambos)

import argparse, json, math, os, re, subprocess, time, uuid
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
    email = f"e2e_{tag}@mathelp.test"
    s.post(BASE + "/registro", data={"familia": f"E2E {tag}", "email": email, "password": "clave-e2e-123"}, allow_redirects=True)
    nombre = f"TRIG-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    if not pid:
        raise RuntimeError("no se creó el perfil")
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


# --- resolver leyendo la FIGURA SVG ------------------------------------------

def _num(t):
    d = re.sub(r"[^\d]", "", t)
    return int(d) if d else None


def isqrt_exact(n):
    r = math.isqrt(n)
    assert r * r == n, f"{n} no es cuadrado perfecto (figura corrupta?)"
    return r


def resolver_figura(html):
    # Las 3 etiquetas de lado, en orden de DOM: [horiz, vert, hyp].
    lbls = re.findall(r'<text[^>]*class="tg-lbl"[^>]*>(.*?)</text>', html, re.S)
    assert len(lbls) == 3, f"la figura SVG no tiene 3 etiquetas (diff corrupto?): {lbls!r}"
    horiz, vert, hyp = [x.strip() for x in lbls]
    ang_m = re.search(r'<text[^>]*class="tg-ang"[^>]*>(\d+)', html)
    ang = int(ang_m.group(1)) if ang_m else 0

    if ang == 30:
        # razón 30°: sin(30)=1/2. modo0: hyp dada, vert="?" -> hyp/2.
        #            modo1: vert dado, hyp="?" -> vert*2.
        if hyp == "?":
            return _num(vert) * 2
        return _num(hyp) // 2
    if hyp == "?":                 # Pitágoras: hallar hipotenusa
        return isqrt_exact(_num(horiz) ** 2 + _num(vert) ** 2)
    # Pitágoras: hallar cateto (vert="?"), con horiz + hyp
    return isqrt_exact(_num(hyp) ** 2 - _num(horiz) ** 2)


def figura_presente(html):
    return "<svg" in html and 'class="tg-tri"' in html and len(re.findall(r'class="tg-lbl"', html)) == 3


# --- socket ------------------------------------------------------------------

def open_ws(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(
        BASE.replace("http", "ws") + "/live/trigonometria",
        header=[f"Cookie: {cookies}"], timeout=10,
    )
    first = json.loads(ws.recv())
    html = first.get("html", "")
    cid_m = re.search(r'data-flv-value-instance_id="([^"]+)"', html)
    assert cid_m, "no llegó el instance_id en el primer frame"
    return ws, cid_m.group(1), html


def digito(ws, cid, d):
    payload = {"d": str(d), "component_name": "trig", "instance_id": cid}
    ws.send(json.dumps({"event": "digito", "payload": payload, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def answer(ws, cid, ei, valor):
    payload = {"v": str(valor), "ei": str(ei), "touched": "1", "component_name": "trig", "instance_id": cid}
    ws.send(json.dumps({"event": "answer", "payload": payload, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def escenario():
    s = requests.Session()
    pid = setup_perfil(s, 10)

    # 1) /juegos muestra Trigonometría.
    r = s.get(BASE + "/juegos")
    assert r.status_code == 200, f"GET /juegos -> {r.status_code}"
    assert 'href="/trigonometria"' in r.text, "no aparece la carta Trigonometría"

    # 2) SSR de /trigonometria trae la figura.
    rp = s.get(BASE + "/trigonometria")
    assert rp.status_code == 200, f"GET /trigonometria -> {rp.status_code}"
    assert "<svg" in rp.text and 'class="tg-tri"' in rp.text, "el SSR no trae la figura SVG"

    # 3) Jugar 10, resolviendo desde la figura del frame vivo (y verificando que el
    #    SVG sobrevive el diff en cada tick).
    ws, cid, html = open_ws(s)
    for ei in range(LIMIT):
        assert figura_presente(html), f"turno {ei}: el diff corrompió el SVG del frame vivo"
        sol = resolver_figura(html)
        digito(ws, cid, 1)          # marca touched en el server
        html = answer(ws, cid, ei, sol)
        time.sleep(0.05)
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)

    # 4) Verificación en Postgres.
    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND mode='numpad' AND topic_code='trig' ORDER BY id DESC LIMIT 1")
    assert sid, "no se creó la sesión de Trigonometría (numpad/trig)"
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}"))
    n_ok = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND correct"))
    ended = psql(f"SELECT (ended_at IS NOT NULL) FROM sessions WHERE id={sid}")
    print(f"  perfil={pid} sesion={sid} mode=numpad/trig attempts={n_att} correctos={n_ok} ended={ended}")
    assert n_att == LIMIT, f"esperaba {LIMIT} attempts, hubo {n_att}"
    assert n_ok == LIMIT, f"resolví todos pero solo {n_ok} quedaron correctos"
    assert ended == "t", "la sesión no cerró su ciclo (ended_at nulo)"

    return {"juegos_ve": True, "svg_sobrevive_diff": True, "attempts": n_att, "correctos": n_ok, "ended": ended == "t"}


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
    print("\nOK: Trigonometría E2E verde." if results else "nada que correr")
