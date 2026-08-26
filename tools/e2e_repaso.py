#!/usr/bin/env python3
# tools/e2e_repaso.py — E2E del CTA "Repasá lo que te cuesta" + "Mis récords".
#
# Valida el RENDER (la persistencia de juego ya la cubren los E2E por juego):
# sembramos mastery (una destreza floja) + profile_game_stats (un récord) via
# psql, y verificamos:
#   1. GET / -> el home muestra el CTA de repaso (.mh-repaso) linkeando al juego
#      que entrena la destreza mas floja (mul.tabla -> /escalera).
#   2. GET /progreso -> aparece "Mis récords" (.mh-records) con la mejor racha.
#   3. Sin datos (perfil nuevo) -> el home NO muestra el CTA de repaso.
#
# Requiere: requests, psql en PATH (o FITZ_PSQL).
# Uso:  python tools/e2e_repaso.py --only build   (o --only run, o ambos)

import argparse, os, subprocess, time, uuid
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
    nombre = f"REP-{tag}"
    s.post(BASE + "/perfiles/nuevo", data={"nombre": nombre, "grado": str(grado), "pin": ""}, allow_redirects=True)
    pid = psql(f"SELECT id FROM profiles WHERE name = '{nombre}' ORDER BY id DESC LIMIT 1")
    assert pid, "no se creo el perfil"
    s.post(BASE + "/perfiles/elegir", data={"pid": pid}, allow_redirects=True)
    return int(pid)


def escenario():
    s = requests.Session()
    pid = setup_perfil(s, 6)

    # 3 (antes de sembrar): perfil nuevo -> sin CTA de repaso
    home0 = s.get(BASE + "/").text
    assert 'mh-btn sec mh-repaso"' not in home0, "el perfil nuevo no deberia mostrar el CTA de repaso"

    # sembrar: destreza floja (mul.tabla, rating bajo, >=3 vistas) + un record
    psql(f"INSERT INTO mastery (profile_id, skill_code, rating, seen, hits, streak, avg_ms) VALUES ({pid}, 'mul.tabla', 620, 6, 2, 0, 3200)")
    psql(f"INSERT INTO mastery (profile_id, skill_code, rating, seen, hits, streak, avg_ms) VALUES ({pid}, 'add', 950, 8, 7, 3, 2100)")
    psql(f"INSERT INTO profile_game_stats (profile_id, game_code, best_streak, updated_at) VALUES ({pid}, 'escalera', 7, NOW())")
    psql(f"INSERT INTO profile_game_stats (profile_id, game_code, best_streak, updated_at) VALUES ({pid}, 'series', 4, NOW())")

    # 1. home muestra el CTA de repaso hacia el juego de la destreza mas floja
    home = s.get(BASE + "/").text
    assert 'mh-btn sec mh-repaso"' in home, "no aparece el CTA de repaso"
    assert 'class="mh-btn sec mh-repaso" href="/escalera"' in home, "el CTA no linkea a /escalera (mul.tabla mas floja)"

    # 2. /progreso muestra "Mis records" con la mejor racha
    prog = s.get(BASE + "/progreso").text
    assert 'class="mh-records"' in prog, "no aparece la seccion de records"
    assert 'class="mh-record-row"' in prog, "no hay filas de record"

    return {"nuevo_sin_repaso": True, "cta_repaso": True, "ruta": "/escalera", "records": True}


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
    print("\nOK: Repaso + records E2E verde." if results else "nada que correr")
