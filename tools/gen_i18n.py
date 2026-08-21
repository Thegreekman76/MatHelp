#!/usr/bin/env python3
"""
gen_i18n.py — compila locales/*.json a módulos Fitz.

Por qué existe: Fitz v0.47.0 no tiene acceso al filesystem (lo único que lee
del disco es load_env), así que los catálogos de traducción NO se pueden
cargar en runtime. Tienen que ser código compilado.

Pero no queremos perder el JSON: un traductor tiene que poder editar un
archivo sin tocar Fitz. Así que el JSON es la fuente de verdad y esto lo
compila a `src/cat_<locale>.fitz`.

El día que exista `fs.read()` (docs/norte-mathelp.md · FITZ-03) este script
se borra y el loader lee los .json directo.

Uso:
    python tools/gen_i18n.py
"""

import json
import pathlib
import sys

# En Windows la consola es cp1252 por defecto y los ✓/✗ de los mensajes la
# rompen (UnicodeEncodeError). Forzamos UTF-8 en la salida — no afecta los
# .fitz generados, que ya se escriben con encoding="utf-8" explícito.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

RAIZ = pathlib.Path(__file__).resolve().parent.parent
LOCALES = RAIZ / "locales"
SRC = RAIZ / "src"

# locale del archivo -> sufijo del módulo Fitz (los guiones no son ident)
def sufijo(locale: str) -> str:
    return locale.replace("-", "_").lower()


def escapar(s: str) -> str:
    """Escapa para un literal de string de Fitz.

    Ojo con las llaves: Fitz interpola {expr} dentro de strings, así que una
    llave literal en una traducción tiene que ir escapada como \\{ y \\}.
    """
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("{", "\\{")
    s = s.replace("}", "\\}")
    return s


def main() -> int:
    archivos = sorted(LOCALES.glob("*.json"))
    if not archivos:
        print(f"✗ no hay .json en {LOCALES}", file=sys.stderr)
        return 1

    catalogos = {}
    for f in archivos:
        catalogos[f.stem] = json.loads(f.read_text(encoding="utf-8"))

    # --- Validación: ningún locale puede tener claves faltantes -----------
    # Esto es lo que evita que alguien agregue texto y se olvide de traducirlo.
    todas = set()
    for datos in catalogos.values():
        todas |= set(datos.keys())

    faltantes = False
    for locale, datos in catalogos.items():
        falta = sorted(todas - set(datos.keys()))
        if falta:
            faltantes = True
            print(f"✗ {locale} — faltan {len(falta)} claves:", file=sys.stderr)
            for k in falta:
                print(f"    {k}", file=sys.stderr)

    if faltantes:
        print("\n✗ abortado: completá las traducciones primero.", file=sys.stderr)
        return 1

    # --- Emisión ----------------------------------------------------------
    for locale, datos in sorted(catalogos.items()):
        suf = sufijo(locale)
        destino = SRC / f"cat_{suf}.fitz"
        lineas = [
            f"// cat_{suf}.fitz — GENERADO por tools/gen_i18n.py. NO EDITAR.",
            f"// Fuente: locales/{locale}.json",
            "//",
            "// Existe porque Fitz no puede leer archivos en runtime (FITZ-03).",
            "",
            f"fn cat_{suf}(key: Str) -> Str {{",
            "    return match key {",
        ]
        for k in sorted(datos.keys()):
            lineas.append(f'        "{escapar(k)}" => "{escapar(datos[k])}",')
        lineas.append('        _ => key,')
        lineas.append("    }")
        lineas.append("}")
        lineas.append("")
        destino.write_text("\n".join(lineas), encoding="utf-8")
        print(f"✓ {destino.relative_to(RAIZ)} — {len(datos)} claves")

    print(f"\n✓ {len(catalogos)} locales, {len(todas)} claves, sin faltantes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
