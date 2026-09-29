"""Sistema de diseño del dashboard: colores, tipografías, CSS y las piezas de
HTML que se repiten (tarjetas, indicadores, chips, avisos, LEDs, frases).

Es el MISMO lenguaje visual que el visor 3D (`app/visor3d/index.html`): fondo
#0e1116, paneles #161b22, bordes #2a313c, Space Grotesk para el texto e IBM
Plex Mono para cifras y códigos, y cinco colores con significado fijo:

    ámbar  #f2b134  lo principal / en proceso / guardado
    verde  #3fb68b  bien / aceptado / trabajando
    rojo   #e5534b  rechazo / alarma / sin internet
    azul   #539bf5  carro / información / terminado
    morado #b083f0  visión / hardware real / odometría

Regla: ninguna pestaña escribe CSS ni colores sueltos; todo sale de aquí.
Las funciones `html_*` devuelven texto HTML y `pintar()` lo muestra.
"""

from __future__ import annotations

import html as _html

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------------------
# paleta
# ---------------------------------------------------------------------------

FONDO = "#0e1116"
PANEL = "#161b22"
PANEL_2 = "#1c222b"
HUNDIDO = "#07090c"      # el interior de una casilla de la cinta (cinta negra mate)
BORDE = "#2a313c"
TEXTO = "#e6e8eb"
TENUE = "#8b949e"
APAGADO = "#586069"

AMBAR = "#f2b134"
VERDE = "#3fb68b"
ROJO = "#e5534b"
AZUL = "#539bf5"
MORADO = "#b083f0"
GRIS = TENUE

TONOS = {"ambar": AMBAR, "verde": VERDE, "rojo": ROJO, "azul": AZUL, "morado": MORADO, "gris": GRIS}

LETRA = "'Space Grotesk', system-ui, sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, monospace"

# ---------------------------------------------------------------------------
# CSS (una sola hoja; se inyecta al principio de cada ejecución)
# ---------------------------------------------------------------------------

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root {{
  --fondo:{FONDO}; --panel:{PANEL}; --panel2:{PANEL_2}; --hundido:{HUNDIDO}; --borde:{BORDE};
  --texto:{TEXTO}; --tenue:{TENUE}; --apagado:{APAGADO};
  --ambar:{AMBAR}; --verde:{VERDE}; --rojo:{ROJO}; --azul:{AZUL}; --morado:{MORADO};
  --r:10px; --r-chico:6px;
  --e1:4px; --e2:8px; --e3:12px; --e4:16px; --e5:24px;
}}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp h1, .stApp h2,
.stApp h3, .stApp h4, .stMarkdown, [data-testid="stSidebar"] {{ font-family:{LETRA}; }}
.stApp code, .mono {{ font-family:{MONO}; }}
.block-container {{ padding:2.6rem 2.5rem 3rem; max-width:1560px; }}
[data-testid="stHeader"] {{ background:transparent; }}

/* --- pestañas ------------------------------------------------------------ */
/* Las 9 pestañas tienen que verse todas, también a ~900 px: si no caben en una fila pasan a una
   segunda (antes quedaban 4 a la vista y el resto detrás de una flecha de desplazamiento). La barra
   ámbar que Streamlit mueve bajo la pestaña activa se calcula para UNA fila, así que se oculta y la
   activa se marca con su propio borde inferior. */
