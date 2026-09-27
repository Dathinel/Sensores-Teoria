# Sistema de Logística de Monedas Inteligentes

Proyecto del segundo corte de Micros y Laboratorio, quinto semestre de Ingeniería
Mecatrónica, Universidad Militar Nueva Granada. Elemento diferencial del grupo:
**7 — detector de elementos de monedas y vasos**.

Una línea que filtra monedas colombianas (rechaza botones, arandelas, bloques y monedas
extranjeras), las guarda por denominación, las empaca en vasos tapados de una sola
denominación y las entrega a un carro que sigue una línea, esquiva tres muros, llega a la
meta y vuelve solo. Todo corre hoy en simulación (PyBullet con física real) y se ve en un
visor 3D.

## Cómo verlo

Doble clic en **`visor.bat`**. Si la simulación ya está corriendo, abre el visor 3D; si no,
la arranca (en una ventana minimizada: cerrarla la detiene) y lo abre.

- **Visor 3D** (Three.js): la línea completa en vivo, con el paso a paso guiado, los
  sensores y los componentes, y botones de sabotaje (retirar o cambiar un vaso, meter la
  mano, etc.). Es también el boceto de cómo se construye.
- **Dashboard** (Streamlit, <http://localhost:8501>): producción, línea en vivo, rechazos
  por causa, ruta del carro y la replicación real.
- **Asistente** (pestaña del dashboard): se le pregunta por escrito o por voz por las cifras de
  la corrida o por cualquier parte del proyecto, y se le puede pedir que mueva el carro (avanzar,
  girar, ir a un punto, ir a la meta, volver al muelle) o la línea. Usa DeepSeek (clave en `.env`,
  ver `.env.example`); sin internet, un intérprete local entiende las órdenes y lo básico.

```mermaid
flowchart LR
    B[visor.bat] --> L[app/lanzar.py]
    L --> S[app/supervisor.py<br/>simulación: sim/planta.py + sim/vehiculo_sim.py]
    L --> D[app/dashboard.py<br/>Streamlit + asistente]
    D -- pregunta + estado + docs --> API[API de DeepSeek]
    S -- estado en vivo --> V[visor 3D<br/>app/visor3d]
    S -- eventos, telemetría, ruta --> DB[(SQLite<br/>datos/planta.db)]
    DB --> D
    D -- órdenes --> DB --> S
```

La simulación y el dashboard son procesos separados a propósito (sección 8 de
`CLAUDE.md`): Streamlit reejecuta el script en cada click.

## Documentación

- [`docs/paso-a-paso.md`](docs/paso-a-paso.md) — los 16 puntos del funcionamiento: qué
  sensor usa cada uno, qué entra, qué decide, qué sale y su estado de revisión.
- [`docs/sensores.md`](docs/sensores.md) — los 13 sensores: qué los activa, qué entregan,
  qué mensaje mandan, cómo se replican y cómo se simulan.
- [`docs/componentes.md`](docs/componentes.md) — lista de materiales.
- [`docs/revision-final.md`](docs/revision-final.md) — revisión total: espacio, alcance de sensores,
  pines, alimentación, cables y ruido.
- [`docs/replicacion.md`](docs/replicacion.md) — qué medir para construirlo de verdad y el
  presupuesto de tiempos.
- [`docs/bitacora.md`](docs/bitacora.md) — las decisiones sesión a sesión.
- [`docs/enunciado/`](docs/enunciado/) — la guía del parcial (PDF) y sus figuras.

Los `.md` de `docs/` se generan con `python -m app.documentos` (no se editan a mano).

## Dónde está cada cosa

```
visor.bat              abre el visor (y arranca la simulación si hace falta)
config/                parametros.yaml (todo número del diseño) y monedas.yaml
control/               lógica pura, sin PyBullet: filtrado, cintas, almacén, carro
  hal/                 interfaces de sensores/actuadores y su versión simulada
sim/                   simulación en PyBullet
  planta.py            LA simulación de la línea: cintas, almacén, canaleta, carro
  mundo.py             escena de las dos cintas (URDF en sim/urdf/)
  sensores_sim.py      sensores emulados (incluida la cámara en modo oráculo)
  vehiculo_sim.py      el carro con física real, en su propio mundo
  pista.py             línea central de la pista
  geometria.py         la geometría que dibuja el visor
  catalogos.py         sensores y lista de materiales
  escenarios/          prueba_completa.yaml (la única prueba de la interfaz)
app/                   supervisor, visor 3D, dashboard, asistente, base de datos, documentos
tests/                 pruebas automáticas (+ escenarios de un solo filtro)
docs/                  documentación generada, bitácora y enunciado
```

## Pruebas

```
python -m venv entorno
entorno\Scripts\activate
pip install -r requirements.txt
pytest -q
```

Todas corren sin ventana (PyBullet en modo DIRECT).
