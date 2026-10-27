"""Lo que el asistente lee del proyecto: los documentos (README, docs/*.md, la configuracion)
partidos en secciones, y la busqueda de las secciones que tienen que ver con una pregunta."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field

from app.rutas import RAIZ

# Documentos que el asistente puede consultar (todo lo escrito del proyecto).
DOCUMENTOS = ["README.md", "docs/especificacion.md", "docs/paso-a-paso.md", "docs/sensores.md", "docs/componentes.md",
              "docs/conexiones.md", "docs/replicacion.md", "docs/revision-final.md", "docs/costos.md",
              "docs/bitacora.md",
              # Documentos del 2026-09-28 (si todavia no existen, se saltan).
              "docs/logica-interna.md", "docs/electrica.md", "docs/peso.md", "docs/modelo-local.md",
              "docs/fisica-vs-3d.md",
              "config/parametros.yaml", "config/monedas.yaml"]
MAX_CARACTERES_DOCS = 24000      # ~7000 tokens de documentacion por pregunta
MAX_SECCION = 3500

_PALABRAS_VACIAS = set("""
el la los las un una unos unas de del al a en y o u que por para con sin se su sus es son lo le les como
mas pero muy ya hay este esta estos estas ese esa eso cual cuales cuanto cuanta cuantos cuantas donde cuando
porque sobre entre tiene tienen fue ser hace hacer puede pueden cada todo toda todos todas otro otra me mi
yo tu usted nos qué cómo dónde cuándo cuál
""".split())


def normalizar(texto: str) -> str:
    """minusculas y sin tildes (la busqueda no depende de como se escriba)."""
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _palabras(texto: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9_]+", normalizar(texto)) if len(w) >= 3 and w not in _PALABRAS_VACIAS]


@dataclass
class Seccion:
    archivo: str
    titulo: str
    texto: str
    palabras: set[str] = field(default_factory=set)
    foco: float = 1.0          # peso extra por tratar de monedas o del carro (factor_foco)


def _partir(archivo: str, texto: str) -> list[Seccion]:
    """Markdown: por titulos (#, ##, ###). YAML: por claves de primer nivel o
    por puntos del paso a paso. Las secciones largas se cortan."""
    if archivo.endswith(".md"):
        patron = re.compile(r"^#{1,3} .*$", re.M)
    else:
        patron = re.compile(r"^(?:[a-z_]+:|  - numero:).*$", re.M)
    cortes = [m.start() for m in patron.finditer(texto)] or [0]
    if cortes[0] != 0:
        cortes.insert(0, 0)
    secciones = []
    for i, ini in enumerate(cortes):
        trozo = texto[ini:cortes[i + 1] if i + 1 < len(cortes) else len(texto)].strip()
        if not trozo:
            continue
        titulo = trozo.splitlines()[0].lstrip("# ").strip()[:90]
        for k in range(0, len(trozo), MAX_SECCION):
            parte = trozo[k:k + MAX_SECCION]
            secciones.append(Seccion(archivo, titulo if k == 0 else f"{titulo} (sigue)", parte))
    return secciones


_CORPUS: list[Seccion] | None = None
_IDF: dict[str, float] = {}


def corpus(recargar: bool = False) -> list[Seccion]:
    """Todas las secciones de todos los documentos (se lee una vez)."""
    global _CORPUS, _IDF
    if _CORPUS is None or recargar:
        secciones = []
        for rel in DOCUMENTOS:
            ruta = RAIZ / rel
            if ruta.exists():
                # Los cuadritos de color de las tablas de cables (<span style=...>■</span>) no le
                # dicen nada al modelo y gastan contexto: se quitan.
                texto = re.sub(r"<span[^>]*>■</span>", "", ruta.read_text(encoding="utf-8"))
                secciones += _partir(rel, texto)
        for s in secciones:
            s.palabras = set(_palabras(s.titulo + " " + s.texto))
            s.foco = factor_foco(s)
        n = len(secciones) or 1
        df: dict[str, int] = {}
        for s in secciones:
            for w in s.palabras:
                df[w] = df.get(w, 0) + 1
        _IDF = {w: math.log(n / c) for w, c in df.items()}
        _CORPUS = secciones
    return _CORPUS


# Foco del grupo (usuario, 2026-09-28: "LLM enfocado a la parte de monedas y movimiento del carro
# pero sin dejar de lado lo demas"). El elemento 7 es el filtrado de monedas, y el carro es lo que
# mas se le pide al asistente. Las secciones que TRATAN de eso (su titulo lo dice) pesan un poco
# mas en la busqueda; las demas no se excluyen: una pregunta de costos sigue trayendo costos,
# porque el peso extra solo multiplica un puntaje que ya existe (sin palabras en comun, 0 x 1,3 = 0).
FOCO_MONEDAS = re.compile(r"moneda|filtr|rechaz|capacitiv|inductiv|vision|camara|diametro|circular|perfora|"
                          r"confianza|coheren|denominaci|familia|almacen|revolver|lote|clasific")
FOCO_CARRO = re.compile(r"carro|vehiculo|ruta|odometr|evasi|obstacul|muelle|\bmeta\b|encoder|ultrason|acople")
PESO_FOCO = 1.3               # la seccion SE LLAMA como un tema del foco


def factor_foco(s: Seccion) -> float:
    """Cuanto se multiplica el puntaje de una seccion por tratar del foco del grupo. Solo cuenta el
    TITULO (de que trata la seccion); la bitacora no, porque sus titulos resumen una sesion entera
    ("carro mas rapido y proyecto reorganizado") y le ganaban a secciones de verdad (se vio: costos)."""
    if s.archivo == "docs/bitacora.md":
        return 1.0
    titulo = normalizar(s.titulo)
    return PESO_FOCO if FOCO_MONEDAS.search(titulo) or FOCO_CARRO.search(titulo) else 1.0


def buscar(pregunta: str, limite_caracteres: int = MAX_CARACTERES_DOCS) -> list[Seccion]:
    """Las secciones que mas palabras (poco comunes) comparten con la pregunta, con un peso
    extra para las de monedas/filtros/rechazos y carro/ruta (`factor_foco`)."""
    secciones = corpus()
    q = set(_palabras(pregunta))
    if not q:
        return []
    puntaje = []
    for s in secciones:
        comunes = q & s.palabras
        if comunes:
            p = sum(_IDF.get(w, 0) for w in comunes)
            # El titulo pesa el doble: una seccion que SE LLAMA como la pregunta.
            p += sum(_IDF.get(w, 0) for w in comunes & set(_palabras(s.titulo)))
            puntaje.append((p * s.foco, s))
    puntaje.sort(key=lambda x: -x[0])
    elegidas, total = [], 0
    for _, s in puntaje:
        if total + len(s.texto) > limite_caracteres:
            continue
        elegidas.append(s)
        total += len(s.texto)
    return elegidas
