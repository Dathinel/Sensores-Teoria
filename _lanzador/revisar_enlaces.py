#!/usr/bin/env python3
"""
Revisa los enlaces de todos los .md del repo como los resolvería GitHub (solo biblioteca estándar).

Uso (desde cualquier carpeta):

    python _lanzador/revisar_enlaces.py              # todos los .md del repo
    python _lanzador/revisar_enlaces.py 7-brazo-robotico-urdf proyecto-final   # solo esas carpetas
    python _lanzador/revisar_enlaces.py --todos-los-anclas   # lista además los anclas de cada .md

Qué comprueba, en cada .md versionado (más los nuevos que git todavía no ignora):

  1. Enlaces e imágenes relativos: [texto](ruta), ![alt](ruta), [ref]: ruta, <a href>, <img src>.
     La ruta tiene que existir EN GIT con esas mismas mayúsculas (GitHub distingue mayúsculas
     y minúsculas; Windows no, así que un enlace puede funcionar en este PC y no en GitHub). Un
     archivo que existe en el disco pero que el .gitignore excluye cuenta como roto: en GitHub
     no está.
  2. Anclas (#seccion), en el mismo archivo o en otro .md: tienen que coincidir con el "slug"
     que GitHub genera para algún título (o con un id="..." / name="..." escrito a mano).

La regla del slug de GitHub (github-slugger): el texto visible del título, en minúsculas; se
quita todo lo que no sea letra, número, "_", "-" o espacio (las tildes y la ñ SE CONSERVAN; los
emojis, "·", "★", "→", ":", ".", "(", "/"... se quitan); cada espacio pasa a ser un "-" (dos
espacios seguidos dan "--"); y si el slug se repite en el archivo, el segundo lleva "-1", el
tercero "-2", etc. Ejemplo: "## 3. Cómo probarlo (sin ESP32)" -> "#3-cómo-probarlo-sin-esp32".

Los enlaces externos (http, https, mailto) no se revisan: necesitarían internet.
Sale con código 1 si hay algún enlace roto (sirve para revisar antes de subir).
"""

import argparse
import html
import re
import subprocess
import sys
import unicodedata
import urllib.parse
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------------------
# Archivos del repo, como los ve git
# --------------------------------------------------------------------------------------


def archivos_git():
    """Rutas (con "/") versionadas o nuevas no ignoradas. None si git no está disponible."""
    try:
        r = subprocess.run(["git", "-C", str(RAIZ), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                           capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return {x for x in r.stdout.decode("utf-8", "replace").split("\0") if x}


def carpetas_de(archivos):
    dirs = {""}
    for f in archivos:
        partes = f.split("/")[:-1]
        for i in range(1, len(partes) + 1):
            dirs.add("/".join(partes[:i]))
    return dirs


# --------------------------------------------------------------------------------------
# Slugs de GitHub
# --------------------------------------------------------------------------------------

def texto_visible(titulo):
    """El texto que GitHub muestra de un título en markdown (sin `código`, **negritas**, enlaces...)."""
    t = titulo
    # Código en línea: se conserva el contenido tal cual (incluidos sus "_" y "*").
    codigos = []

    def guardar_codigo(m):
        codigos.append(m.group(2))
        return f"\x00{len(codigos) - 1}\x00"
    t = re.sub(r"(`+)(.+?)\1", guardar_codigo, t)
    t = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", t)          # imagen -> su texto alternativo
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)           # enlace -> su texto
    t = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", t)          # enlace por referencia
    t = re.sub(r"<[^>]+>", "", t)                            # etiquetas HTML
    t = re.sub(r"\\([!-/:-@\[-`{-~])", r"\1", t)            # escapes de markdown: \* -> *
    t = re.sub(r"(\*\*|__)(.+?)\1", r"\2", t)                # negrita
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", t)   # cursiva con *
    t = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"\1", t)           # cursiva con _
    t = re.sub(r"~~(.+?)~~", r"\1", t)                       # tachado
    t = re.sub(r"\x00(\d+)\x00", lambda m: codigos[int(m.group(1))], t)
    return html.unescape(t)


def slug(texto):
    """github-slugger: minúsculas; solo letras, marcas (tildes), números, conectores ("_"),
    espacios y guiones; cada espacio -> "-"."""
    out = []
    for c in texto.lower():
        cat = unicodedata.category(c)
        if cat[0] in "LMN" or cat == "Pc" or c in " -":
            out.append("-" if c == " " else c)
    return "".join(out)


FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def lineas_sin_codigo(texto):
    """(número, línea) de las líneas que no están dentro de un bloque ``` / ~~~."""
    dentro, marca = False, ""
    for n, linea in enumerate(texto.splitlines(), 1):
        m = FENCE.match(linea)
        if m:
            if not dentro:
                dentro, marca = True, m.group(1)[0] * 3
                continue
            if linea.strip().startswith(marca):
                dentro = False
                continue
        if not dentro:
            yield n, linea


def anclas_de(texto):
    """Conjunto de anclas válidas de un .md: slugs de títulos (con -1, -2...) e ids a mano."""
    vistos = defaultdict(int)
    anclas = set()
    previa = None
    for _, linea in lineas_sin_codigo(texto):
        titulo = None
        m = re.match(r"^ {0,3}(#{1,6})(?:\s+(.*?))?\s*$", linea)
        if m:
            titulo = re.sub(r"\s+#+\s*$", "", m.group(2) or "")
        elif previa is not None and previa.strip() and re.match(r"^ {0,3}(=+|-+)\s*$", linea) \
                and not re.match(r"^\s*([-*+]\s|\d+[.)]\s|\||>)", previa) and "|" not in previa:
            titulo = previa.strip()   # título "setext" (texto subrayado con === o ---)
        if titulo is not None:
            base = slug(texto_visible(titulo))
            s = base if vistos[base] == 0 else f"{base}-{vistos[base]}"
            vistos[base] += 1
            anclas.add(s)
        for a in re.finditer(r"""<[a-zA-Z][^>]*?\s(?:id|name)\s*=\s*["']([^"']+)["']""", linea):
            anclas.add(a.group(1))
        previa = linea
    return anclas


# --------------------------------------------------------------------------------------
# Enlaces de un .md
# --------------------------------------------------------------------------------------

def quitar_codigo_en_linea(linea):
    return re.sub(r"(`+).+?\1", lambda m: " " * len(m.group(0)), linea)


def destino_md(s, i):
    """Lee el destino de un enlace markdown que empieza en s[i] (justo después de "(").
    Admite <con espacios>, paréntesis balanceados y un "título" opcional."""
    while i < len(s) and s[i] == " ":
        i += 1
    if i < len(s) and s[i] == "<":
        j = s.find(">", i)
        return (s[i + 1:j], j) if j > 0 else (None, i)
    prof, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "(":
            prof += 1
        elif c == ")":
            if prof == 0:
                break
            prof -= 1
        elif c in " \t" and prof == 0:
            break
        j += 1
    return s[i:j], j


def enlaces_de(texto):
    """(línea, tipo, destino) de cada enlace/imagen del .md, fuera de bloques de código."""
    for n, linea in lineas_sin_codigo(texto):
        l = quitar_codigo_en_linea(linea)
        for m in re.finditer(r"(!?)\[", l):
            # Buscar el ] que cierra (con corchetes anidados) y que siga "(".
            prof, j = 0, m.end()
            while j < len(l):
                if l[j] == "\\":
                    j += 2
                    continue
                if l[j] == "[":
                    prof += 1
                elif l[j] == "]":
                    if prof == 0:
                        break
                    prof -= 1
                j += 1
            if j + 1 < len(l) and l[j] == "]" and l[j + 1] == "(":
                dest, _ = destino_md(l, j + 2)
                if dest is not None:
                    yield n, "imagen" if m.group(1) else "enlace", dest
        m = re.match(r"^ {0,3}\[[^\]]+\]:\s*<?([^\s>]+)>?", l)
        if m:
            yield n, "referencia", m.group(1)
        for m in re.finditer(r"""<(a|img|source|video)\b[^>]*?\s(href|src)\s*=\s*["']([^"']*)["']""", l, re.I):
            yield n, "imagen" if m.group(1).lower() != "a" else "enlace", m.group(3)


# --------------------------------------------------------------------------------------
# Revisión
# --------------------------------------------------------------------------------------

