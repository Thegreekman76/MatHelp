#!/usr/bin/env python3
# tools/e2e_tema.py — E2E del selector de tema de color por perfil (F9 pulido).
#
# Escenario (contra `fitz run` o el binario):
#   1. Perfil nuevo -> GET / (home) trae el enlace a /tema + el <script> del tema
#      en el <head> (data-theme desde la cookie mathelp_theme).
#   2. GET /tema -> muestra 5 swatches; "Menta" (default) marcado (.sel).
#   3. GET /tema/oceano -> 303 a /tema + setea cookie mathelp_theme=oceano.
#   4. En Postgres: profiles.theme = 'oceano' para el perfil.
#   5. GET /tema de nuevo -> ahora "Océano" está marcado (.sel).
#   6. GET /tema/basura (código inválido) -> 303 a /tema, no cambia nada.
#
# Requiere: requests, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_tema.py --only build   (o --only run, o ambos)

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
    nombre = f"TEMA-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creó el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


def marcado(html):
    # devuelve el color del swatch marcado con .sel (por el nombre visible)
    m = re.search(r'class="mh-swatch sel"[^>]*>\s*<span[^>]*>[^<]*</span>\s*<span class="mh-swatch-name">([^<]+)</span>', html)
    return m.group(1) if m else None


def escenario():
    s = requests.Session()
    pid = setup_perfil(s, 6)

    # 1. home trae el enlace a /tema + el script del tema en el <head>
    home = s.get(BASE + "/").text
    assert 'href="/tema"' in home, "el home no linkea a /tema"
    assert "data-theme" in home and "mathelp_theme" in home, "falta el <script> del tema en el head"

    # 2. /tema muestra 5 swatches, Menta (default) marcado
    t0 = s.get(BASE + "/tema").text
    n_swatches = t0.count('<a class="mh-swatch')  # solo los anchors (sel + no-sel)
    assert n_swatches == 5, f"esperaba 5 swatches, hay {n_swatches}"
    assert marcado(t0) in ("Menta", "Mint"), f"default no marcado: {marcado(t0)!r}"

    # 3. aplicar oceano -> 303 a /tema + cookie
    r = s.get(BASE + "/tema/oceano", allow_redirects=False)
    assert r.status_code == 303 and r.headers.get("Location") == "/tema", f"redirect malo: {r.status_code} {r.headers.get('Location')}"
    assert s.cookies.get("mathelp_theme") == "oceano", f"cookie no seteada: {s.cookies.get('mathelp_theme')}"

    # 4. persistido en DB
    theme_db = psql(f"SELECT theme FROM profiles WHERE id = {pid}")
    assert theme_db == "oceano", f"DB theme = {theme_db!r}, esperaba 'oceano'"

    # 5. /tema ahora marca Oceano
    t1 = s.get(BASE + "/tema").text
    assert marcado(t1) in ("Oceano", "Océano", "Ocean"), f"oceano no marcado: {marcado(t1)!r}"

    # 6. codigo invalido -> 303 a /tema, no cambia nada
    r2 = s.get(BASE + "/tema/basura", allow_redirects=False)
    assert r2.status_code == 303 and r2.headers.get("Location") == "/tema", "codigo invalido no redirige bien"
    theme_db2 = psql(f"SELECT theme FROM profiles WHERE id = {pid}")
    assert theme_db2 == "oceano", f"codigo invalido cambio el theme: {theme_db2!r}"

    return {"home_link": True, "swatches": n_swatches, "aplica": "oceano", "persiste": True, "invalido_ignora": True}


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
    print("\nOK: Tema E2E verde." if results else "nada que correr")
