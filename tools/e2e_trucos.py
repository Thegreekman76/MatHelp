#!/usr/bin/env python3
# tools/e2e_trucos.py — E2E de la sección de aprendizaje "Trucos" (§11.e).
#
# La sección es contenido ESTÁTICO (sin generador ni persistencia), así que el
# E2E no verifica paridad run↔binario ni psql: verifica el RENDER y el filtrado.
#
# Escenario (contra el server en :3000, `fitz run` o el binario/docker):
#   1. Home linkea a /trucos (💡 Trucos).
#   2. Un perfil de grado alto (13) ve las 21 fichas; cada una linkea a /trucos/{code}.
#   3. Cada ficha (/trucos/{code}) trae: SVG (.tk-svg) + 3 pasos (<li>×3) + ejemplo
#      (.mh-truco-ej) + botón "Probalo" que apunta al juego correcto (truco_route).
#   4. Filtrado por grado: el menú muestra sólo las fichas con min_grade <= grado
#      (un chico de primaria NO ve las de secundaria).
#   5. El decimal respeta el locale (½ = 0,5 en es-AR, 0.5 en en) — regla 2.
#   6. Ningún leak de `Html { raw: ... }`.
#
# Requiere: requests, y el server andando en BASE. Sin psql (saca el pid de /perfiles).
# Uso:  python tools/e2e_trucos.py

import re, sys, time, uuid
import requests

BASE = "http://127.0.0.1:3000"

# code -> (min_grade, ruta esperada del botón "Probalo")
TRUCOS = {
    "amigos10": (1, "/jugar"), "x9manos": (2, "/escalera"), "x5mitad": (2, "/escalera"),
    "x11": (3, "/escalera"), "x4doble": (3, "/escalera"), "divis": (3, "/jugar"),
    "redondear": (3, "/estimar"), "divis39": (4, "/jugar"), "equiv": (4, "/fracciones"),
    "jerarquia": (5, "/jugar"), "simplificar": (5, "/fracciones"), "pctmental": (6, "/porcentaje"),
    "regla3": (6, "/porcentaje"), "pruebanueve": (6, "/jugar"), "signos": (7, "/enteros"),
    "despejar": (8, "/ecuaciones"), "potencias": (8, "/potencias"), "cuad5": (8, "/potencias"),
    "binomio": (9, "/ecuaciones"), "sohcahtoa": (11, "/trigonometria"), "terna345": (11, "/trigonometria"),
}


def wait_up(timeout=40):
    for _ in range(timeout * 2):
        try:
            requests.get(BASE + "/", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def setup_perfil(grado):
    s = requests.Session()
    tag = uuid.uuid4().hex[:10]
    s.post(BASE + "/registro", data={"familia": f"E2E {tag}", "email": f"e2e_{tag}@mathelp.test", "password": "clave-e2e-123"}, allow_redirects=True)
    s.post(BASE + "/perfiles/nuevo", data={"nombre": f"TRUCO-{tag}", "grado": str(grado), "pin": "", "modalidad": "comun"}, allow_redirects=True)
    pids = re.findall(r'name="pid"[^>]*value="(\d+)"', s.get(BASE + "/perfiles").text)
    assert pids, f"no se creó/encontró el perfil (grado {grado})"
    s.post(BASE + "/perfiles/elegir", data={"pid": pids[-1]}, allow_redirects=True)
    return s


def cards(html):
    return set(re.findall(r'href="/trucos/(\w+)"', html))


def visibles_a(grado):
    return {c for c, (mg, _) in TRUCOS.items() if mg <= grado}


def escenario():
    s13 = setup_perfil(13)

    # 1. home linkea a /trucos
    home = s13.get(BASE + "/").text
    assert 'href="/trucos"' in home, "el home no linkea a /trucos"
    assert "Html { raw:" not in home, "LEAK de Html en el home"

    # 2. grado 13 ve las 21
    land = s13.get(BASE + "/trucos").text
    got = cards(land)
    assert got == set(TRUCOS), f"grado 13 debería ver las 21: falta {set(TRUCOS) - got}, sobra {got - set(TRUCOS)}"
    assert len(got) == 21, f"esperaba 21 fichas, hay {len(got)}"
    assert "Html { raw:" not in land, "LEAK de Html en /trucos"

    # 3. cada ficha: SVG + 3 pasos + ejemplo + ruta Probalo correcta
    for c, (_, route) in TRUCOS.items():
        d = s13.get(BASE + f"/trucos/{c}").text
        assert "Html { raw:" not in d, f"LEAK de Html en /trucos/{c}"
        assert 'class="tk-svg"' in d, f"falta el SVG en {c}"
        assert d.count("<li>") == 3, f"esperaba 3 pasos en {c}"
        assert 'class="mh-truco-ej"' in d, f"falta el ejemplo en {c}"
        href = re.search(r'<a class="mh-btn" href="([^"]+)"', d).group(1)
        assert href == route, f"{c}: Probalo -> {href}, esperaba {route}"

    # 4. filtrado por grado exacto
    for g in (2, 4, 5, 6, 8, 13):
        got_g = cards(setup_perfil(g).get(BASE + "/trucos").text)
        assert got_g == visibles_a(g), f"grado {g}: veo {sorted(got_g)}, esperaba {sorted(visibles_a(g))}"

    # 5. código inválido -> redirige a /trucos (sin ficha)
    bad = s13.get(BASE + "/trucos/nope", allow_redirects=True).text
    assert 'class="tk-svg"' not in bad, "un código inválido no debería renderizar ficha"

    # 6. decimal por locale (regla 2): es-AR usa coma, en usa punto
    es = s13.get(BASE + "/trucos/equiv").text
    assert "0,5" in es and "0.5" not in es, "equiv en es-AR debería usar 0,5"
    s13.get(BASE + "/lang/en")
    en = s13.get(BASE + "/trucos/equiv").text
    assert "0.5" in en and "0,5" not in en, "equiv en en debería usar 0.5"
    assert "Math tricks" in s13.get(BASE + "/trucos").text, "no cambió a EN"

    print("OK e2e_trucos: 21 fichas (grado 13), cada una con SVG + 3 pasos + ejemplo + ruta Probalo,")
    print("               filtrado por grado exacto (2/4/5/6/8/13), decimal ES=0,5 EN=0.5, sin leak.")


def main():
    if not wait_up():
        print("FAIL: el server no responde en :3000 (levantá con start.bat o `fitz run`)")
        sys.exit(1)
    escenario()


if __name__ == "__main__":
    main()
