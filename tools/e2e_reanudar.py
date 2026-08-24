#!/usr/bin/env python3
# tools/e2e_reanudar.py — E2E de "reanudar partida" (F6), sobre el Desafío del día.
#
# Escenario (contra `fitz run` o el binario):
#   1. Registra familia + perfil grado 4, lo elige.
#   2. Abre WS /live/desafio, responde 4 de 10, cierra el socket (partida a medias).
#   3. GET /desafio  -> pantalla de reanudar (link a /desafio/seguir + "sin terminar").
#   4. GET /desafio/seguir -> el juego (componente quiz).
#   5. Reabre el WS, responde los 6 restantes -> phase done -> se finaliza.
#   6. Verifica en Postgres: UNA sola sesión de desafío (la MISMA, reusada),
#      10 attempts, ended_at NO nulo (ciclo cerrado).
#   7. POST /desafio/nuevo sobre una partida a medias -> la abandona (ended_at set).
#
# Requiere: requests, websocket-client, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_reanudar.py --only build   (o --only run, o ambos)

import argparse, json, os, re, subprocess, sys, time, uuid
import requests
import websocket  # websocket-client

BASE = "http://127.0.0.1:3000"
PSQL = os.environ.get("FITZ_PSQL", r"C:\Program Files\PostgreSQL\15\bin\psql.exe")
PGUSER = os.environ.get("FITZ_PGUSER", "postgres")
PGPASS = os.environ.get("FITZ_PGPASS", "123mgp")
PGDB = os.environ.get("FITZ_PGDB", "mathelp")
PGENV = {**os.environ, "PGPASSWORD": PGPASS}
LIMIT = 10  # desafio_n()


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


def setup_perfil(s):
    tag = uuid.uuid4().hex[:10]
    email = f"e2e_{tag}@mathelp.test"
    s.post(BASE + "/registro", data={"familia": f"E2E {tag}", "email": email, "password": "clave-e2e-123"}, allow_redirects=True)
    nombre = f"REANU-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": "4", "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    if not pid:
        raise RuntimeError("no se creó el perfil")
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


def open_ws(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(
        BASE.replace("http", "ws") + "/live/desafio",
        header=[f"Cookie: {cookies}"], timeout=10,
    )
    first = json.loads(ws.recv())
    html = first.get("html", "")
    cid_m = re.search(r'data-flv-value-instance_id="([^"]+)"', html)
    assert cid_m, "no llegó el instance_id en el primer frame"
    return ws, cid_m.group(1), html


def answer(ws, cid, ei):
    payload = {"v": "1", "ei": str(ei), "component_name": "quiz", "instance_id": cid}
    ws.send(json.dumps({"event": "answer", "payload": payload, "html": "", "patches": []}))
    ws.recv()
    time.sleep(0.05)


def escenario():
    s = requests.Session()
    pid = setup_perfil(s)

    # 1) Jugar 4 de 10 y cortar.
    ws, cid, _ = open_ws(s)
    for ei in range(4):
        answer(ws, cid, ei)
    ws.close()
    time.sleep(0.4)

    s1 = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND mode='desafio' ORDER BY id DESC LIMIT 1")
    assert s1, "no se creó la sesión de desafío"
    n_att_1 = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={s1}"))
    assert n_att_1 == 4, f"esperaba 4 attempts, hubo {n_att_1}"

    # 2) GET /desafio -> pantalla de reanudar.
    r = s.get(BASE + "/desafio")
    assert r.status_code == 200, f"GET /desafio -> {r.status_code}"
    assert '/desafio/seguir' in r.text, "la pantalla de reanudar no ofrece /desafio/seguir"
    assert 'data-flv-component-name="quiz"' not in r.text, "GET /desafio mostró el juego en vez de reanudar"

    # 3) GET /desafio/seguir -> el juego.
    r2 = s.get(BASE + "/desafio/seguir")
    assert r2.status_code == 200, f"GET /desafio/seguir -> {r2.status_code}"
    assert 'data-flv-component-name="quiz"' in r2.text, "/desafio/seguir no trae el componente quiz"

    # 4) Reabrir el WS -> debe reanudar (mismo seed+idx, la misma sesión).
    ws2, cid2, _ = open_ws(s)
    sess_ct_mid = int(psql(f"SELECT count(*) FROM sessions WHERE profile_id={pid} AND mode='desafio'"))
    assert sess_ct_mid == 1, f"al reanudar se creó otra sesión (hay {sess_ct_mid}, esperaba 1)"

    # 5) Completar los 6 restantes (idx 4..9). phase done al llegar a 10.
    for ei in range(4, LIMIT):
        answer(ws2, cid2, ei)
    time.sleep(0.4)
    ws2.close()
    time.sleep(0.4)

    # 6) Verificación final: UNA sesión, 10 attempts, ended_at seteado.
    sess_ct = int(psql(f"SELECT count(*) FROM sessions WHERE profile_id={pid} AND mode='desafio'"))
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={s1}"))
    ended = psql(f"SELECT (ended_at IS NOT NULL) FROM sessions WHERE id={s1}")
    total = psql(f"SELECT total FROM sessions WHERE id={s1}")
    print(f"  perfil={pid} sesion={s1} sesiones_desafio={sess_ct} attempts={n_att} total={total} ended={ended}")
    assert sess_ct == 1, f"la partida no se reusó: {sess_ct} sesiones de desafío"
    assert n_att == LIMIT, f"esperaba {LIMIT} attempts en la sesión reusada, hubo {n_att}"
    assert ended == "t", "la sesión no cerró su ciclo (ended_at nulo)"

    # 7) "Empezar de nuevo": partida a medias -> POST /desafio/nuevo la abandona.
    s2 = requests.Session()
    pid2 = setup_perfil(s2)
    ws3, cid3, _ = open_ws(s2)
    for ei in range(3):
        answer(ws3, cid3, ei)
    ws3.close()
    time.sleep(0.4)
    sA = psql(f"SELECT id FROM sessions WHERE profile_id={pid2} AND mode='desafio' ORDER BY id DESC LIMIT 1")
    r3 = s2.post(BASE + "/desafio/nuevo", allow_redirects=False)
    assert r3.status_code in (302, 303), f"POST /desafio/nuevo -> {r3.status_code}"
    endedA = psql(f"SELECT (ended_at IS NOT NULL) FROM sessions WHERE id={sA}")
    assert endedA == "t", "empezar de nuevo no abandonó la partida anterior"
    r4 = s2.get(BASE + "/desafio")
    assert 'data-flv-component-name="quiz"' in r4.text, "tras empezar de nuevo, /desafio no arranca el juego"
    print(f"  empezar_nuevo: sesion_abandonada={sA} ended={endedA} -> /desafio arranca fresco OK")

    return {"reuso_sesion": sess_ct == 1, "attempts_totales": n_att, "ended": ended == "t", "empezar_nuevo": endedA == "t"}


def run_server(cmd, label):
    print(f"[{label}] arrancando: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd="d:/MathHelp", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_up():
            raise RuntimeError(f"[{label}] el server no levantó")
        time.sleep(2.5)  # warmup: el pool de DB del intérprete tarda un toque más
                         # que el `/` en estar listo (fitz run, no el binario).
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

    print("RESULTADOS:", json.dumps(results))
    if "run" in results and "build" in results:
        assert results["run"] == results["build"], "PARIDAD ROTA run vs build"
        print("OK - reanudar: paridad run vs build correcta")
    else:
        print("OK - reanudar")
