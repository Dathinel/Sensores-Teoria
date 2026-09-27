from app import db


def test_conectar_crea_las_ocho_tablas(tmp_path):
    ruta = tmp_path / "prueba.db"
    conexion = db.conectar(ruta)
    try:
        tablas = db.nombres_de_tablas(conexion)
        assert tablas == {"eventos", "elementos", "vasos", "ruta", "ordenes", "almacen_turno", "asistente", "asistente_pensando"}
    finally:
        conexion.close()


def test_conectar_es_idempotente(tmp_path):
    ruta = tmp_path / "prueba.db"
    db.conectar(ruta).close()
    # abrir de nuevo sobre el mismo archivo no debe fallar por tablas que ya existen
    conexion = db.conectar(ruta)
    conexion.close()


def test_se_puede_insertar_un_evento(tmp_path):
    ruta = tmp_path / "prueba.db"
    conexion = db.conectar(ruta)
    try:
        conexion.execute(
            "INSERT INTO eventos (ts, origen, tipo, payload) VALUES (?, ?, ?, ?)",
            ("2026-01-01T00:00:00", "linea", "paso", '{"casilla": 1}'),
        )
        conexion.commit()
        fila = conexion.execute("SELECT * FROM eventos").fetchone()
        assert fila["origen"] == "linea"
    finally:
        conexion.close()


def test_almacen_turno_sobrevive_a_reiniciar_corrida(tmp_path):
    """Lo que quedo en los tubos NO es de la corrida: el turno siguiente
    arranca con eso."""
    conexion = db.conectar(tmp_path / "prueba.db")
    try:
        assert db.leer_almacen_turno(conexion) == []
        monedas = [{"clase": "500_nueva", "valor": 500, "masa_g": 7.1}]
        db.guardar_almacen_turno(conexion, monedas)
        db.reiniciar_corrida(conexion)
        assert db.leer_almacen_turno(conexion) == monedas
    finally:
        conexion.close()
