"""
aco.py - Optimizacion por colonia de hormigas (ACO) para el laberinto del enjambre.

Es la MISMA logica que corre en C++ dentro de cada ESP32 (firmware/esp32_aco_nodo/aco_core.h).
Se escribio a proposito con las mismas decisiones, en el mismo orden, para que con la misma
semilla los dos lenguajes elijan exactamente los mismos caminos:

  1. El laberinto se lee de maze.json y se convierte en un grafo: cada celda es un nodo y cada
     par de celdas vecinas SIN pared entre ellas es una arista. Las aristas se numeran siempre en
     el mismo orden (celda por celda, primero el vecino de la derecha y luego el de arriba), y ese
     orden es el que usan el firmware y la simulacion para guardar la feromona en un arreglo.
  2. El generador de numeros aleatorios NO es el de Python (random) ni el de Arduino (random()),
     porque cada uno da otra secuencia. Se usa un xorshift32, que son tres desplazamientos y tres
     XOR sobre un entero de 32 bits: es facil de escribir igual en los dos lenguajes.
  3. Las probabilidades se calculan en doble precision (double en C++, float en Python, que es lo
     mismo: IEEE 754 de 64 bits).
  4. La feromona que deposita cada nodo se aplica siempre en el orden nodo 1, nodo 2, nodo 3, sin
     importar en que orden llegaron los paquetes por la red. Sumar en otro orden cambia el ultimo
     bit de un double, y con eso, mucho despues, una hormiga podria elegir distinto.

Se puede usar como libreria (lo importan gemelo_digital.py, emulador_nodos.py y las pruebas) o
correr directo:

    entorno\\Scripts\\python aco.py                 (enjambre de 3 nodos sobre maze.json)
    entorno\\Scripts\\python aco.py --semilla 7 --rho 0.1
"""

from __future__ import annotations

import argparse
import json
import math
import os
import zlib
from collections import deque
from dataclasses import dataclass, field, asdict

AQUI = os.path.dirname(os.path.abspath(__file__))
MAZE_POR_DEFECTO = os.path.join(AQUI, "maze.json")

MASCARA32 = 0xFFFFFFFF


# --------------------------------------------------------------------------------------------
# Parametros del algoritmo
# --------------------------------------------------------------------------------------------
@dataclass
class Parametros:
    """Parametros del ACO. Los valores por defecto son los del enunciado complementario.

    alfa  : peso de la feromona. Con alfa alto la hormiga sigue lo que ya marcaron las demas.
    beta  : peso de la visibilidad (1/distancia). Con beta alto prefiere la arista mas corta.
    rho   : tasa de evaporacion. Al final de cada iteracion queda (1 - rho) de la feromona.
    q     : constante de deposito. Una hormiga con ruta de longitud L deja q/L en cada arista.
    hormigas    : hormigas que suelta CADA nodo en cada iteracion.
    iteraciones : cuantas iteraciones corre el enjambre.
    semilla     : semilla base; cada nodo deriva la suya (ver semilla_de_nodo).
    tau0  : feromona inicial de todas las aristas.
    deposito : "mejor" (por defecto) = en cada iteracion deposita SOLO la mejor hormiga de cada
               nodo (la de ruta mas corta); "todas" = deposita toda hormiga que llego, como en el
               Ant System original. Se cambio a "mejor" porque con "todas" la colonia se estancaba
               en rutas largas del laberinto abierto (prueba 6; ver el README).
    """

    alfa: float = 1.0
    beta: float = 2.0
    rho: float = 0.5
    q: float = 100.0
    hormigas: int = 4
    iteraciones: int = 30
    semilla: int = 12345
    tau0: float = 1.0
    deposito: str = "mejor"


# --------------------------------------------------------------------------------------------
# Generador pseudoaleatorio identico al del firmware
# --------------------------------------------------------------------------------------------
class Xorshift32:
    """xorshift32 de Marsaglia (2003). Periodo 2^32 - 1; el estado nunca puede ser 0."""

    def __init__(self, semilla: int):
        self.estado = (semilla & MASCARA32) or 1

    def siguiente(self) -> int:
        x = self.estado
        x ^= (x << 13) & MASCARA32
        x ^= x >> 17
        x ^= (x << 5) & MASCARA32
        self.estado = x & MASCARA32
        return self.estado

    def uniforme(self) -> float:
        """Numero en [0, 1). Se usan los 24 bits altos: 24 bits caben exactos en un double y en
        un float, asi que la division da el mismo resultado en Python y en el ESP32."""
        return (self.siguiente() >> 8) / 16777216.0


