#!/usr/bin/env python3
# tools/e2e_memoria.py — E2E del juego "Memoria" (unir los pares, F9).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil -> GET /juegos muestra "Memoria" (href="/memoria").
#   2. GET /memoria -> el SSR trae la grilla de cartas.
#   3. Abre WS /live/memoria; parsea las cartas (pos + texto), EVALÚA cada
#      expresión, agrupa por valor (cada par: expresión ↔ su resultado) y toca las
#      dos cartas de cada par.
#   4. Verifica: data-fb-seq (sonido), q-racha, q-progress, estrellas, ronda perfecta
#      + confetti + récord; y en Postgres: sesión mode='memoria' topic 'memoria', K
#      attempts TODOS correctos, best_streak=K en profile_game_stats.
#
# Que unir por VALOR resuelva todos los pares valida que las expresiones del
# generador evalúan a su resultado (pares correctos) end-to-end.
#
# Requiere: requests, websocket-client, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_memoria.py --only build   (o --only run, o ambos)

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
    nombre = f"MEM-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creó el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


# --- parsear + evaluar las cartas -------------------------------------------

def evaluar(text):
    text = text.strip()
    if "×" in text:
        a, b = text.split("×")
        return int(a) * int(b)
    if "÷" in text:
        a, b = text.split("÷")
        return int(a) // int(b)
    if "−" in text:  # signo menos U+2212
        a, b = text.split("−")
        return int(a) - int(b)
    if "+" in text:
        a, b = text.split("+")
        return int(a) + int(b)
    return int(text)  # resultado pelado


def parse_cartas(html):
    cards = re.findall(r'data-flv-value-pos="(\d+)">([^<]+)</button>', html)
    return [(int(pos), txt.strip()) for pos, txt in cards]


# --- socket ------------------------------------------------------------------

def open_ws(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(BASE.replace("http", "ws") + "/live/memoria", header=[f"Cookie: {cookies}"], timeout=10)
    html = json.loads(ws.recv()).get("html", "")
    cid = re.search(r'data-flv-value-instance_id="([^"]+)"', html).group(1)
    return ws, cid, html


def pick(ws, cid, pos):
    ws.send(json.dumps({"event": "pick", "payload": {"pos": str(pos), "component_name": "memoria", "instance_id": cid}, "html": "", "patches": []}))
    return json.loads(ws.recv()).get("html", "")


def jugar_ronda(grado):
    s = requests.Session()
    pid = setup_perfil(s, grado)
    rp = s.get(BASE + "/memoria")
    assert rp.status_code == 200, f"GET /memoria -> {rp.status_code}"
    assert 'mem-grid' in rp.text, "el SSR no trae la grilla"

    ws, cid, html = open_ws(s)
    cartas = parse_cartas(html)
    assert len(cartas) >= 8, f"grade {grado}: esperaba >= 8 cartas, hubo {len(cartas)}"

    # Agrupar por valor: cada valor tiene 2 posiciones (expresión + resultado).
    por_valor = {}
    for pos, txt in cartas:
        por_valor.setdefault(evaluar(txt), []).append(pos)
    k = len(por_valor)
    for v, poss in por_valor.items():
        assert len(poss) == 2, f"grade {grado}: el valor {v} no tiene exactamente 2 cartas ({poss})"

    fb_con_seq = False
    vio_racha = False
    for v, poss in por_valor.items():
        pick(ws, cid, poss[0])
        html = pick(ws, cid, poss[1])
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

    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND mode='memoria' AND topic_code='memoria' ORDER BY id DESC LIMIT 1")
    assert sid, "no se creó la sesión de Memoria (memoria/memoria)"
    n_att = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid}"))
    n_ok = int(psql(f"SELECT count(*) FROM attempts WHERE session_id={sid} AND correct"))
    rec = psql(f"SELECT best_streak FROM profile_game_stats WHERE profile_id={pid} AND game_code='memoria'")
    assert rec == str(k), f"grade {grado}: récord debería ser {k}, fue '{rec}'"
    print(f"  grade {grado}: perfil={pid} pares={k} attempts={n_att} correctos={n_ok} record={rec}")
    assert n_att == k, f"grade {grado}: esperaba {k} attempts, hubo {n_att}"
    assert n_ok == k, f"grade {grado}: uní todos pero solo {n_ok} quedaron correctos"
    return k


def escenario():
    s0 = requests.Session()
    setup_perfil(s0, 3)
    r = s0.get(BASE + "/juegos")
    assert r.status_code == 200, f"GET /juegos -> {r.status_code}"
    assert 'href="/memoria"' in r.text, "no aparece la carta Memoria"
    # Grado 2 (sumas, 4 pares) y grado 13 (mixto, 6 pares).
    g2 = jugar_ronda(2)
    g13 = jugar_ronda(13)
    return {"aparece": True, "g2_pares": g2, "g13_pares": g13}


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
    print("\nOK: Memoria E2E verde." if results else "nada que correr")
