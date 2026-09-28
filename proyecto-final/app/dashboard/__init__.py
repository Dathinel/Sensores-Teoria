"""Dashboard de Streamlit (CLAUDE.md, sección 13), en módulos:

    inicio.py     punto de entrada (lo corre `streamlit run app/dashboard/inicio.py`)
    estilo.py     sistema de diseño: colores, CSS, tarjetas, chips, avisos, tema de Plotly
    datos.py      lo que se lee de SQLite y del supervisor; `enviar()` deja órdenes
    textos.py     nombres y frases simples de cada estado y evento
    dibujos.py    las cintas, el almacén y los vasos dibujados en HTML
    cabecera.py   título, chips de estado y avisos grandes
    controles.py  barra lateral (manejar la línea)
    pestanas/     una pestaña por módulo

Inventario de funciones (lista de verificación): docs/interfaz-dashboard.md.

El punto de entrada NO se llama app.py: Streamlit pone la carpeta del script al
principio de sys.path y un `app.py` ahí taparía al paquete `app` del proyecto.
"""