def semilla_de_nodo(semilla_base: int, nodo: int) -> int:
    """Cada ESP32 tiene su propia semilla para que los tres no exploren igual. Se mezcla con la
    constante 0x9E3779B9 (la razon aurea en 32 bits, la misma que usan muchas tablas hash)."""
    s = (semilla_base + 0x9E3779B9 * nodo) & MASCARA32
    return s or 1


# --------------------------------------------------------------------------------------------
# Laberinto -> grafo
# --------------------------------------------------------------------------------------------
@dataclass
class Laberinto:
    nombre: str
    columnas: int
    filas: int
    tam_celda: float
    inicio: int
    meta: int
    aristas: list            # [(u, v)] con u < v, en orden canonico
    longitud: list           # longitud en metros de cada arista
    vecinos: list            # vecinos[u] = [(v, indice_arista), ...] en orden +x, +y, -x, -y
    paredes: list = field(default_factory=list)

    def celda(self, nodo: int) -> tuple:
        """Nodo -> (x, y). x crece hacia la derecha (columna) e y hacia arriba (fila)."""
        return nodo % self.columnas, nodo // self.columnas

    def nodo(self, x: int, y: int) -> int:
        return y * self.columnas + x

    def arista_entre(self, u: int, v: int) -> int:
        for w, e in self.vecinos[u]:
            if w == v:
                return e
        raise KeyError(f"no hay arista entre {u} y {v}")

    def longitud_camino(self, camino: list) -> float:
        # Suma a mano, de izquierda a derecha, y NO con sum(): desde Python 3.12, sum() de floats
        # usa suma compensada (mas exacta) y da 2.4000000000000004 donde el C++ del ESP32, que
        # suma en orden, da 2.3999999999999999. Ese ultimo bit cambia q/L y con eso la feromona.
        total = 0.0
        for a, b in zip(camino, camino[1:]):
            total += self.longitud[self.arista_entre(a, b)]
        return total

    def crc(self) -> int:
        """Huella del mapa. El firmware la manda en HELLO y el gemelo la compara: si el ESP32 se
        flasheo con otro maze.json, el gemelo lo avisa en vez de simular un mundo distinto."""
        return zlib.crc32(texto_canonico(self).encode("ascii")) & MASCARA32


def texto_canonico(lab: Laberinto) -> str:
    """Descripcion de texto unica del grafo; de aqui sale el CRC (igual en el generador del .h)."""
    ar = ",".join(f"{u}-{v}" for u, v in lab.aristas)
    return f"{lab.columnas}x{lab.filas};{lab.tam_celda:.3f};{lab.inicio};{lab.meta};{ar}"


def cargar_laberinto(ruta: str = MAZE_POR_DEFECTO) -> Laberinto:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    cols, fils = int(datos["columnas"]), int(datos["filas"])
    tam = float(datos["tam_celda_m"])

    def nid(par):
        x, y = par
        if not (0 <= x < cols and 0 <= y < fils):
            raise ValueError(f"celda fuera del laberinto: {par}")
        return y * cols + x

    # Las paredes se guardan como pares de celdas vecinas que NO se pueden cruzar.
    bloqueadas = set()
    for a, b in datos.get("paredes", []):
        u, v = nid(a), nid(b)
        ax, ay = a
        bx, by = b
        if abs(ax - bx) + abs(ay - by) != 1:
            raise ValueError(f"pared entre celdas no vecinas: {a} {b}")
        bloqueadas.add((min(u, v), max(u, v)))

    aristas, longitud = [], []
    for y in range(fils):
        for x in range(cols):
            u = y * cols + x
            # Orden canonico: primero la vecina de la derecha (+x), despues la de arriba (+y).
            for dx, dy in ((1, 0), (0, 1)):
                nx, ny = x + dx, y + dy
                if nx < cols and ny < fils:
                    v = ny * cols + nx
                    if (u, v) not in bloqueadas:
                        aristas.append((u, v))
                        # Distancia real entre los centros de dos celdas vecinas = lado de la celda.
                        longitud.append(tam * math.hypot(dx, dy))

    # Lista de vecinos de cada nodo en orden fijo +x, +y, -x, -y (el mismo del firmware).
    indice = {par: i for i, par in enumerate(aristas)}
    vecinos = [[] for _ in range(cols * fils)]
    for y in range(fils):
        for x in range(cols):
            u = y * cols + x
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < cols and 0 <= ny < fils:
                    v = ny * cols + nx
                    clave = (min(u, v), max(u, v))
                    if clave in indice:
                        vecinos[u].append((v, indice[clave]))

    return Laberinto(
        nombre=datos.get("nombre", os.path.basename(ruta)),
        columnas=cols, filas=fils, tam_celda=tam,
        inicio=nid(datos["inicio"]), meta=nid(datos["meta"]),
        aristas=aristas, longitud=longitud, vecinos=vecinos,
        paredes=datos.get("paredes", []),
    )


