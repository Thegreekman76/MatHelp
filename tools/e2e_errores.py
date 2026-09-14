#!/usr/bin/env python3
# tools/e2e_errores.py — E2E de "Repasá tus errores".
#
# Siembra errores (attempts con correct=false) con caracteres NO-ASCII (× y ÷) —
# esto es clave: el bug del 2026-09-14 era que el round-trip del prompt "10 × 10"
# por el <form> no matcheaba (Fitz decodifica mal el campo UTF-8), y la pantalla se
# quedaba clavada. El fix busca por el ID del intento (entero), no por el prompt.
#
# Prueba: teclado propio presente (no input nativo) · resolución por aid con × y ÷ ·
# avanza · feedback correcto/incorrecto · vacío final.
#
# Requiere: requests + psql (o FITZ_PSQL). Server en :3000.  Uso: python tools/e2e_errores.py

import os, re, subprocess, sys, time, uuid
import requests

BASE = "http://127.0.0.1:3000"
PSQL = os.environ.get("FITZ_PSQL", r"C:\Program Files\PostgreSQL\15\bin\psql.exe")
PGUSER = os.environ.get("FITZ_PGUSER", "postgres")
PGPASS = os.environ.get("FITZ_PGPASS", "123mgp")
PGDB = os.environ.get("FITZ_PGDB", "mathelp")
ENV = {**os.environ, "PGPASSWORD": PGPASS}


def psql(sql):
    out = subprocess.run([PSQL, "-h", "localhost", "-U", PGUSER, "-d", PGDB, "-tAc", sql], capture_output=True, text=True, env=ENV, encoding="utf-8")
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


def aid_de(html):
    m = re.search(r'name="aid" value="(\d+)"', html)
    return m.group(1) if m else None


def escenario():
    s = requests.Session()
    tag = uuid.uuid4().hex[:10]
    s.post(BASE + "/registro", data={"familia": f"ERR {tag}", "email": f"err_{tag}@mathelp.test", "password": "clave-e2e-123"})
    s.post(BASE + "/perfiles/nuevo", data={"nombre": f"ERR-{tag}", "grado": "4", "pin": "", "modalidad": "comun"})
    pid = re.findall(r'name="pid"[^>]*value="(\d+)"', s.get(BASE + "/perfiles").text)[-1]
    s.post(BASE + "/perfiles/elegir", data={"pid": pid})

    # sin errores -> vacío (sin teclado)
    e0 = s.get(BASE + "/errores").text
    assert ("No mistakes" in e0) or ("errores para repasar" in e0), "sin errores no muestra la tarjeta vacía"
    assert 'class="ekp-pad"' not in e0, "la tarjeta vacía no debería tener teclado"
    assert psql("SELECT to_regclass('public.review_resolved') IS NOT NULL") == "t", "no se creó review_resolved (lazy)"

    # sembrar 2 errores con × y ÷ (no-ASCII: reproduce el bug del round-trip)
    psql(
        f"WITH ses AS (INSERT INTO sessions (profile_id, mode, seed) VALUES ({pid},'quiz',1) RETURNING id) "
        f"INSERT INTO attempts (session_id, profile_id, skill_code, prompt, expected, given, correct) "
        f"SELECT ses.id, {pid}, v.sk, v.p, v.e, '0', false FROM ses, "
        f"(VALUES ('mul.tabla','10 × 10','100'),('div.exacta','12 ÷ 3','4')) AS v(sk,p,e);"
    )

    # la vista trae el TECLADO PROPIO (no input nativo) + hidden aid + contador 2
    e1 = s.get(BASE + "/errores").text
    assert 'class="ekp-pad"' in e1 and 'data-ekp="7"' in e1, "no está el teclado propio"
    assert 'type="text"' not in e1, "quedó un input de texto nativo (dependería del teclado del dispositivo)"
    aid = aid_de(e1)
    assert aid, "no está el hidden aid"
    assert re.search(r"\b2\b", e1), "no muestra el contador 2"

    # responder BIEN por aid -> resuelve (el × ya NO rompe)
    exp = psql(f"SELECT expected FROM attempts WHERE id={aid}")
    fb = s.post(BASE + "/errores/responder", data={"aid": aid, "respuesta": exp}).text
    assert ("Well done" in fb) or ("Muy bien" in fb), "NO resolvió por aid (fix del × roto)"
    assert psql(f"SELECT COUNT(*) FROM review_resolved WHERE profile_id={pid}") == "1", "no marcó resuelto"

    # avanza al OTRO (aid distinto), contador baja a 1
    e2 = s.get(BASE + "/errores").text
    aid2 = aid_de(e2)
    assert aid2 and aid2 != aid, "no avanzó (mismo aid)"
    assert re.search(r"\b1\b", e2), "el contador no bajó a 1"

    # responder MAL -> muestra la respuesta correcta, también resuelve
    exp2 = psql(f"SELECT expected FROM attempts WHERE id={aid2}")
    fb2 = s.post(BASE + "/errores/responder", data={"aid": aid2, "respuesta": "99999"}).text
    assert ("Almost" in fb2) or ("Casi" in fb2), "no marcó incorrecto"
    assert exp2 in fb2, "no muestra la respuesta correcta"

    # vacío final + home linkea + mastery subió
    assert 'class="ekp-pad"' not in s.get(BASE + "/errores").text, "tras repasar todo debería quedar vacío"
    assert 'href="/errores"' in s.get(BASE + "/").text, "el home no linkea a /errores"
    assert int(psql(f"SELECT COALESCE(MAX(seen),0) FROM mastery WHERE profile_id={pid}")) >= 1, "el acierto en review no subió mastery"

    print("OK e2e_errores: teclado propio (sin input nativo); resolución por aid con × y ÷ (fix del round-trip);")
    print("               avanza; contador baja; feedback correcto/incorrecto; vacío final; mastery sube.")


def main():
    if not wait_up():
        print("FAIL: el server no responde en :3000")
        sys.exit(1)
    escenario()


if __name__ == "__main__":
    main()
