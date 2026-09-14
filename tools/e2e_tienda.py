#!/usr/bin/env python3
# tools/e2e_tienda.py — E2E de "Monedas + tienda".
#
# Las monedas son una vista (respuestas correctas − gastado). Se siembran 100
# respuestas correctas via psql y se prueba: comprar, equipar, el gateo de posesión
# (no se puede equipar lo no comprado) y el saldo insuficiente.
#
# Requiere: requests + psql en PATH (o FITZ_PSQL). Server andando en :3000.
# Uso:  python tools/e2e_tienda.py

import os, re, subprocess, sys, time, uuid
import requests

BASE = "http://127.0.0.1:3000"
PSQL = os.environ.get("FITZ_PSQL", r"C:\Program Files\PostgreSQL\15\bin\psql.exe")
PGUSER = os.environ.get("FITZ_PGUSER", "postgres")
PGPASS = os.environ.get("FITZ_PGPASS", "123mgp")
PGDB = os.environ.get("FITZ_PGDB", "mathelp")
ENV = {**os.environ, "PGPASSWORD": PGPASS}


def psql(sql):
    out = subprocess.run([PSQL, "-h", "localhost", "-U", PGUSER, "-d", PGDB, "-tAc", sql], capture_output=True, text=True, env=ENV)
    if out.returncode != 0:
        raise RuntimeError("psql falló: " + out.stderr)
    return out.stdout.strip().split("\n")[0].strip()


def wait_up(timeout=40):
    for _ in range(timeout * 2):
        try:
            requests.get(BASE + "/", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def escenario():
    s = requests.Session()
    tag = uuid.uuid4().hex[:10]
    s.post(BASE + "/registro", data={"familia": f"SHOP {tag}", "email": f"shop_{tag}@mathelp.test", "password": "clave-e2e-123"})
    s.post(BASE + "/perfiles/nuevo", data={"nombre": f"SHOP-{tag}", "grado": "4", "pin": "", "modalidad": "comun"})
    pid = re.findall(r'name="pid"[^>]*value="(\d+)"', s.get(BASE + "/perfiles").text)[-1]
    s.post(BASE + "/perfiles/elegir", data={"pid": pid})

    # 100 respuestas correctas -> 100 monedas
    psql(
        f"WITH ses AS (INSERT INTO sessions (profile_id, mode, seed) VALUES ({pid},'quiz',1) RETURNING id) "
        f"INSERT INTO attempts (session_id, profile_id, skill_code, prompt, expected, given, correct) "
        f"SELECT ses.id, {pid}, 'add', '1 + 1', '2', '2', true FROM ses, generate_series(1,100);"
    )

    # saldo 100 + tabla lazy
    t0 = s.get(BASE + "/tienda").text
    assert re.search(r"\b100\b", t0), "no muestra saldo 100"
    assert psql("SELECT to_regclass('public.purchases') IS NOT NULL") == "t", "no creó purchases (lazy)"
    assert 'href="/avatar/mate"' in t0, "el avatar gratis no está usable"
    assert 'href="/tienda/comprar/avatar/cohete"' in t0, "cohete no está comprable"

    # comprar cohete (25) -> saldo 75, usable
    s.get(BASE + "/tienda/comprar/avatar/cohete")
    assert psql(f"SELECT COUNT(*) FROM purchases WHERE profile_id={pid} AND item_code='cohete'") == "1", "no registró la compra"
    t1 = s.get(BASE + "/tienda").text
    assert re.search(r"\b75\b", t1) and 'href="/avatar/cohete"' in t1, "saldo/estado tras comprar mal"

    # equipar el comprado
    s.get(BASE + "/avatar/cohete")
    assert psql(f"SELECT avatar FROM profiles WHERE id={pid}") == "cohete", "no equipó el avatar comprado"

    # equipar uno NO poseído -> redirige a /tienda y NO cambia
    r = s.get(BASE + "/avatar/estrella", allow_redirects=False)
    assert "/tienda" in r.headers.get("Location", ""), "equipar no-poseído no redirige a la tienda"
    assert psql(f"SELECT avatar FROM profiles WHERE id={pid}") == "cohete", "equipó un avatar no poseído (gateo roto)"

    # comprar + equipar un tema
    s.get(BASE + "/tienda/comprar/theme/oceano")
    assert psql(f"SELECT COUNT(*) FROM purchases WHERE profile_id={pid} AND item_type='theme' AND item_code='oceano'") == "1", "no compró el tema"
    s.get(BASE + "/tema/oceano")
    assert psql(f"SELECT theme FROM profiles WHERE id={pid}") == "oceano", "no equipó el tema comprado"

    # sin saldo (35) no se compra pulpo (50)
    s.get(BASE + "/tienda/comprar/avatar/pulpo")
    assert psql(f"SELECT COUNT(*) FROM purchases WHERE profile_id={pid} AND item_code='pulpo'") == "0", "compró sin saldo (bug)"

    # bloqueados en /avatar linkean a la tienda; home linkea
    assert 'class="mh-avpick lock" href="/tienda"' in s.get(BASE + "/avatar").text, "bloqueados no linkean a la tienda"
    assert 'href="/tienda"' in s.get(BASE + "/").text, "el home no linkea a la tienda"

    print("OK e2e_tienda: saldo 100 -> compra cohete(25)->75 + equipa; no-poseído redirige y NO equipa;")
    print("              tema comprado+equipado; sin saldo NO compra; bloqueados->tienda; home linkea.")


def main():
    if not wait_up():
        print("FAIL: el server no responde en :3000")
        sys.exit(1)
    escenario()


if __name__ == "__main__":
    main()
