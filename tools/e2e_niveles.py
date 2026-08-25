#!/usr/bin/env python3
# tools/e2e_niveles.py — E2E de la progresión graduada (F8). Prueba, jugando de
# verdad, que:
#   (a) la dificultad ESCALA POR GRADO: un 3° secundaria (grade 10) sólo ve
#       Pitágoras (trig.pitagoras, niveles 1..3); un 6° (grade 13) llega a la razón
#       trigonométrica (trig.razon, niveles 4..5) y ya no ve el nivel 1 trivial.
#   (b) la dificultad SUBE DENTRO DE LA RONDA: el `difficulty` (= nivel) de los
#       últimos ejercicios es mayor que el de los primeros.
# Resuelve leyendo la figura SVG (mismo parser que e2e_trig).
#
# Uso:  python tools/e2e_niveles.py --only build   (o --only run, o ambos)

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
    s.post(BASE + "/registro", data={"familia": f"E2E {tag}", "email": f"e2e_{tag}@mathelp.test", "password": "clave-e2e-123"}, allow_redirects=True)
    nombre = f"NIV-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creó el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


def isqrt_exact(n):
    r = math.isqrt(n)
    assert r * r == n, f"{n} no es cuadrado perfecto"
    return r


def resolver_figura(html):
    lbls = re.findall(r'<text[^>]*class="tg-lbl"[^>]*>(.*?)</text>', html, re.S)
    assert len(lbls) == 3, f"figura sin 3 etiquetas: {lbls!r}"
    horiz, vert, hyp = [x.strip() for x in lbls]
    ang_m = re.search(r'<text[^>]*class="tg-ang"[^>]*>(\d+)', html)
    ang = int(ang_m.group(1)) if ang_m else 0

    def num(t):
        d = re.sub(r"[^\d]", "", t)
        return int(d) if d else None

    if ang == 30:
        if hyp == "?":
            return num(vert) * 2
        return num(hyp) // 2
    if hyp == "?":
        return isqrt_exact(num(horiz) ** 2 + num(vert) ** 2)
    return isqrt_exact(num(hyp) ** 2 - num(horiz) ** 2)


def jugar(s):
    cookies = "; ".join(f"{c.name}={c.value}" for c in s.cookies)
    ws = websocket.create_connection(BASE.replace("http", "ws") + "/live/trigonometria", header=[f"Cookie: {cookies}"], timeout=10)
    html = json.loads(ws.recv()).get("html", "")
    cid = re.search(r'data-flv-value-instance_id="([^"]+)"', html).group(1)
    for ei in range(LIMIT):
        sol = resolver_figura(html)
        ws.send(json.dumps({"event": "digito", "payload": {"d": "1", "component_name": "trig", "instance_id": cid}, "html": "", "patches": []}))
        ws.recv()
        ws.send(json.dumps({"event": "answer", "payload": {"v": str(sol), "ei": str(ei), "touched": "1", "component_name": "trig", "instance_id": cid}, "html": "", "patches": []}))
        html = json.loads(ws.recv()).get("html", "")
        time.sleep(0.05)
    time.sleep(0.4)
    ws.close()
    time.sleep(0.4)


def skills_y_rampa(pid):
    sid = psql(f"SELECT id FROM sessions WHERE profile_id={pid} AND topic_code='trig' ORDER BY id DESC LIMIT 1")
    assert sid, "no hay sesión de trig"
    skills = set(psql(f"SELECT DISTINCT skill_code FROM attempts WHERE session_id={sid}").split("\n"))
    dif_ini = int(psql(f"SELECT difficulty FROM attempts WHERE session_id={sid} ORDER BY idx ASC LIMIT 1"))
    dif_fin = int(psql(f"SELECT difficulty FROM attempts WHERE session_id={sid} ORDER BY idx DESC LIMIT 1"))
    return skills, dif_ini, dif_fin


def escenario():
    # Grade 10 (3° sec): sólo Pitágoras.
    s10 = requests.Session()
    p10 = setup_perfil(s10, 10)
    jugar(s10)
    sk10, ini10, fin10 = skills_y_rampa(p10)

    # Grade 13 (6° sec): llega a la razón trigonométrica.
    s13 = requests.Session()
    p13 = setup_perfil(s13, 13)
    jugar(s13)
    sk13, ini13, fin13 = skills_y_rampa(p13)

    print(f"  grade10: skills={sorted(sk10)} dif {ini10}->{fin10}")
    print(f"  grade13: skills={sorted(sk13)} dif {ini13}->{fin13}")

    # (a) escala por grado: grade 10 sólo pitagoras; grade 13 incluye razon.
    assert sk10 == {"trig.pitagoras"}, f"grade 10 debería ver sólo Pitágoras, vio {sk10}"
    assert "trig.razon" in sk13, f"grade 13 debería ver la razón trigonométrica, vio {sk13}"
    # (b) rampa dentro de la ronda: la dificultad sube.
    assert fin10 > ini10, f"grade 10 no rampeó ({ini10}→{fin10})"
    assert fin13 > ini13, f"grade 13 no rampeó ({ini13}→{fin13})"
    # el 6° arranca más arriba que el 3° (piso más alto).
    assert ini13 >= ini10, f"grade 13 debería arrancar >= grade 10 ({ini13} vs {ini10})"

    return {"escala_por_grado": True, "rampa_en_ronda": True, "g10_skills": sorted(sk10), "g13_skills": sorted(sk13), "g10_dif": [ini10, fin10], "g13_dif": [ini13, fin13]}


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
    print("\nOK: niveles E2E verde." if results else "nada que correr")