.stTabs [role="tablist"] {{ gap:2px; border-bottom:1px solid var(--borde); flex-wrap:wrap; overflow:visible !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
.stTabs [data-baseweb="tab-list"] ~ button, .stTabs div:has(> [role="tablist"]) > button {{ display:none; }}
.stTabs [role="tab"] {{ padding:6px 7px; border-radius:8px 8px 0 0; border-bottom:2px solid transparent; }}
.stTabs [role="tab"][aria-selected="true"] {{ border-bottom-color:var(--ambar); }}
.stTabs [role="tab"] p {{ font-size:0.8rem; font-weight:500; white-space:nowrap; }}
.stTabs [role="tab"][aria-selected="true"] {{ background:var(--panel); }}
.stTabs [role="tab"][aria-selected="true"] p {{ color:var(--ambar); font-weight:600; }}

/* --- barra lateral --------------------------------------------------------- */
[data-testid="stSidebar"] {{ background:#11151b; border-right:1px solid var(--borde); }}
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarContent"] {{ padding-top:0.6rem; }}
.lado-marca {{ display:flex; align-items:center; gap:10px; margin:0 0 var(--e3); }}
.lado-marca .moneda {{ width:30px; height:30px; border-radius:50%; flex:none;
  background:radial-gradient(circle at 35% 30%, #ffe08a, #c9982e 70%); box-shadow:0 0 0 2px #7a5a14 inset; }}
.lado-marca b {{ font-size:0.98rem; display:block; line-height:1.1; }}
.lado-marca span {{ font-size:0.72rem; color:var(--tenue); }}

/* --- paneles (st.container(border=True, key="panel_...")) ------------------- */
[class*="st-key-panel"] {{ background:var(--panel); border-radius:var(--r); }}
[class*="st-key-panel"] [class*="st-key-panel"] {{ background:var(--panel2); }}

/* --- títulos de sección ----------------------------------------------------- */
.sec {{ display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; margin:var(--e4) 0 var(--e2); }}
.sec h3 {{ font-size:1.02rem; font-weight:600; margin:0; padding:0; letter-spacing:-0.005em; color:var(--texto); }}
.sec .num {{ font-family:{MONO}; font-size:0.72rem; color:var(--fondo); background:var(--ambar); border-radius:999px;
  padding:1px 8px; font-weight:600; }}
.sec .sec-nota {{ font-size:0.8rem; color:var(--tenue); }}
.sec.primera {{ margin-top:var(--e1); }}
.subgrupo {{ font-size:0.72rem; color:var(--tenue); text-transform:uppercase; letter-spacing:.06em; margin:var(--e3) 0 var(--e1); }}
.subgrupo b {{ color:var(--texto); font-weight:600; }} .subgrupo span {{ text-transform:none; letter-spacing:0; }}
.nota {{ color:var(--tenue); font-size:0.8rem; line-height:1.45; }}
.nota code, .aviso code {{ font-size:0.76rem; background:rgba(255,255,255,.06); padding:0 4px; border-radius:4px; }}

/* --- cabecera ---------------------------------------------------------------- */
.cabecera {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }}
.cabecera h1 {{ font-size:1.5rem; margin:0 6px 0 0; padding:0; font-weight:700; letter-spacing:-0.015em; }}
.cabecera .moneda {{ width:26px; height:26px; border-radius:50%; flex:none;
  background:radial-gradient(circle at 35% 30%, #ffe08a, #c9982e 70%); box-shadow:0 0 0 2px #7a5a14 inset; }}
.subtitulo {{ color:var(--tenue); font-size:0.82rem; margin:4px 0 var(--e2); }}

/* --- chips ------------------------------------------------------------------ */
.chip {{ display:inline-flex; align-items:center; gap:5px; padding:2px 10px; border-radius:999px; white-space:nowrap;
  font-family:{MONO}; font-size:0.74rem; border:1px solid var(--borde); color:var(--tenue); background:transparent; }}
.chip.lleno {{ color:var(--fondo); font-weight:600; }}
.chip.lleno.rojo {{ color:#fff; }}
.chip.lleno.verde {{ background:var(--verde); border-color:var(--verde); }}
.chip.lleno.ambar {{ background:var(--ambar); border-color:var(--ambar); }}
.chip.lleno.rojo {{ background:var(--rojo); border-color:var(--rojo); }}
.chip.lleno.azul {{ background:var(--azul); border-color:var(--azul); }}
.chip.lleno.morado {{ background:var(--morado); border-color:var(--morado); }}
.chip.borde.azul {{ color:var(--texto); border-color:var(--azul); }}
.chip.borde.verde {{ color:var(--verde); border-color:rgba(63,182,139,.55); }}

/* --- avisos ------------------------------------------------------------------ */
.aviso {{ border-radius:var(--r-chico); padding:9px 13px; margin:var(--e2) 0; font-size:0.88rem; line-height:1.45;
  border:1px solid var(--borde); border-left-width:4px; background:var(--panel); }}
.aviso.ambar {{ border-color:rgba(242,177,52,.45); border-left-color:var(--ambar); background:rgba(242,177,52,.07); }}
.aviso.rojo {{ border-color:rgba(229,83,75,.5); border-left-color:var(--rojo); background:rgba(229,83,75,.09); }}
.aviso.azul {{ border-color:rgba(83,155,245,.45); border-left-color:var(--azul); background:rgba(83,155,245,.07); }}
.aviso.morado {{ border-color:rgba(176,131,240,.45); border-left-color:var(--morado); background:rgba(176,131,240,.07); }}
.aviso.verde {{ border-color:rgba(63,182,139,.45); border-left-color:var(--verde); background:rgba(63,182,139,.07); }}
/* Avisos GRANDES (usuario, 2026-09-27): que se note de lejos si no es en vivo o no hay internet. */
.aviso-grande {{ display:flex; gap:14px; align-items:flex-start; border-radius:var(--r); padding:12px 18px;
  margin:var(--e2) 0 var(--e1); font-size:0.92rem; line-height:1.45; }}
.aviso-grande .ico {{ font-size:1.5rem; line-height:1.2; }}
.aviso-grande b.titulo {{ display:block; font-size:1.12rem; letter-spacing:.05em; margin-bottom:2px; font-weight:700; }}
.aviso-grande.demo {{ background:var(--ambar); color:#1b1300; }}
.aviso-grande.offline {{ background:rgba(229,83,75,.13); border:2px solid var(--rojo); }}
.aviso-grande.offline b.titulo {{ color:#ff8a80; }}

/* --- indicadores (cifras grandes) ------------------------------------------- */
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:var(--e3); margin:var(--e2) 0 var(--e3); }}
.kpi {{ background:var(--panel); border:1px solid var(--borde); border-radius:var(--r); padding:12px 16px 12px; position:relative; overflow:hidden; }}
.kpi::before {{ content:''; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--c, var(--tenue)); }}
.kpi .k-et {{ font-size:0.72rem; color:var(--tenue); text-transform:uppercase; letter-spacing:.06em; }}
.kpi .k-val {{ font-family:{MONO}; font-size:1.7rem; font-weight:600; color:var(--texto); line-height:1.25; margin-top:2px; }}
.kpi .k-det {{ font-size:0.76rem; color:var(--apagado); margin-top:2px; line-height:1.35; }}

/* --- tarjetas de estado ------------------------------------------------------ */
.tarjetas {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(165px, 1fr)); gap:var(--e3); margin:var(--e2) 0 var(--e3); }}
.tarjeta {{ background:var(--panel); border:1px solid var(--borde); border-radius:var(--r); padding:11px 15px; }}
.tarjeta .t-titulo {{ display:flex; align-items:center; gap:7px; font-size:0.72rem; color:var(--tenue);
  text-transform:uppercase; letter-spacing:.06em; }}
.tarjeta .t-titulo i {{ width:8px; height:8px; border-radius:50%; background:var(--c); box-shadow:0 0 8px var(--c); }}
.tarjeta .t-estado {{ font-size:1.1rem; font-weight:600; margin:3px 0 1px; color:var(--c); }}
.tarjeta .t-detalle {{ font-size:0.8rem; color:var(--tenue); line-height:1.4; }}

/* --- LEDs de sensores -------------------------------------------------------- */
.leds {{ display:flex; flex-wrap:wrap; gap:6px 18px; margin:var(--e2) 0 var(--e1); padding:8px 12px;
  background:var(--panel); border:1px solid var(--borde); border-radius:var(--r-chico); }}
.leds .rot {{ font-size:0.7rem; color:var(--apagado); text-transform:uppercase; letter-spacing:.06em; align-self:center; }}
.led {{ display:flex; align-items:center; gap:7px; font-size:0.82rem; color:var(--tenue); }}
.led i {{ width:10px; height:10px; border-radius:50%; background:#30363d; display:inline-block; }}
.led.on {{ color:var(--texto); }}
.led.on i {{ background:var(--verde); box-shadow:0 0 8px var(--verde); }}
.led.on.alarma i {{ background:var(--rojo); box-shadow:0 0 8px var(--rojo); }}

/* --- frases (lo que pasa, en palabras simples) ------------------------------ */
.frases {{ display:flex; flex-direction:column; gap:5px; }}
.frase {{ display:flex; gap:9px; align-items:flex-start; font-size:0.86rem; line-height:1.4; padding:6px 10px;
  border-radius:var(--r-chico); background:var(--panel); border:1px solid var(--borde); border-left:3px solid var(--c, var(--borde)); }}
.frase .hora {{ font-family:{MONO}; font-size:0.7rem; color:var(--apagado); min-width:56px; padding-top:2px; }}
.frase .ico {{ min-width:18px; text-align:center; }}
.bitacora {{ font-family:{MONO}; font-size:0.74rem; color:var(--tenue); line-height:1.6; background:var(--panel);
  border:1px solid var(--borde); border-radius:var(--r-chico); padding:10px 12px; max-height:520px; overflow-y:auto; }}
.bitacora .h {{ color:var(--apagado); }} .bitacora .o {{ color:var(--ambar); }}
.bitacora b {{ color:var(--texto); font-weight:600; }}

/* --- respuesta de la línea a una orden ------------------------------------ */
.respuesta {{ border-radius:var(--r-chico); padding:7px 11px; margin:var(--e2) 0; font-size:0.84rem; line-height:1.4; }}
.respuesta.ok {{ background:rgba(63,182,139,.12); border:1px solid rgba(63,182,139,.6); }}
.respuesta.no {{ background:rgba(242,177,52,.11); border:1px solid rgba(242,177,52,.6); }}
.respuesta .de {{ display:block; font-size:0.68rem; color:var(--tenue); text-transform:uppercase; letter-spacing:.06em; }}

/* --- leyenda de un mapa o gráfica ------------------------------------------- */
.leyenda {{ display:flex; flex-wrap:wrap; gap:4px 16px; font-size:0.78rem; color:var(--tenue); margin:2px 0 var(--e2); }}
.leyenda span b {{ font-weight:700; margin-right:4px; }}

/* --- causas de rechazo ------------------------------------------------------ */
.causas {{ display:flex; flex-direction:column; gap:6px; }}
.causa {{ display:grid; grid-template-columns:34px 1fr; gap:10px; align-items:center; padding:7px 10px;
  background:var(--panel); border:1px solid var(--borde); border-radius:var(--r-chico); }}
.causa .n {{ font-family:{MONO}; font-size:1.05rem; font-weight:600; text-align:center; color:var(--texto); }}
.causa.cero .n {{ color:var(--apagado); }}
.causa .t {{ font-size:0.86rem; }} .causa .t small {{ display:block; color:var(--tenue); font-size:0.76rem; }}
.etiqueta {{ font-family:{MONO}; font-size:0.66rem; padding:0 6px; border-radius:999px; border:1px solid var(--c); color:var(--c); margin-left:6px; }}

/* --- dibujos de la línea (cintas, almacén, vasos) ---------------------------- */
.cinta {{ display:grid; gap:8px; margin:var(--e1) 0 var(--e1); }}
.casilla {{ background:var(--hundido); border:1px solid var(--borde); border-radius:8px; padding:8px 6px 10px;
  min-height:150px; display:flex; flex-direction:column; align-items:center; gap:6px; }}
.casilla .est {{ font-size:0.7rem; color:var(--tenue); text-transform:uppercase; letter-spacing:.06em; text-align:center; }}
.casilla .num {{ font-family:{MONO}; font-size:0.68rem; color:var(--apagado); margin-top:auto; }}
.casilla.baja {{ min-height:122px; }}
.ficha {{ display:flex; align-items:center; justify-content:center; font-family:{MONO};
  font-weight:600; font-size:0.78rem; color:#1b1300; margin-top:6px; }}
.ficha.moneda {{ border-radius:50%; background:radial-gradient(circle at 35% 30%, #ffe08a, #c9982e 70%); }}
.ficha.boton_plastico {{ border-radius:50%; background:#d9259f; color:#fff; }}
.ficha.boton_metalico {{ border-radius:50%; background:radial-gradient(circle at 35% 30%, #d0d4da, #7d828a 70%); }}
.ficha.bloque {{ border-radius:3px; background:#3372c4; color:#fff; }}
.ficha.mano {{ border:2px dashed var(--rojo); border-radius:50%; color:var(--rojo); }}
.ficha .ojal {{ width:5px; height:5px; background:var(--hundido); border-radius:50%; margin:0 2px; }}
.veredicto {{ font-size:0.72rem; text-align:center; line-height:1.25; }}
.veredicto.ok {{ color:var(--verde); }} .veredicto.no {{ color:var(--rojo); }} .veredicto.pend {{ color:var(--tenue); }}
.vacia {{ color:#30363d; font-size:0.75rem; margin-top:30px; }}
.vaso {{ width:54px; height:70px; border:2px solid #9aa4b1; border-top:none; border-radius:0 0 10px 10px;
  position:relative; overflow:hidden; margin-top:10px; background:rgba(154,164,177,.06); }}
.vaso .nivel {{ position:absolute; bottom:0; left:0; right:0; background:linear-gradient(#ffd66b,#c9982e); }}
.vaso.tapado::before {{ content:''; position:absolute; top:0; left:-2px; right:-2px; height:6px; background:#f28c28; z-index:2; }}
.vaso.ausente {{ border-style:dashed; border-color:var(--rojo); background:none; }}
.vaso.figura {{ width:44px; height:28px; margin-top:52px; border:none; border-radius:4px; background:#8a4fcf; }}
.estado-vaso {{ font-family:{MONO}; font-size:0.7rem; padding:1px 8px; border-radius:999px; border:1px solid var(--c); color:var(--c); }}
.tubo {{ position:relative; width:34px; height:70px; border:2px solid #9aa4b1; border-top:none; border-radius:0 0 6px 6px;
  margin-top:6px; overflow:hidden; }}
.tubo .nivel {{ position:absolute; bottom:0; left:0; right:0; background:var(--c); }}
.tubo .lote {{ position:absolute; left:-4px; right:-4px; border-top:2px dashed var(--texto); }}
.caja-otras {{ width:40px; height:40px; border:2px dashed var(--tenue); border-radius:6px; margin-top:20px;
  display:flex; align-items:center; justify-content:center; font-family:{MONO}; }}

/* --- widgets de Streamlit, afinados ------------------------------------------ */
.stButton button, .stDownloadButton button {{ border-radius:8px; font-weight:500; }}
.stButton button[kind="primary"] {{ color:#1b1300; font-weight:600; }}
/* Texto de los botones: pasa a otra línea en vez de cortarse con "…" (a 900 px el panel "Mover el
   carro" quedaba solo con íconos y los sabotajes y ejemplos del asistente cortados; 2026-09-28). */
.stButton button [data-testid="stMarkdownContainer"],
.stButton button [data-testid="stMarkdownContainer"] p {{ white-space:normal; overflow:visible; text-overflow:clip; }}
.stButton button [data-testid="stMarkdownContainer"] {{ line-height:1.25; overflow-wrap:normal; word-break:normal; }}
/* Y en los paneles angostos, cada par de botones o de casillas pasa a una columna en vez de apretarse
   (pantalla de ~900 px con la barra lateral abierta). */
.st-key-panel_ordenes [data-testid="stHorizontalBlock"], .st-key-panel_sabotajes [data-testid="stHorizontalBlock"],
[data-testid="stHorizontalBlock"]:not(:has([data-testid="stHorizontalBlock"])):has(.st-key-panel_filtro) {{ flex-wrap:wrap; }}
.st-key-panel_ordenes [data-testid="stColumn"] {{ flex:1 1 130px; min-width:130px; }}
.st-key-panel_sabotajes [data-testid="stColumn"] {{ flex:1 1 170px; min-width:170px; }}
[data-testid="stHorizontalBlock"]:not(:has([data-testid="stHorizontalBlock"])):has(.st-key-panel_filtro) > [data-testid="stColumn"] {{ flex:1 1 220px; min-width:220px; }}
/* Columnas PRINCIPALES de cada pestaña (las de primer nivel, no las de adentro de un panel): en
   pantallas angostas se apilan una debajo de la otra en vez de dejar la derecha de ~200 px (mapa
   aplastado en "Carro y ruta", respuestas en una palabra por línea en "Pruebas" y "Línea en vivo").
   Angosta = el área principal queda por debajo de ~900 px: ventana de hasta 1200 px con la barra
   lateral abierta (le quita ~300), o de hasta 960 px con la barra cerrada. Streamlit por su cuenta
   solo apila por debajo de 640 px de ventana. 2026-09-28. */
@media (max-width:1200px) {{
  .stApp:has([data-testid="stSidebar"][aria-expanded="true"]) .block-container
    [data-testid="stHorizontalBlock"]:not([data-testid="stColumn"] [data-testid="stHorizontalBlock"]) {{ flex-wrap:wrap; }}
  .stApp:has([data-testid="stSidebar"][aria-expanded="true"]) .block-container
    [data-testid="stHorizontalBlock"]:not([data-testid="stColumn"] [data-testid="stHorizontalBlock"]) > [data-testid="stColumn"] {{
    flex:1 1 100% !important; width:100% !important; min-width:100% !important; }}
}}
@media (max-width:960px) {{
  .block-container [data-testid="stHorizontalBlock"]:not([data-testid="stColumn"] [data-testid="stHorizontalBlock"]) {{ flex-wrap:wrap; }}
  .block-container [data-testid="stHorizontalBlock"]:not([data-testid="stColumn"] [data-testid="stHorizontalBlock"]) > [data-testid="stColumn"] {{
    flex:1 1 100% !important; width:100% !important; min-width:100% !important; }}
}}
/* Tablas de texto (html_tabla): el texto largo pasa a otra línea dentro de la celda, así la tabla
   cabe en su columna sin barra de desplazamiento horizontal (st.dataframe no ajusta el texto). */
.tabla-texto {{ width:100%; border-collapse:collapse; font-size:0.8rem; line-height:1.4; margin:var(--e1) 0 var(--e3);
  border:1px solid var(--borde); border-radius:var(--r-chico); overflow:hidden; }}
.tabla-texto th {{ text-align:left; font-weight:600; color:var(--tenue); font-size:0.7rem; text-transform:uppercase;
  letter-spacing:.05em; background:var(--panel); padding:6px 9px; border-bottom:1px solid var(--borde); }}
/* Nunca partir una palabra a la mitad ("independien-tes", "compuert-a" a 900 px con la barra lateral
   abierta, revisión visual 2026-09-29): el texto se corta solo entre palabras y sin guiones. Si la
   tabla no cabe, en vez de apretar las columnas pasa a filas apiladas (ver @container abajo). */
.tabla-texto td {{ padding:6px 9px; border-top:1px solid #21262d; vertical-align:top; color:var(--texto);
  overflow-wrap:normal; word-break:normal; hyphens:none; }}
.tabla-texto td.num {{ font-family:{MONO}; white-space:nowrap; text-align:right; }}
.tabla-texto td.corto {{ white-space:nowrap; }}
.tabla-texto td.no {{ color:var(--rojo); font-weight:600; }} .tabla-texto td.ok {{ color:var(--verde); }}
.tabla-texto td.espera {{ color:var(--ambar); font-weight:600; }}
/* Pantalla angosta: cada fila pasa a ser una tarjeta con "COLUMNA  valor" en renglones. Se mide el
   ANCHO DE LA TABLA (container query sobre su envoltura), no el de la ventana: la misma ventana de
   900 px da ~500 px con la barra lateral abierta y ~800 sin ella. Una tabla ancha (5 o más
   columnas, como el presupuesto de tiempos) se apila por debajo de 680 px; una de pocas columnas
   (dónde abaratar) solo por debajo de 420 px. */
.tabla-env {{ container-type:inline-size; width:100%; }}
@container (max-width:680px) {{
  .tabla-env.ancha .tabla-texto thead {{ display:none; }}
  .tabla-env.ancha .tabla-texto, .tabla-env.ancha .tabla-texto tbody,
  .tabla-env.ancha .tabla-texto tr, .tabla-env.ancha .tabla-texto td {{ display:block; width:100%; }}
  .tabla-env.ancha .tabla-texto tr {{ border-top:1px solid var(--borde); padding:4px 0; }}
  .tabla-env.ancha .tabla-texto tr:first-child {{ border-top:none; }}
  .tabla-env.ancha .tabla-texto td {{ border-top:none; padding:2px 10px; text-align:left; white-space:normal;
    display:grid; grid-template-columns:7.5rem 1fr; gap:10px; }}
  .tabla-env.ancha .tabla-texto td::before {{ content:attr(data-col); color:var(--tenue); font-size:0.68rem;
    text-transform:uppercase; letter-spacing:.05em; padding-top:2px; font-family:inherit; font-weight:600; }}
  .tabla-env.ancha .tabla-texto td:first-child {{ font-weight:600; }}
  .tabla-env.ancha .tabla-texto td {{ border:none; }}
  /* Las cifras y los estados cortos van en UNA fila (rótulo arriba, valor abajo), no uno por renglón:
     la tarjeta queda de 3-4 renglones en vez de 7. */
  .tabla-env.ancha .tabla-texto td.num, .tabla-env.ancha .tabla-texto td.corto {{
    display:inline-block; width:auto; min-width:5.5rem; padding:4px 10px; }}
  .tabla-env.ancha .tabla-texto td.num::before, .tabla-env.ancha .tabla-texto td.corto::before {{ display:block; }}
}}
@container (max-width:420px) {{
  .tabla-env .tabla-texto thead {{ display:none; }}
  .tabla-env .tabla-texto, .tabla-env .tabla-texto tbody, .tabla-env .tabla-texto tr,
  .tabla-env .tabla-texto td {{ display:block; width:100%; }}
  .tabla-env .tabla-texto tr {{ border-top:1px solid var(--borde); padding:4px 0; }}
  .tabla-env .tabla-texto tr:first-child {{ border-top:none; }}
  .tabla-env .tabla-texto td {{ border:none; padding:2px 10px; text-align:left; white-space:normal;
    display:grid; grid-template-columns:6.5rem 1fr; gap:10px; }}
  .tabla-env .tabla-texto td::before {{ content:attr(data-col); color:var(--tenue); font-size:0.68rem;
    text-transform:uppercase; letter-spacing:.05em; padding-top:2px; font-weight:600; }}
}}
[class*="st-key-paro"] button {{ border-color:rgba(229,83,75,.7); color:#ff8a80; }}
[class*="st-key-paro"] button:hover:not(:disabled) {{ background:var(--rojo); color:#fff; border-color:var(--rojo); }}
[data-testid="stExpander"] details {{ border-color:var(--borde); border-radius:var(--r); }}
[data-testid="stDataFrame"] {{ border:1px solid var(--borde); border-radius:var(--r-chico); }}
[data-testid="stChatMessage"] {{ background:var(--panel); border:1px solid var(--borde); border-radius:var(--r); }}
</style>
"""


def aplicar() -> None:
    """Inyecta la hoja de estilo (va en cada ejecución: Streamlit rearma la página)."""
    st.html(CSS)


def pintar(contenido: str) -> None:
    """Muestra un pedazo de HTML hecho con las funciones de este módulo."""
    st.markdown(contenido, unsafe_allow_html=True)


def esc(texto) -> str:
    return _html.escape(str(texto))


# ---------------------------------------------------------------------------
# piezas de HTML
# ---------------------------------------------------------------------------


def html_seccion(titulo: str, nota: str = "", *, numero: int | str | None = None, primera: bool = False) -> str:
    num = f'<span class="num">{numero}</span>' if numero is not None else ""
    nota = f'<span class="sec-nota">{nota}</span>' if nota else ""
    return f'<div class="sec{" primera" if primera else ""}">{num}<h3>{titulo}</h3>{nota}</div>'


def seccion(titulo: str, nota: str = "", **kw) -> None:
    """Título de una sección con su nota en gris al lado (una sola forma en todo el tablero)."""
    pintar(html_seccion(titulo, nota, **kw))


def html_nota(texto: str) -> str:
    return f'<div class="nota">{texto}</div>'


def nota(texto: str) -> None:
    pintar(html_nota(texto))


def subgrupo(titulo: str, nota: str = "") -> None:
    """Rótulo chico de un grupo de botones dentro de un panel."""
    pintar(f'<div class="subgrupo"><b>{titulo}</b>{f" <span>· {nota}</span>" if nota else ""}</div>')


def html_chip(texto: str, tono: str = "", *, lleno: bool = True) -> str:
    """Chip redondo en letra mono. Sin tono: gris con borde."""
    clase = "chip" + (f" {'lleno' if lleno else 'borde'} {tono}" if tono else "")
    return f'<span class="{clase}">{texto}</span>'


def html_aviso(texto: str, tono: str = "ambar") -> str:
    return f'<div class="aviso {tono}">{texto}</div>'


def aviso(texto: str, tono: str = "ambar") -> None:
    pintar(html_aviso(texto, tono))


def html_aviso_grande(icono: str, titulo: str, texto: str, clase: str) -> str:
    """clase: 'demo' (ámbar lleno: no es en vivo / emulado) u 'offline' (rojo: sin internet)."""
    return (f'<div class="aviso-grande {clase}"><span class="ico">{icono}</span><div>'
            f'<b class="titulo">{titulo}</b>{texto}</div></div>')


def html_kpis(items: list[tuple[str, str, str, str]]) -> str:
    """Indicadores grandes: (etiqueta, valor, detalle en palabras simples, color)."""
    partes = []
    for etiqueta, valor, detalle, color in items:
        det = f'<div class="k-det">{detalle}</div>' if detalle else ""
        partes.append(f'<div class="kpi" style="--c:{color}"><div class="k-et">{etiqueta}</div>'
                      f'<div class="k-val">{valor}</div>{det}</div>')
    return f'<div class="kpis">{"".join(partes)}</div>'


def kpis(items: list[tuple[str, str, str, str]]) -> None:
    pintar(html_kpis(items))


def html_tarjeta(titulo: str, estado: str, color: str, detalle: str) -> str:
    return (f'<div class="tarjeta" style="--c:{color}"><div class="t-titulo"><i></i>{titulo}</div>'
            f'<div class="t-estado">{estado}</div><div class="t-detalle">{detalle}</div></div>')


def tarjetas(lista: list[str]) -> None:
    pintar(f'<div class="tarjetas">{"".join(t for t in lista if t)}</div>')


def html_leds(pares: list[tuple[str, bool, bool]], rotulo: str = "Sensores") -> str:
    """(nombre, encendido, es_alarma): un LED por sensor, como en el tablero de una máquina."""
    items = [f'<span class="rot">{rotulo}</span>'] if rotulo else []
    for nombre, encendido, alarma in pares:
        clase = ("led on" + (" alarma" if alarma else "")) if encendido else "led"
        items.append(f'<span class="{clase}"><i></i>{nombre}</span>')
    return f'<div class="leds">{"".join(items)}</div>'


def html_frases(frases: list[tuple[str, str, str, str]], vacio: str = "Todavía no pasó nada.") -> str:
    """(hora, tono, ícono, texto) → lista de frases con la hora y un borde del color del tono."""
    if not frases:
        return html_nota(vacio)
    filas = "".join(f'<div class="frase" style="--c:{TONOS.get(tono, BORDE)}"><span class="hora">{h}</span>'
                    f'<span class="ico">{i}</span><span>{t}</span></div>' for h, tono, i, t in frases)
    return f'<div class="frases">{filas}</div>'


def html_leyenda(items: list[tuple[str, str, str]]) -> str:
    """(símbolo, color, texto)."""
    return '<div class="leyenda">' + "".join(
        f'<span><b style="color:{c}">{s}</b>{t}</span>' for s, c, t in items) + "</div>"


# ---------------------------------------------------------------------------
# gráficas: un tema común de Plotly
# ---------------------------------------------------------------------------

pio.templates["monedas"] = go.layout.Template(layout=go.Layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Space Grotesk, system-ui, sans-serif", color="#c9d1d9", size=13),
    colorway=[AMBAR, VERDE, AZUL, MORADO, ROJO, GRIS],
    # Formato colombiano en ejes y tooltips: coma decimal y PUNTO de miles ($6.000, no $6000).
    # `separators` es "<decimal><miles>"; `separatethousands` pone el punto también en cifras de 4
    # dígitos (Plotly solo lo pone desde 5 dígitos). Revisión visual 2026-09-29.
    separators=",.",
    xaxis=dict(gridcolor="#21262d", zeroline=False, linecolor=BORDE, tickfont=dict(color=TENUE),
               separatethousands=True),
    yaxis=dict(gridcolor="#21262d", zeroline=False, linecolor=BORDE, tickfont=dict(color=TENUE),
               separatethousands=True),
    hoverlabel=dict(bgcolor=PANEL, bordercolor=BORDE, font=dict(family="IBM Plex Mono, monospace", color=TEXTO)),
    margin=dict(l=10, r=10, t=10, b=10),
    showlegend=False,
))


def figura(alto: int = 300) -> go.Figure:
    """Figura vacía con el tema del tablero."""
    fig = go.Figure()
    fig.update_layout(template="monedas", height=alto)
    return fig


def figura_vacia(alto: int, texto: str) -> go.Figure:
    fig = figura(alto)
    fig.add_annotation(text=texto, showarrow=False, font=dict(color=GRIS))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def mostrar(fig: go.Figure, key: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)


def tabla(df, **kw) -> None:
    """Tabla con el mismo aspecto en todas partes (sin índice, ancho completo)."""
    st.dataframe(df, hide_index=True, width="stretch", **kw)


def html_tabla(filas: list[dict], clases: dict[str, str] | None = None) -> str:
    """Tabla de TEXTO en HTML: a diferencia de `tabla` (st.dataframe, que corta cada celda en una
    línea y pide desplazamiento horizontal), aquí el texto largo pasa a otra línea dentro de la celda.
    `clases`: columna -> "num" (cifra, a la derecha), "corto" (no se parte) o una función
    valor -> clase ("ok"/"no" para colorear un estado)."""
    if not filas:
        return ""
    clases = clases or {}
    columnas = list(filas[0])
    cab = "".join(f"<th>{esc(c)}</th>" for c in columnas)

    def celda(col, valor):
        clase = clases.get(col, "")
        clase = clase(valor) if callable(clase) else clase
        # data-col: el nombre de la columna, que el CSS muestra al lado del valor cuando la tabla
        # no cabe y pasa a filas apiladas (sin encabezado).
        return (f'<td data-col="{esc(col)}"' + (f' class="{clase}"' if clase else "") + f">{esc(valor)}</td>")

    cuerpo = "".join("<tr>" + "".join(celda(c, f[c]) for c in columnas) + "</tr>" for f in filas)
    ancha = " ancha" if len(columnas) >= 5 else ""
    return (f'<div class="tabla-env{ancha}"><table class="tabla-texto"><thead><tr>{cab}</tr></thead>'
            f"<tbody>{cuerpo}</tbody></table></div>")
