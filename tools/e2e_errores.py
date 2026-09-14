#!/usr/bin/env python3
# tools/e2e_errores.py — E2E de "Repasá tus errores".
#
# Siembra errores (attempts con correct=false) vía psql y prueba el flujo completo:
#   1. Sin errores -> tarjeta "no tenés errores" (sin formulario).
#   2. La tabla review_resolved se crea LAZY al entrar (anda en bases existentes).
#   3. Con 3 errores sembrados -> /errores muestra una pregunta + contador "3".
#   4. Responder BIEN -> feedback correcto, marca resuelto (review_resolved) y sube
#      el rating (mastery); el prompt sale de la cola (baja a 2).
#   5. Responder MAL -> feedback con la respuesta correcta; también sale de la cola.
#   6. Repasar todo -> vuelve a la tarjeta vacía.
#   7. El home linkea a /errores.
#
# Requiere: requests + psql en PATH (o FITZ_PSQL). Server andando en :3000.
# Uso:  python tools/e2e_errores.py

import os, re, subprocess, sys, time, uuid
import requests

BASE = "http://127.0.0.1:3000"
PSQL = os.environ.get("FITZ_PSQL", r"C:\Program Files\PostgreSQL\15\bin\psql.exe")
PGUSER = os.environ.get("FITZ_PGUSER", "postgres")
PGPASS = os.environ.get("FITZ_PGPASS", "123mgp")
PGDB = os.environ.get("FITZ_PGDB", "mathelp")
ENV = {**os.environ, "PGPASSWORD": PGPASS}
EXP = {"7 * 8": "56", "9 + 6": "15", "12 - 5": "7"}


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


def prompt_actual(html):
    m = re.search(r'name="prompt" value="([^"]+)"', html)
    return m.group(1) if m else None


def escenario():
    s = requests.Session()
    tag = uuid.uuid4().hex[:10]
    s.post(BASE + "/registro", data={"familia": f"ERR {tag}", "email": f"err_{tag}@mathelp.test", "password": "clave-e2e-123"})
    s.post(BASE + "/perfiles/nuevo", data={"nombre": f"ERR-{tag}", "grado": "4", "pin": "", "modalidad": "comun"})
    pid = re.findall(r'name="pid"[^>]*value="(\d+)"', s.get(BASE + "/perfiles").text)[-1]
    s.post(BASE + "/perfiles/elegir", data={"pid": pid})

    # 1. sin errores -> vacío, sin formulario
    e0 = s.get(BASE + "/errores").text
    assert ("No mistakes" in e0) or ("errores para repasar" in e0), "sin errores no muestra la tarjeta vacía"
    assert 'name="respuesta"' not in e0, "la tarjeta vacía no debería tener formulario"
    # 2. la tabla se creó lazy
    assert psql("SELECT to_regclass('public.review_resolved') IS NOT NULL") == "t", "no se creó review_resolved (lazy)"

    # sembrar 3 errores (una sesión + 3 attempts correct=false)
    psql(
        f"WITH ses AS (INSERT INTO sessions (profile_id, mode, seed) VALUES ({pid},'quiz',1) RETURNING id) "
        f"INSERT INTO attempts (session_id, profile_id, skill_code, prompt, expected, given, correct) "
        f"SELECT ses.id, {pid}, v.sk, v.p, v.e, v.g, false FROM ses, "
        f"(VALUES ('mul.tabla','7 * 8','56','54'),('add','9 + 6','15','16'),('sub','12 - 5','7','8')) AS v(sk,p,e,g);"
    )

    # 3. pregunta + contador 3
    e1 = s.get(BASE + "/errores").text
    assert 'name="respuesta"' in e1 and re.search(r"\b3\b", e1), "no muestra pregunta + contador 3"
    p1 = prompt_actual(e1)
    assert p1 in EXP, f"prompt inesperado: {p1!r}"

    # 4. responder BIEN -> correcto + resuelto + mastery, baja a 2
    fb = s.post(BASE + "/errores/responder", data={"prompt": p1, "respuesta": EXP[p1]}).text
    assert ("Well done" in fb) or ("Muy bien" in fb), "no marcó correcto"
    assert EXP[p1] in fb, "no muestra la cuenta resuelta"
    assert psql(f"SELECT COUNT(*) FROM review_resolved WHERE profile_id={pid}") == "1", "no marcó resuelto"
    e2 = s.get(BASE + "/errores").text
    assert re.search(r"\b2\b", e2), "no bajó a 2"
    assert prompt_actual(e2) != p1, "el resuelto reapareció"

    # 5. responder MAL -> muestra la respuesta correcta, también sale de la cola
    p2 = prompt_actual(e2)
    fb2 = s.post(BASE + "/errores/responder", data={"prompt": p2, "respuesta": "99999"}).text
    assert ("Almost" in fb2) or ("Casi" in fb2), "no marcó incorrecto"
    assert EXP[p2] in fb2, "no muestra la respuesta correcta en el error"

    # 6. repasar el último -> vacío
    e3 = s.get(BASE + "/errores").text
    p3 = prompt_actual(e3)
    s.post(BASE + "/errores/responder", data={"prompt": p3, "respuesta": EXP[p3]})
    assert 'name="respuesta"' not in s.get(BASE + "/errores").text, "tras repasar todo debería quedar vacío"

    # 7. home linkea + mastery subió por el acierto en review
    assert 'href="/errores"' in s.get(BASE + "/").text, "el home no linkea a /errores"
    assert int(psql(f"SELECT COALESCE(MAX(seen),0) FROM mastery WHERE profile_id={pid}")) >= 1, "el acierto en review no subió mastery"

    print("OK e2e_errores: vacío -> 3 sembrados (pregunta + contador) -> BIEN (resuelve + mastery) -> 2")
    print("               -> MAL (muestra la respuesta) -> vacío. Lazy CREATE TABLE en base existente OK.")


def main():
    if not wait_up():
        print("FAIL: el server no responde en :3000")
        sys.exit(1)
    escenario()


if __name__ == "__main__":
    main()
