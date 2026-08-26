#!/usr/bin/env python3
# tools/e2e_avatar.py — E2E del selector de avatar por perfil (F9 pulido).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil nuevo -> GET / (home) trae el saludo con el avatar por defecto (🧉)
#      y el link a /avatar.
#   2. GET /avatar -> muestra 12 avatares; el default (mate) marcado (.sel).
#   3. GET /avatar/cohete -> 303 a /avatar; en Postgres profiles.avatar='cohete'.
#   4. GET / -> el saludo ahora muestra 🚀.
#   5. GET /perfiles -> la tarjeta del perfil muestra 🚀.
#   6. GET /avatar/basura (invalido) -> 303 a /avatar, no cambia nada.
#
# Requiere: requests, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_avatar.py --only build   (o --only run, o ambos)

import argparse, os, re, subprocess, time, uuid
import requests

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
    nombre = f"AVA-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creo el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid), nombre


def escenario():
    s = requests.Session()
    pid, nombre = setup_perfil(s, 5)

    # 1. home trae saludo con el avatar default (mate) + link /avatar
    home = s.get(BASE + "/").text
    assert 'href="/avatar"' in home, "el home no linkea a /avatar"
    assert "mh-saludo" in home and "🧉" in home, "el saludo no muestra el avatar por defecto"
    # regresion: los sub-bloques Html deben ir con .raw (no filtrar 'Html { raw: ')
    assert "Html { raw:" not in home, "se filtra el Display de Html en el home (falta .raw)"

    # 2. /avatar muestra 12 avatares, mate marcado
    a0 = s.get(BASE + "/avatar").text
    n = a0.count('<a class="mh-avpick')
    assert n == 12, f"esperaba 12 avatares, hay {n}"
    assert 'mh-avpick sel" href="/avatar/mate"' in a0, "el default no esta marcado"

    # 3. elegir cohete -> 303 + persiste en DB
    r = s.get(BASE + "/avatar/cohete", allow_redirects=False)
    assert r.status_code == 303 and r.headers.get("Location") == "/avatar", f"redirect malo: {r.status_code}"
    av_db = psql(f"SELECT avatar FROM profiles WHERE id = {pid}")
    assert av_db == "cohete", f"DB avatar = {av_db!r}, esperaba 'cohete'"

    # 4. home ahora muestra 🚀
    home2 = s.get(BASE + "/").text
    assert "🚀" in home2, "el saludo no actualizo el avatar"

    # 5. /perfiles muestra 🚀 en la tarjeta
    perf = s.get(BASE + "/perfiles").text
    assert "🚀" in perf, "la tarjeta de perfil no muestra el nuevo avatar"

    # 6. avatar invalido -> 303, no cambia
    r2 = s.get(BASE + "/avatar/basura", allow_redirects=False)
    assert r2.status_code == 303 and r2.headers.get("Location") == "/avatar", "invalido no redirige"
    av_db2 = psql(f"SELECT avatar FROM profiles WHERE id = {pid}")
    assert av_db2 == "cohete", f"invalido cambio el avatar: {av_db2!r}"

    # bonus: la galeria de logros muestra medallas bloqueadas (recien creado)
    prog = s.get(BASE + "/progreso").text
    assert "mh-medalla" in prog, "no aparece la galeria de logros"

    return {"home_saludo": True, "avatares": n, "aplica": "cohete", "persiste": True, "en_perfiles": True, "invalido_ignora": True, "galeria": True}


def run_server(cmd, label):
    print(f"[{label}] arrancando: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd="d:/MathHelp", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_up():
            raise RuntimeError(f"[{label}] el server no levanto")
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
    print("\nOK: Avatar E2E verde." if results else "nada que correr")
