#!/usr/bin/env python3
# tools/e2e_fase_c.py — E2E del arranque adaptativo cross-sesión (F8 Fase C).
#
# Prueba que el rating de mastery del juego nudgea el NIVEL de arranque: dos
# perfiles de 1° secundaria (grade 8) juegan Ecuaciones —
#   A) con rating alto en la destreza ancla "ec.lineal" (viene de sesiones
#      anteriores) -> arranca en cuadrática (difficulty >= 2);
#   B) a ciegas (sin fila de mastery, rating 800) -> arranca en lineal (dif 1).
# No hace falta resolver: se contesta el idx 0 (mal) sólo para persistir el
# attempt, y se compara la `difficulty` (= nivel) del primer ejercicio.
#
# Uso:  python tools/e2e_fase_c.py --only build   (o --only run, o ambos)

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
    nombre = f"FC-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creó el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


def set_rating(pid, skill, rating):
    psql(
        "INSERT INTO mastery (profile_id, skill_code, rating, seen, hits, streak, avg_ms, last_seen_at, due_at) "
        f"VALUES ({pid}, '{skill}', {rating}, 20, 18, 5, 0, NOW(), NOW()) "
        "ON CONFLICT (profile_id, skill_code) DO UPDATE SET rating = EXCLUDED.rating"
    )


def jugar_idx0(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(BASE.replace("http", "ws") + "/live/ecuaciones", header=[f"Cookie: {cookies}"], timeout=10)
    html = json.loads(ws.recv()).get("html", "")
    cid = re.search(r'data-flv-value-instance_id="([^"]+)"', html).group(1)
    # Un dígito (marca touched en el server) + answer mal (v grande) para el idx 0.
    ws.send(json.dumps({"event": "digito", "payload": {"d": "9", "component_name": "ecuaciones", "instance_id": cid}, "html": "", "patches": []}))
    ws.recv()
    ws.send(json.dumps({"event": "answer", "payload": {"v": "999999", "ei": "0", "touched": "1", "component_name": "ecuaciones", "instance_id": cid}, "html": "", "patches": []}))
    ws.recv()
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)


def dif_idx0(pid):
    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND topic_code='ec' ORDER BY id DESC LIMIT 1")
    assert sid, "no hay sesión de ecuaciones"
    d = psql(f"SELECT difficulty FROM attempts WHERE session_id={sid} AND idx=0 LIMIT 1")
    assert d, "no se persistió el attempt del idx 0"
    return int(d)


def escenario():
    # A) grade 8 con rating alto en ec.lineal (viene de antes) → arranca boosteado.
    sa = requests.Session()
    pa = setup_perfil(sa, 8)
    set_rating(pa, "ec.lineal", 1200)      # delta +2 → grado efectivo 10
    jugar_idx0(sa)
    dif_a = dif_idx0(pa)

    # B) grade 8 a ciegas (sin mastery) → arranca en el piso de su grado.
    sb = requests.Session()
    pb = setup_perfil(sb, 8)
    jugar_idx0(sb)
    dif_b = dif_idx0(pb)

    print(f"  A (rating 1200): dif_idx0={dif_a}   B (a ciegas): dif_idx0={dif_b}")
    assert dif_b == 1, f"el perfil a ciegas debería arrancar en nivel 1, arrancó {dif_b}"
    assert dif_a >= 2, f"el perfil con mastery alto debería arrancar boosteado (>=2), arrancó {dif_a}"
    assert dif_a > dif_b, "el mastery no subió el nivel de arranque"

    return {"boosteado": dif_a, "a_ciegas": dif_b}


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
    print("\nOK: Fase C E2E verde." if results else "nada que correr")
