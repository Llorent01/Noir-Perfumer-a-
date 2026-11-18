import csv
import io
from datetime import datetime
from conftest import crear_venta
from app.models import Pedido


def preparar(perfume, perfume2):
    crear_venta(perfume, cliente="Ana", ml=5, cantidad=2, total=50000, abonos=[20000], fecha=datetime(2026, 1, 10, 10, 0))
    crear_venta(perfume, cliente="Luis", ml=10, cantidad=1, total=45000, abonos=[45000], fecha=datetime(2026, 2, 15, 11, 0))
    crear_venta(perfume2, cliente="Marta", ml=5, cantidad=1, total=25000, abonos=[], fecha=datetime(2026, 2, 20, 12, 0))


def filas_csv(respuesta):
    return list(csv.reader(io.StringIO(respuesta.get_data(as_text=True).lstrip("﻿")), delimiter=";"))


def test_reporte_sin_filtros_suma_todo(admin_cliente, perfume, perfume2):
    preparar(perfume, perfume2)
    r = admin_cliente.get("/admin/reportes/")
    texto = r.get_data(as_text=True)
    assert r.status_code == 200 and "$120.000" in texto and "$55.000" in texto  # vendido y por cobrar
    assert "Ana" in texto and "Luis" in texto and "Marta" in texto


def test_filtro_por_fechas_incluye_el_dia_final(admin_cliente, perfume, perfume2):
    preparar(perfume, perfume2)
    t = admin_cliente.get("/admin/reportes/?desde=2026-02-01&hasta=2026-02-20").get_data(as_text=True)
    assert "Luis" in t and "Marta" in t and "Ana" not in t
    t = admin_cliente.get("/admin/reportes/?hasta=2026-01-10").get_data(as_text=True)
    assert "Ana" in t and "Luis" not in t


def test_filtro_por_perfume_marca_y_presentacion(admin_cliente, perfume, perfume2):
    preparar(perfume, perfume2)
    por_perfume = admin_cliente.get(f"/admin/reportes/?perfume={perfume2.id}").get_data(as_text=True)
    assert "Marta" in por_perfume and "Ana" not in por_perfume
    por_marca = admin_cliente.get("/admin/reportes/?marca=Afnan").get_data(as_text=True)
    assert "Ana" in por_marca and "Marta" not in por_marca
    por_ml = admin_cliente.get("/admin/reportes/?ml=10").get_data(as_text=True)
    assert "Luis" in por_ml and "Ana" not in por_ml
    combinado = admin_cliente.get(f"/admin/reportes/?marca=Afnan&ml=5&desde=2026-01-01").get_data(as_text=True)
    assert "Ana" in combinado and "Luis" not in combinado


def test_filtros_invalidos_se_ignoran(admin_cliente, perfume, perfume2):
    preparar(perfume, perfume2)
    r = admin_cliente.get("/admin/reportes/?desde=basura&perfume=xx&ml=9999&hasta=")
    assert r.status_code == 200 and "Ana" in r.get_data(as_text=True)


def test_agrupa_por_mes_si_el_rango_es_largo(admin_cliente, perfume, perfume2):
    preparar(perfume, perfume2)  # del 10 de enero al 20 de febrero: 41 días, se agrupa por día
    assert "Ventas por día" in admin_cliente.get("/admin/reportes/").get_data(as_text=True)
    crear_venta(perfume, cliente="Tardía", total=1000, abonos=[1000], fecha=datetime(2026, 6, 1, 9, 0))
    assert "Ventas por mes" in admin_cliente.get("/admin/reportes/").get_data(as_text=True)
    assert "Ventas por día" in admin_cliente.get("/admin/reportes/?desde=2026-02-01&hasta=2026-02-28").get_data(as_text=True)


def test_reporte_vacio(admin_cliente):
    r = admin_cliente.get("/admin/reportes/?desde=2030-01-01")
    assert r.status_code == 200 and "No hay ventas con estos filtros" in r.get_data(as_text=True)


def test_csv_respeta_los_mismos_filtros(admin_cliente, perfume, perfume2):
    preparar(perfume, perfume2)
    r = admin_cliente.get("/admin/reportes/exportar.csv?marca=Afnan")
    assert r.mimetype == "text/csv" and "attachment" in r.headers["Content-Disposition"]
    assert r.get_data().startswith(b"\xef\xbb\xbf")  # BOM para Excel
    filas = filas_csv(r)
    assert filas[0][:4] == ["Venta", "Fecha", "Cliente", "Perfume"]
    clientes = [f[2] for f in filas[1:] if f and f[2]]
    assert clientes == ["Luis", "Ana"]
    total = [f for f in filas if f and "Total" in f[6]][0]
    assert total[7:] == ["95000", "65000", "30000"]  # total, abonado, debe de las 2 ventas Afnan


def test_csv_sin_filtros_y_con_tildes(admin_cliente, perfume, perfume2):
    crear_venta(perfume, cliente="José Ñandú", total=1000, abonos=[1000])
    filas = filas_csv(admin_cliente.get("/admin/reportes/exportar.csv"))
    assert filas[1][2] == "José Ñandú"


def test_csv_evita_inyeccion_de_formulas(admin_cliente, perfume):
    crear_venta(perfume, cliente="=HYPERLINK(\"http://malo\")", total=1000, abonos=[1000])
    crear_venta(perfume, cliente="@cmd", total=1000, abonos=[1000])
    clientes = [f[2] for f in filas_csv(admin_cliente.get("/admin/reportes/exportar.csv"))[1:] if f and f[2]]
    assert all(c.startswith("'") for c in clientes)
