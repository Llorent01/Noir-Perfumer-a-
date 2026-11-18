import os
import re
from app.database import db

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def leer(nombre):
    with open(os.path.join(RAIZ, "database", nombre), encoding="utf8") as archivo:
        return archivo.read()


def tablas_del_sql(texto):
    tablas = {}
    for nombre, cuerpo in re.findall(r"CREATE TABLE IF NOT EXISTS `(\w+)` \((.*?)\) ENGINE", texto, flags=re.S):
        tablas[nombre] = cuerpo
    return tablas


def columnas(cuerpo):
    return re.findall(r"^\s+`(\w+)` ", cuerpo, flags=re.M)


def test_schema_sql_coincide_con_los_modelos(app):
    sql = tablas_del_sql(leer("schema.sql"))
    modelos = db.metadata.tables
    assert set(sql) == set(modelos), "Las tablas del schema.sql y de models.py deben ser las mismas"
    for nombre, tabla in modelos.items():
        assert columnas(sql[nombre]) == [c.name for c in tabla.columns], "Columnas distintas en " + nombre


def test_llaves_foraneas_del_schema_coinciden_con_los_modelos(app):
    sql = tablas_del_sql(leer("schema.sql"))
    for nombre, tabla in db.metadata.tables.items():
        esperadas = sorted(fk.column.table.name for fk in tabla.foreign_keys)
        escritas = sorted(re.findall(r"FOREIGN KEY \(`\w+`\) REFERENCES `(\w+)`", sql[nombre]))
        assert esperadas == escritas, "Llaves foráneas distintas en " + nombre


def test_longitudes_de_texto_coinciden(app):
    sql = tablas_del_sql(leer("schema.sql"))
    for nombre, tabla in db.metadata.tables.items():
        for columna in tabla.columns:
            if hasattr(columna.type, "length") and columna.type.length and columna.type.__class__.__name__ == "String":
                assert re.search(r"`%s` varchar\(%d\)" % (columna.name, columna.type.length), sql[nombre]), nombre + "." + columna.name


def test_migracion_crea_las_tablas_nuevas_y_no_borra_nada():
    migracion = leer("migracion.sql")
    assert "CREATE TABLE IF NOT EXISTS `abonos`" in migracion and "CREATE TABLE IF NOT EXISTS `gastos`" in migracion
    activas = [l for l in migracion.splitlines() if not l.strip().startswith("--")]
    assert not any(re.search(r"\b(DROP|TRUNCATE)\b|(?<!ON )\bDELETE\b", l, re.I) for l in activas)


def test_no_hay_credenciales_reales_en_el_proyecto():
    for archivo in ["README.md", ".env.example", "crear_admin.py"]:
        ruta = os.path.join(RAIZ, archivo)
        if os.path.exists(ruta):
            texto = open(ruta, encoding="utf8").read().lower()
            assert "noir.co" not in texto and "gmail.com" not in texto, archivo
