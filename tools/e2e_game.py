#!/usr/bin/env python3
# tools/e2e_game.py — E2E de un juego (HTTP auth + WS + verificación en Postgres).
#
# Reusable: corré con --route/--ws/--component/--mode para cualquier juego que
# use el patrón LiveComponent + @ws (contrarreloj, V/F, ...). Registra una familia
# fresca, crea un perfil de grado 4, entra, abre la página del juego, juega N
# respuestas por WebSocket y verifica que persistió (sesión con el `mode` dado +
# attempts + mastery movido). Se corre contra `fitz run` y contra el binario para
# comprobar paridad.
#
# Requiere: requests, websocket-client, y psql en el PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_game.py --route /vf --ws /live/vf --component verdadero_falso --mode truefalse

import argparse, json, os, re, subprocess, sys, time, uuid
import requests
import websocket  # websocket-client

BASE = "http://127.0.0.1:3000"
PSQL = os.environ.get("FITZ_PSQL", r"C:\Program Files\PostgreSQL\15\bin\psql.exe")
PGENV = {**os.environ, "PGPASSWORD": "mathelp"}


def psql(sql):
    out = subprocess.run(
        [PSQL, "-h", "localhost", "-U", "mathelp", "-d", "mathelp", "-tAc", sql],
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


def setup_perfil(s):
    """Registra una familia fresca + perfil grado 4 sin PIN, lo elige. Devuelve profile_id."""
    tag = uuid.uuid4().hex[:10]
    email = f"e2e_{tag}@mathelp.test"
    s.post(BASE + "/registro", data={"familia": f"E2E {tag}", "email": email, "password": "clave-e2e-123"},
           allow_redirects=True)
    nombre = f"E2E-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": "4", "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    if not pid:
        raise RuntimeError("no se creó el perfil")
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid), nombre


def play(args):
    s = requests.Session()
    pid, nombre = setup_perfil(s)

    # GET de la página del juego: debe traer el componente SSR.
    r = s.get(BASE + args.route)
    assert r.status_code == 200, f"GET {args.route} -> {r.status_code}"
    assert f'data-flv-component-name="{args.component}"' in r.text, "sin componente SSR"

    # WS: cookies de sesión + idioma van en el header Cookie del handshake.
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(
        BASE.replace("http", "ws") + args.ws,
        header=[f"Cookie: {cookies}"], timeout=10,
    )
    # Primer frame del server: trae el instance_id (cid) en el HTML.
    first = json.loads(ws.recv())
    cid_m = re.search(r'data-flv-value-instance_id="([^"]+)"', first.get("html", ""))
    assert cid_m, "no llegó el instance_id en el primer frame"
    cid = cid_m.group(1)

    # Jugamos N respuestas. `v` alterna; `ei` es el índice esperado (0,1,2,...).
    for i in range(args.n):
        payload = {args.value_key: args.values[i % len(args.values)], "ei": str(i),
                   "component_name": args.component, "instance_id": cid}
        ws.send(json.dumps({"event": args.event, "payload": payload, "html": "", "patches": []}))
        ws.recv()  # frame de respuesta
        time.sleep(0.05)
    ws.close()
    time.sleep(0.4)  # dar tiempo a los writes best-effort

    # Verificación en Postgres.
    sess = psql(f"SELECT id, total, correct FROM sessions WHERE profile_id={pid} AND mode='{args.mode}' ORDER BY id DESC LIMIT 1")
    assert sess, f"no se creó la sesión mode={args.mode}"
    sid, total, correct = sess.split("|")
    n_att = psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}")
    n_mast = psql(f"SELECT count(*) FROM mastery WHERE profile_id={pid}")
    n_streak = psql(f"SELECT count(*) FROM streaks WHERE profile_id={pid} AND day=CURRENT_DATE")
    print(f"  perfil={pid} sesión={sid} mode={args.mode} total={total} attempts={n_att} mastery_rows={n_mast} streak_hoy={n_streak}")
    assert int(n_att) == args.n, f"attempts esperados {args.n}, hubo {n_att}"
    assert int(n_mast) >= 1, "mastery no se movió"
    assert int(n_streak) == 1, "racha del día no se registró"
    # Invariantes DETERMINISTAS (comparables run↔build). El nº exacto de filas de
    # mastery NO lo es: cada partida usa un seed random fresco → distinto set de
    # operaciones tocadas. La paridad real (mismo seed+idx ⇒ mismo ejercicio) la
    # garantizan los generadores deterministas + que el binario compile.
    return {"attempts": int(n_att), "mastery_movido": int(n_mast) >= 1, "racha_hoy": int(n_streak) == 1}


def run_server(cmd, label):
    print(f"[{label}] arrancando: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd="d:/MathHelp", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_up():
            raise RuntimeError(f"[{label}] el server no levantó")
        return play(ARGS)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        time.sleep(1.0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", required=True)
    ap.add_argument("--ws", required=True)
    ap.add_argument("--component", required=True)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--event", default="answer")
    ap.add_argument("--value-key", default="v")
    ap.add_argument("--values", default="1,0", help="valores de `v` que se rotan")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--only", choices=["run", "build"], help="correr sólo run o sólo build")
    ARGS = ap.parse_args()
    ARGS.values = ARGS.values.split(",")

    results = {}
    if ARGS.only in (None, "run"):
        results["run"] = run_server(["fitz", "run"], "fitz run")
    if ARGS.only in (None, "build"):
        results["build"] = run_server(["d:/MathHelp/target/release/mathelp.exe"], "binario")

    print("RESULTADOS:", json.dumps(results))
    if "run" in results and "build" in results:
        assert results["run"] == results["build"], "PARIDAD ROTA run vs build"
        print("OK - paridad run vs build correcta")
    else:
        print("OK")