def camino_optimo(lab: Laberinto) -> list | None:
    """Camino mas corto por busqueda en anchura. Como todas las aristas miden lo mismo, la ruta
    con menos pasos es tambien la de menor longitud. Sirve para saber contra que comparar."""
    previo = {lab.inicio: None}
    cola = deque([lab.inicio])
    while cola:
        u = cola.popleft()
        if u == lab.meta:
            break
        for v, _ in lab.vecinos[u]:
            if v not in previo:
                previo[v] = u
                cola.append(v)
    if lab.meta not in previo:
        return None
    camino, u = [], lab.meta
    while u is not None:
        camino.append(u)
        u = previo[u]
    return camino[::-1]


# --------------------------------------------------------------------------------------------
# Un nodo del enjambre (lo mismo que hace UN ESP32)
# --------------------------------------------------------------------------------------------
class NodoACO:
    """Estado de la colonia dentro de un ESP32: su propia copia de la feromona, su generador
    aleatorio y la mejor ruta que encontraron SUS hormigas."""

    def __init__(self, lab: Laberinto, params: Parametros, nodo: int):
        self.lab = lab
        self.p = params
        self.nodo = nodo
        self.rng = Xorshift32(semilla_de_nodo(params.semilla, nodo))
        self.tau = [params.tau0] * len(lab.aristas)
        # Visibilidad eta = 1/d de cada arista, elevada a beta una sola vez (no cambia nunca).
        self.eta_beta = [(1.0 / d) ** params.beta for d in lab.longitud]
        self.mejor_camino: list | None = None
        self.mejor_longitud = math.inf
        self.iteracion = 0

    def construir_hormiga(self) -> list | None:
        """Una hormiga camina desde el inicio hasta la meta. En cada celda:

            p(i -> j) = tau_ij^alfa * eta_ij^beta / suma sobre los vecinos k permitidos

        donde 'permitido' es: hay arista (no hay pared) y la hormiga no ha pisado esa celda.
        Si llega a una celda sin vecinos permitidos (un callejon o una zona ya recorrida) se
        descarta: devuelve None y no deposita nada."""
        lab, p = self.lab, self.p
        actual = lab.inicio
        camino = [actual]
        visitado = [False] * (lab.columnas * lab.filas)
        visitado[actual] = True
        while actual != lab.meta:
            candidatos, pesos = [], []
            total = 0.0  # acumulado a mano, en orden (ver longitud_camino: nada de sum())
            for v, e in lab.vecinos[actual]:
                if not visitado[v]:
                    candidatos.append(v)
                    pesos.append((self.tau[e] ** p.alfa) * self.eta_beta[e])
                    total += pesos[-1]
            if not candidatos:
                return None  # atrapada: se descarta sin depositar
            # Ruleta: se tira un numero en [0, total) y se recorre la lista acumulando pesos.
            # SIEMPRE se gasta un numero aleatorio por paso (aunque haya un solo candidato),
            # para que el C++ y el Python consuman la secuencia igual.
            r = self.rng.uniforme() * total
            elegido = candidatos[-1]  # por si el redondeo deja r justo en el total
            acumulado = 0.0
            for v, w in zip(candidatos, pesos):
                acumulado += w
                if r < acumulado:
                    elegido = v
                    break
            actual = elegido
            visitado[actual] = True
            camino.append(actual)
        return camino

    def iteracion_local(self) -> dict:
        """Suelta las hormigas de este nodo con la feromona actual y calcula lo que van a
        depositar. NO toca la feromona: eso pasa en aplicar_iteracion, cuando ya se juntaron los
        depositos de los tres nodos.

        Con deposito="mejor" solo deposita la mejor hormiga de esta iteracion (la de L mas
        chica; si empatan, la primera que salio). Con "todas", cada hormiga que llego.

        Devuelve un dict con:
          depositos : {indice_arista: (origen, destino, deposito)} sumado sobre las hormigas
          exitosas, descartadas, caminos (de las hormigas que llegaron)
        """
        lab, p = self.lab, self.p
        depositos: dict[int, list] = {}
        caminos, descartadas = [], 0
        mejor_iter = None  # (L, camino) de la mejor hormiga de ESTA iteracion
        for _ in range(p.hormigas):
            camino = self.construir_hormiga()
            if camino is None:
                descartadas += 1
                continue
            caminos.append(camino)
            L = lab.longitud_camino(camino)
            if L < self.mejor_longitud - 1e-12:
                self.mejor_longitud = L
                self.mejor_camino = list(camino)
            if mejor_iter is None or L < mejor_iter[0] - 1e-12:
                mejor_iter = (L, camino)
        # Quienes depositan: solo la mejor de la iteracion, o todas las que llegaron.
        if p.deposito == "todas":
            depositan = [(lab.longitud_camino(c), c) for c in caminos]
        else:
            depositan = [mejor_iter] if mejor_iter else []
        for L, camino in depositan:
            aporte = p.q / L
            for a, b in zip(camino, camino[1:]):
                e = lab.arista_entre(a, b)
                if e in depositos:
                    depositos[e][2] += aporte
                else:
                    depositos[e] = [a, b, aporte]  # origen/destino: como la cruzo la 1a hormiga
        return {
            "depositos": {e: tuple(v) for e, v in sorted(depositos.items())},
            "exitosas": len(caminos),
            "descartadas": descartadas,
            "caminos": caminos,
        }

    def aplicar_iteracion(self, depositos_por_nodo: dict) -> None:
        """Fin de iteracion:  tau <- (1 - rho) * tau   y luego   tau += suma de depositos.

        depositos_por_nodo = {nodo: {indice_arista: (origen, destino, deposito)}} con los
        depositos propios y los que llegaron por UDP. Se suman en orden de nodo y de arista."""
        f = 1.0 - self.p.rho
        self.tau = [t * f for t in self.tau]
        for n in sorted(depositos_por_nodo):
            for e, (_, _, d) in sorted(depositos_por_nodo[n].items()):
                self.tau[e] += d
        self.iteracion += 1

    def camino_codicioso(self, estricto: bool = False) -> list | None:
        """Sigue siempre la arista de MAS feromona (sin azar). Si ese camino es el optimo, la
        colonia convergio: la memoria compartida ya 'apunta' a la ruta mas corta.

        estricto=True: si en algun paso hay EMPATE de feromona entre las mejores opciones,
        devuelve None (la colonia todavia no decidio). Sin esto, con la feromona aun uniforme el
        camino lo decide el desempate (+x antes que +y) y en maze.json ese desempate cae justo en
        una ruta optima: contaria como 'convergido' algo que nadie aprendio."""
        lab = self.lab
        actual, camino, vis = lab.inicio, [lab.inicio], {lab.inicio}
        while actual != lab.meta:
            opciones = [(self.tau[e], v) for v, e in lab.vecinos[actual] if v not in vis]
            if not opciones:
                return None
            # max por feromona; en empate gana el primero en el orden +x, +y, -x, -y
            mejor = opciones[0]
            for o in opciones[1:]:
                if o[0] > mejor[0]:
                    mejor = o
            if estricto and sum(1 for o in opciones if o[0] == mejor[0]) > 1:
                return None
            actual = mejor[1]
            vis.add(actual)
            camino.append(actual)
        return camino


