#!/usr/bin/env python3
# tools/e2e_aventura.py — E2E del "Modo aventura / mapa".
#
# El mapa es una vista sobre attempts: cada mundo pide N correctas de una destreza
# y desbloquea el siguiente. Se siembran correctas via psql y se cuentan los nodos
# por estado (done/current/lock). También verifica el filtrado por grado.
#
# Requiere: requests + psql (o FITZ_PSQL). Server en :3000.  Uso: python tools/e2e_aventura.py

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


def perfil(grado):
    s = requests.Session()
    tag = uuid.uuid4().hex[:10]
    s.post(BASE + "/registro", data={"familia": f"ADV {tag}", "email": f"adv_{tag}@mathelp.test", "password": "clave-e2e-123"})
    s.post(BASE + "/perfiles/nuevo", data={"nombre": f"ADV-{tag}", "grado": str(grado), "pin": "", "modalidad": "comun"})
    pid = re.findall(r'name="pid"[^>]*value="(\d+)"', s.get(BASE + "/perfiles").text)[-1]
    s.post(BASE + "/perfiles/elegir", data={"pid": pid})
    return s, pid


def seed(pid, skill, n):
    psql(
        f"WITH ses AS (INSERT INTO sessions (profile_id, mode, seed) VALUES ({pid},'quiz',1) RETURNING id) "
        f"INSERT INTO attempts (session_id, profile_id, skill_code, prompt, expected, given, correct) "
        f"SELECT ses.id, {pid}, '{skill}', 'x', '1', '1', true FROM ses, generate_series(1,{n});"
    )


def counts(h):
    return (h.count("mh-adv-nodo done"), h.count("mh-adv-nodo current"), h.count("mh-adv-nodo lock"))


def escenario():
    # grado 6 -> 10 mundos, perfil nuevo 0/1/9
    s, pid = perfil(6)
    a0 = s.get(BASE + "/aventura").text
    assert "/ 10 " in a0, "grado 6 debería ver 10 mundos"
    assert counts(a0) == (0, 1, 9), f"nuevo esperaba (0,1,9), dio {counts(a0)}"
    assert re.search(r'mh-adv-prog">0/5<', a0), "el nodo actual no muestra 0/5"

    # completar add (5) -> 1/1/8
    seed(pid, "add", 5)
    assert counts(s.get(BASE + "/aventura").text) == (1, 1, 8), "tras add=5 esperaba (1,1,8)"

    # completar sub + patron -> 3/1/6
    seed(pid, "sub", 5)
    seed(pid, "patron", 5)
    assert counts(s.get(BASE + "/aventura").text) == (3, 1, 6), "tras 3 mundos esperaba (3,1,6)"

    # completar reloj -> mul.tabla (req 8) pasa a actual con 0/8
    seed(pid, "reloj", 5)
    a3 = s.get(BASE + "/aventura").text
    assert counts(a3) == (4, 1, 5), "tras reloj esperaba (4,1,5)"
    assert re.search(r'mh-adv-prog">0/8<', a3), "mul.tabla debería pedir 0/8"

    # grado 2 -> solo 5 mundos
    s2, _ = perfil(2)
    b0 = s2.get(BASE + "/aventura").text
    assert "/ 5 " in b0 and counts(b0) == (0, 1, 4), "grado 2 debería ver 5 mundos (0,1,4)"

    assert 'href="/aventura"' in s.get(BASE + "/").text, "el home no linkea a /aventura"
    print("OK e2e_aventura: grado 6 = 10 mundos (0/1/9 -> add ->1/1/8 -> 3 mundos ->3/1/6 -> reloj ->4/1/5,")
    print("                mul.tabla 0/8); grado 2 = 5 mundos; home linkea.")


def main():
    if not wait_up():
        print("FAIL: el server no responde en :3000")
        sys.exit(1)
    escenario()


if __name__ == "__main__":
    main()