def revisar(md_rel, archivos, dirs, cache_anclas):
    """Lista de (línea, tipo, destino, motivo) rotos de un .md (ruta relativa con "/")."""
    rotos = []
    texto = (RAIZ / md_rel).read_text(encoding="utf-8-sig", errors="replace")
    carpeta = md_rel.rsplit("/", 1)[0] if "/" in md_rel else ""

    def anclas(rel):
        if rel not in cache_anclas:
            try:
                cache_anclas[rel] = anclas_de((RAIZ / rel).read_text(encoding="utf-8-sig", errors="replace"))
            except OSError:
                cache_anclas[rel] = set()
        return cache_anclas[rel]

    for n, tipo, dest in enlaces_de(texto):
        dest = dest.strip()
        if not dest or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", dest) or dest.startswith("//"):
            continue   # externo (http:, https:, mailto:, data:...) o vacío
        ruta, _, ancla = dest.partition("#")
        ruta = ruta.split("?", 1)[0]
        ruta = urllib.parse.unquote(ruta)
        if ruta:
            if ruta.startswith("/"):
                objetivo = ruta.lstrip("/")          # en GitHub, "/" es la raíz del repo
            else:
                objetivo = "/".join(x for x in (carpeta, ruta) if x)
            # Normalizar ./ y ../ sin tocar el disco (las mayúsculas tienen que ser las de git).
            partes = []
            fuera = False
            for p in objetivo.split("/"):
                if p in ("", "."):
                    continue
                if p == "..":
                    if not partes:
                        fuera = True
                        break
                    partes.pop()
                else:
                    partes.append(p)
            objetivo = "/".join(partes)
            if fuera:
                rotos.append((n, tipo, dest, "sale de la raíz del repo"))
                continue
            if objetivo not in archivos and objetivo not in dirs:
                en_disco = (RAIZ / objetivo).exists()
                parecido = next((a for a in archivos | dirs if a.lower() == objetivo.lower()), None)
                if parecido:
                    motivo = f"no existe con esas mayúsculas (en git es \"{parecido}\")"
                elif en_disco:
                    motivo = "existe en el disco pero git no lo sube (está en el .gitignore)"
                else:
                    motivo = "no existe"
                rotos.append((n, tipo, dest, motivo))
                continue
        else:
            objetivo = md_rel
        if ancla:
            if objetivo in dirs and objetivo not in archivos:
                readme = (objetivo + "/README.md").lstrip("/")
                if readme not in archivos:
                    continue
                objetivo = readme
            if not objetivo.lower().endswith((".md", ".markdown")):
                continue   # anclas de código (#L10) u otros archivos: no se revisan
            ancla_dec = urllib.parse.unquote(ancla)
            validas = anclas(objetivo)
            if ancla_dec not in validas and ancla_dec.lower() not in validas:
                cerca = sorted(validas, key=lambda a: -parecido_texto(a, ancla_dec.lower()))[:1]
                pista = f" (¿quisiste decir #{cerca[0]}?)" if cerca and parecido_texto(cerca[0], ancla_dec.lower()) > 0.6 else ""
                rotos.append((n, "ancla", dest, f"no hay ningún título con ese ancla en {objetivo}{pista}"))
    return rotos


def parecido_texto(a, b):
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio()


def main():
    ap = argparse.ArgumentParser(description="Revisa enlaces, imágenes y anclas de los .md como GitHub.")
    ap.add_argument("carpetas", nargs="*", help="solo los .md dentro de estas carpetas (por defecto, todos)")
    ap.add_argument("--todos-los-anclas", action="store_true", help="lista también los anclas de cada .md")
    args = ap.parse_args()
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    archivos = archivos_git()
    if archivos is None:
        print("No pude preguntarle a git qué archivos hay (¿está instalado git y esto es el repo?).")
        print("Reviso con lo que hay en el disco (sin distinguir lo ignorado).")
        archivos = {p.relative_to(RAIZ).as_posix() for p in RAIZ.rglob("*")
                    if p.is_file() and not any(x in (".git", "entorno") for x in p.relative_to(RAIZ).parts)}
    dirs = carpetas_de(archivos)
    filtros = [c.strip("/\\").replace("\\", "/") for c in args.carpetas]
    mds = sorted(f for f in archivos if f.lower().endswith(".md") and (RAIZ / f).is_file()
                 and (not filtros or any(f == c or f.startswith(c + "/") for c in filtros)))

    cache = {}
    por_carpeta = defaultdict(list)
    total = 0
    for md in mds:
        rotos = revisar(md, archivos, dirs, cache)
        if args.todos_los_anclas:
            print(f"{md}: " + ", ".join(sorted(cache.get(md) or anclas_de((RAIZ / md).read_text(encoding='utf-8-sig')))))
        for r in rotos:
            por_carpeta[md.split("/")[0] if "/" in md else "(raíz)"].append((md, *r))
            total += 1

    print(f"Revisé {len(mds)} archivos .md.")
    if not total:
        print("Sin enlaces rotos.")
        return 0
    for carpeta in sorted(por_carpeta, key=lambda c: (not c.startswith("("), [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", c)])):
        lista = por_carpeta[carpeta]
        print(f"\n== {carpeta} ({len(lista)}) ==")
        for md, n, tipo, dest, motivo in lista:
            print(f"  {md}:{n}  [{tipo}] {dest}\n      -> {motivo}")
    print(f"\nTotal: {total} enlace(s) roto(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