# --------------------------------------------------------------------------------------------
# Enjambre: tres nodos que comparten la feromona (lo que pasa en la red de los ESP32)
# --------------------------------------------------------------------------------------------
def simular_enjambre(lab: Laberinto, params: Parametros, nodos=(1, 2, 3),
                     caidas: dict | None = None, al_iterar=None) -> dict:
    """Reproduce sin hardware lo que hacen los tres ESP32:

    En cada iteracion k, cada nodo vivo suelta sus hormigas con SU copia de la feromona, manda
    sus depositos (PHER) y espera los de los otros (FIN de la iteracion k). Cuando los tiene,
    evapora y suma todo en orden de nodo. Como los tres parten de la misma feromona y aplican los
    mismos depositos en el mismo orden, sus copias quedan identicas: es una memoria comun sin
    servidor central.

    caidas = {nodo: k} apaga ese nodo desde la iteracion k (prueba 14): deja de mandar
    depositos y los demas siguen con lo que les llega.
    al_iterar(k, info) se llama al final de cada iteracion (lo usa el gemelo para animar).
    """
    caidas = caidas or {}
    estado = {n: NodoACO(lab, params, n) for n in nodos}
    optimo = camino_optimo(lab)
    L_opt = lab.longitud_camino(optimo) if optimo else math.inf
    historial = []
    primera_opt = None
    for k in range(params.iteraciones):
        vivos = [n for n in nodos if caidas.get(n, math.inf) > k]
        resultados = {n: estado[n].iteracion_local() for n in vivos}
        depositos = {n: resultados[n]["depositos"] for n in vivos}
        for n in vivos:
            estado[n].aplicar_iteracion(depositos)
        mejor_enjambre = min(estado[n].mejor_longitud for n in nodos)
        if primera_opt is None and optimo and mejor_enjambre <= L_opt + 1e-9:
            primera_opt = k + 1
        info = {
            "iteracion": k + 1,
            "vivos": vivos,
            "por_nodo": {
                n: {
                    "exitosas": resultados[n]["exitosas"] if n in resultados else 0,
                    "descartadas": resultados[n]["descartadas"] if n in resultados else 0,
                    "mejor_longitud": estado[n].mejor_longitud,
                    "mejor_camino": estado[n].mejor_camino,
                    "depositos": resultados[n]["depositos"] if n in resultados else {},
                }
                for n in nodos
            },
            "tau": list(estado[vivos[0]].tau) if vivos else [],
            "mejor_enjambre": mejor_enjambre,
        }
        historial.append(info)
        if al_iterar:
            al_iterar(k + 1, info)

    # La convergencia se mide con un nodo vivo AL FINAL (el de menor numero): uno que se apago
    # tiene la feromona congelada en la iteracion en que cayo.
    vivos_fin = [n for n in nodos if caidas.get(n, math.inf) > params.iteraciones]
    ref = estado[min(vivos_fin)] if vivos_fin else None
    codicioso = ref.camino_codicioso() if ref else None
    # Convergencia con el criterio estricto: sin empates de feromona en ningun paso.
    decidido = ref.camino_codicioso(estricto=True) if ref else None
    mejor_nodo = min(nodos, key=lambda n: estado[n].mejor_longitud)
    return {
        "optimo": optimo,
        "longitud_optima": L_opt,
        "iteracion_primer_optimo": primera_opt,
        "mejor_camino": estado[mejor_nodo].mejor_camino,
        "mejor_longitud": estado[mejor_nodo].mejor_longitud,
        "camino_codicioso": codicioso,
        "convergio": decidido is not None and abs(lab.longitud_camino(decidido) - L_opt) < 1e-9,
        "por_nodo": {n: {"mejor_camino": estado[n].mejor_camino,
                         "mejor_longitud": estado[n].mejor_longitud} for n in nodos},
        "tau_final": {n: estado[n].tau for n in nodos},
        "historial": historial,
    }


