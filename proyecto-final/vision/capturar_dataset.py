"""Captura del dataset de monedas con la webcam del montaje (fase 5, docs/especificacion.md sección 12).

El clasificador se entrena con fotos DEL PROPIO MONTAJE: misma cámara, misma altura (~15 cm sobre
E3), mismo anillo de luz y la cinta negra de fondo. Así el modelo no tiene que aprender a ignorar
fondos ni luces distintas y puede ser chico. Meta: 80-150 fotos por clase, anverso y reverso,
incluidas piezas gastadas, manchadas o descoloridas (ver docs/replicacion.md).

    python -m vision.capturar_dataset              # cámara 0
    python -m vision.capturar_dataset --camara 1   # otra cámara (la USB del montaje suele ser la 1)

Teclas en la ventana:
    1-9      elige la clase (la lista sale en pantalla: las 9 que se entrenan)
    0        clase "otro" (monedas extranjeras, botones metálicos, arandelas...)
    espacio  guarda una foto de la clase elegida
    q        salir

Las fotos quedan en vision/dataset/<clase>/<clase>_<n>.jpg (fuera de git: pesan). Se guarda la
imagen COMPLETA de la cámara; el recorte alrededor de la pieza lo hace después vision/entrenar.py,
igual que lo hará el pipeline de la línea, para que entrenamiento y uso vean lo mismo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "vision" / "dataset"


def clases() -> list[str]:
    """Las clases que se entrenan (familias de `familias_entrenadas` en config/monedas.yaml) + "otro".
    Salen de la misma tabla que usa la línea: si se agrega una familia, aparece sola aquí."""
    sys.path.insert(0, str(RAIZ))
    from control import monedas

    return [c for c in monedas.clases_colombianas() if monedas.reconocible(c)] + ["otro"]


def contar(clase: str) -> int:
    carpeta = DATASET / clase
    return len(list(carpeta.glob("*.jpg"))) if carpeta.exists() else 0


def main() -> None:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--camara", type=int, default=0, help="índice de la cámara (0, 1, ...)")
    args = analizador.parse_args()

    import cv2  # aqui y no arriba: `clases()` se puede usar (y probar) sin OpenCV

    lista = clases()
    # CAP_DSHOW en Windows: abre la webcam en ~1 s (el backend por defecto tarda mucho más).
    cam = cv2.VideoCapture(args.camara, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    if not cam.isOpened():
        print(f"No se pudo abrir la cámara {args.camara}. ¿Está conectada? Probar con --camara 1.")
        sys.exit(1)
    # 1080p si la cámara puede: a 15 cm eso da ~0,1 mm por píxel (docs/revision-final.md, sensor 4).
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    elegida = 0
    print("Clases:", ", ".join(f"{(i + 1) % 10 if i < 9 else 0}={c}" for i, c in enumerate(lista)))
    while True:
        ok, cuadro = cam.read()
        if not ok:
            print("La cámara dejó de mandar imágenes.")
            break
        vista = cuadro.copy()
        alto, ancho = vista.shape[:2]
        # Cruz en el centro: la pieza tiene que quedar ahí (donde la deja la casilla de E3).
        cv2.drawMarker(vista, (ancho // 2, alto // 2), (0, 200, 255), cv2.MARKER_CROSS, 40, 2)
        texto = f"clase: {lista[elegida]}  ({contar(lista[elegida])} fotos)   espacio=foto  q=salir"
        cv2.putText(vista, texto, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2)
        # La ventana se muestra achicada: una de 1080p no cabe en la pantalla de un portátil.
        cv2.imshow("Dataset de monedas", cv2.resize(vista, (ancho * 720 // alto, 720)))
        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break
        if ord("0") <= tecla <= ord("9"):
            indice = (tecla - ord("1")) % 10          # "1" -> 0 ... "9" -> 8, "0" -> 9 ("otro")
            if indice < len(lista):
                elegida = indice
        elif tecla == ord(" "):
            carpeta = DATASET / lista[elegida]
            carpeta.mkdir(parents=True, exist_ok=True)
            ruta = carpeta / f"{lista[elegida]}_{contar(lista[elegida]) + 1:04d}.jpg"
            cv2.imwrite(str(ruta), cuadro, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print("guardada", ruta.relative_to(RAIZ))
    cam.release()
    cv2.destroyAllWindows()
    print("Fotos por clase:", {c: contar(c) for c in lista})


if __name__ == "__main__":
    main()
