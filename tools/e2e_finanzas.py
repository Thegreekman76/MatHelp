#!/usr/bin/env python3
# tools/e2e_finanzas.py — E2E del juego "Finanzas" (F7.3, diferencial comercial).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil COMERCIAL grado 11 (Ciclo Orientado) -> GET /juegos muestra Finanzas.
#   2. Perfil COMÚN grado 11 -> GET /juegos NO muestra Finanzas.
#   3. Abre WS /live/finanzas, y en cada turno: parsea el problema (interés
#      simple/compuesto, porcentaje, descuento), lo RESUELVE, y tipea la respuesta.
#   4. Verifica en Postgres: sesión mode='story', 10 attempts, TODOS correctos
#      (resolvimos bien), ended_at seteado, prompts no vacíos.
#
# Requiere: requests, websocket-client, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_finanzas.py --only build   (o --only run, o ambos)

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


def ascii_safe(s):
    return s.encode("ascii", "replace").decode()


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


def setup_perfil(s, grado, modalidad):
    tag = uuid.uuid4().hex[:10]
    email = f"e2e_{tag}@mathelp.test"
    s.post(BASE + "/registro", data={"familia": f"E2E {tag}", "email": email, "password": "clave-e2e-123"}, allow_redirects=True)
    nombre = f"FIN-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    if not pid:
        raise RuntimeError("no se creó el perfil")
    # La modalidad se setea directo en la DB (dev): F7.0 la modela pero la UI de
    # selección de modalidad es harina de otro costal.
    psql(f"UPDATE profiles SET modalidad = '{modalidad}' WHERE id = {pid}")
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


# --- resolver el problema del enunciado --------------------------------------

def _money(m):  # "$ 1.000" (es-AR) -> 1000
    return int(re.sub(r"[^\d]", "", m))


def resolver(problema):
    # Punto de equilibrio: tres montos ($CF, $precio, $costo) → Q = CF/(P−C).
    if "unidades debe vender" in problema:
        cf, precio, costo = [_money(m) for m in re.findall(r"\$\s*[\d.]+", problema)]
        return cf // (precio - costo)
    # Los otros cuatro: un solo monto + enteros (tasas/plazos/porcentajes).
    mm = re.search(r"\$\s*[\d.]+", problema)
    money = _money(mm.group(0))
    resto = problema[:mm.start()] + problema[mm.end():]
    ints = [int(x) for x in re.findall(r"\d+", resto)]
    if "plazo fijo" in problema:            # interés simple
        rate, years = ints[0], ints[1]
        return money * rate * years // 100
    if "compuesto" in problema:             # interés compuesto
        rate, years = ints[0], ints[1]
        return money * ((100 + rate) ** years) // (100 ** years)
    if "descuento" in problema:             # descuento
        pct = ints[0]
        return money - money * pct // 100
    # porcentaje: "¿Cuánto es el P% de $base?"
    pct = ints[0]
    return money * pct // 100


def extraer_problema(html):
    m = re.search(r'<div class="fin-problema">(.*?)</div>', html, re.S)
    assert m, "no llegó el enunciado (.fin-problema) en el frame"
    return m.group(1).strip()


# --- socket ------------------------------------------------------------------

def open_ws(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(
        BASE.replace("http", "ws") + "/live/finanzas",
        header=[f"Cookie: {cookies}"], timeout=10,
    )
    first = json.loads(ws.recv())
    html = first.get("html", "")
    cid_m = re.search(r'data-flv-value-instance_id="([^"]+)"', html)
    assert cid_m, "no llegó el instance_id en el primer frame"
    return ws, cid_m.group(1), html


def digito(ws, cid, d):
    payload = {"d": str(d), "component_name": "finanzas", "instance_id": cid}
    ws.send(json.dumps({"event": "digito", "payload": payload, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def answer(ws, cid, ei, valor):
    payload = {"v": str(valor), "ei": str(ei), "touched": "1", "component_name": "finanzas", "instance_id": cid}
    ws.send(json.dumps({"event": "answer", "payload": payload, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def escenario():
    # 1) Perfil comercial: /juegos muestra Finanzas.
    sc = requests.Session()
    pid_com = setup_perfil(sc, 11, "comercial")
    r = sc.get(BASE + "/juegos")
    assert r.status_code == 200, f"GET /juegos (comercial) -> {r.status_code}"
    assert 'href="/finanzas"' in r.text, "el perfil COMERCIAL no ve la carta Finanzas"

    # 2) Perfil común (mismo grado): NO ve Finanzas.
    su = requests.Session()
    pid_com2 = setup_perfil(su, 11, "comun")
    r2 = su.get(BASE + "/juegos")
    assert r2.status_code == 200, f"GET /juegos (comun) -> {r2.status_code}"
    assert 'href="/finanzas"' not in r2.text, "el perfil COMÚN no debería ver Finanzas"

    # 3) Jugar los 10, resolviendo cada problema.
    ws, cid, html = open_ws(sc)
    for ei in range(LIMIT):
        problema = extraer_problema(html)
        sol = resolver(problema)
        # Un dígito para que el server marque touched; la respuesta va en `v`.
        digito(ws, cid, 1)
        html = answer(ws, cid, ei, sol)
        time.sleep(0.05)
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)

    # 4) Verificación en Postgres.
    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid_com} AND mode='story' ORDER BY id DESC LIMIT 1")
    assert sid, "no se creó la sesión de Finanzas con mode='story'"
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}"))
    n_ok = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND correct"))
    n_prompt = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND length(prompt) > 0"))
    ended = psql(f"SELECT (ended_at IS NOT NULL) FROM sessions WHERE id={sid}")
    correct_col = psql(f"SELECT correct FROM sessions WHERE id={sid}")
    print(f"  comercial={pid_com} comun={pid_com2} sesion={sid} mode=story attempts={n_att} correctos={n_ok} prompts={n_prompt} sess.correct={correct_col} ended={ended}")
    assert n_att == LIMIT, f"esperaba {LIMIT} attempts, hubo {n_att}"
    assert n_ok == LIMIT, f"resolví todos pero solo {n_ok} quedaron correctos"
    assert n_prompt == LIMIT, "algún prompt quedó vacío"
    assert ended == "t", "la sesión no cerró su ciclo (ended_at nulo)"

    return {"comercial_ve": True, "comun_no_ve": True, "attempts": n_att, "correctos": n_ok, "ended": ended == "t"}


def run_server(cmd, label):
    print(f"[{label}] arrancando: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd="d:/MathHelp", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_up():
            raise RuntimeError(f"[{label}] el server no levantó")
        time.sleep(2.5)  # warmup del pool (fitz run)
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
    print("\nOK: Finanzas E2E verde." if results else "nada que correr")