def _formato(camino):
    return "-".join(str(c) for c in camino) if camino else "(ninguno)"


def main():
    ap = argparse.ArgumentParser(description="ACO del enjambre sin hardware")
    ap.add_argument("--maze", default=MAZE_POR_DEFECTO)
    for nombre, tipo in (("alfa", float), ("beta", float), ("rho", float), ("q", float),
                         ("hormigas", int), ("iteraciones", int), ("semilla", int)):
        ap.add_argument(f"--{nombre}", type=tipo, default=getattr(Parametros(), nombre))
    ap.add_argument("--deposito", choices=("mejor", "todas"), default=Parametros().deposito)
    args = ap.parse_args()
    params = Parametros(**{k: getattr(args, k) for k in asdict(Parametros()) if hasattr(args, k)})
    lab = cargar_laberinto(args.maze)
    r = simular_enjambre(lab, params)
    print(f"Laberinto {lab.nombre}: {len(lab.aristas)} aristas, CRC {lab.crc():08X}")
    print(f"Parametros: {params}")
    print(f"Optimo (BFS): {_formato(r['optimo'])}  L = {r['longitud_optima']:.2f} m")
    for n, d in r["por_nodo"].items():
        print(f"  nodo {n}: L = {d['mejor_longitud']:.2f} m  {_formato(d['mejor_camino'])}")
    print(f"Primera vez con el optimo: iteracion {r['iteracion_primer_optimo']}")
    print(f"Camino por maxima feromona: {_formato(r['camino_codicioso'])}  convergio={r['convergio']}")


if __name__ == "__main__":
    main()
