from datetime import date, datetime, timedelta
from conftest import crear_venta, crear_gasto
from app import finanzas
from app.utilidades import pesos


def escenario(perfume, perfume2):
    # Venta A: 50.000, abonó 30.000 · Venta B: 25.000 pagada completa
    crear_venta(perfume, cliente="Ana", total=50000, abonos=[20000, 10000])
    crear_venta(perfume2, cliente="Luis", total=25000, abonos=[25000])
    crear_gasto(15000, concepto="Frascos", categoria="Envases y empaques")
    crear_gasto(5000, concepto="Publicidad IG", categoria="Publicidad")


def test_resumen_con_cifras_exactas(app, perfume, perfume2):
    escenario(perfume, perfume2)
    r = finanzas.resumen()
    assert r["vendido"] == 75000
    assert r["cobrado"] == 55000
    assert r["por_cobrar"] == 20000
    assert r["gastos"] == 20000
    assert r["en_mano"] == 35000       # cobrado - gastos
    assert r["ganancia"] == 55000      # vendido - gastos
    assert r["ventas"] == 2
    assert r["cobrado_mes"] == 55000 and r["gastos_mes"] == 20000


def test_resumen_sin_datos_es_cero(app):
    r = finanzas.resumen()
    assert all(valor == 0 for valor in r.values())


def test_en_mano_puede_ser_negativo(app, perfume):
    crear_venta(perfume, total=10000, abonos=[10000])
    crear_gasto(15000)
    assert finanzas.resumen()["en_mano"] == -5000
    assert pesos(-5000) == "-$5.000" and pesos(1234567) == "$1.234.567" and pesos(None) == "$0"


def test_dashboard_muestra_las_cifras(admin_cliente, perfume, perfume2):
    escenario(perfume, perfume2)
    texto = admin_cliente.get("/admin/").get_data(as_text=True)
    for esperado in ["$35.000", "$55.000", "$20.000", "$75.000", "Dinero en mano", "Mayores deudas", "Ana"]:
        assert esperado in texto, esperado


def test_dashboard_vacio_no_falla(admin_cliente):
    r = admin_cliente.get("/admin/")
    texto = r.get_data(as_text=True)
    assert r.status_code == 200 and "Nadie debe dinero" in texto and "Aún no hay gastos" in texto


def test_movimientos_y_totales(app, perfume, perfume2):
    escenario(perfume, perfume2)
    todos = finanzas.movimientos()
    assert len(todos) == 5  # 3 abonos + 2 gastos
    t = finanzas.totales_movimientos(todos)
    assert (t["ingresos"], t["gastos"], t["neto"]) == (55000, 20000, 35000)
    assert len(finanzas.movimientos(tipo="ingresos")) == 3
    assert len(finanzas.movimientos(tipo="gastos")) == 2
    assert [m["concepto"] for m in finanzas.movimientos(buscar="publicidad")] == ["Publicidad IG"]
    assert len(finanzas.movimientos(buscar="luis")) == 1


def test_movimientos_filtrados_por_fecha(app, perfume):
    viejo = datetime(2026, 1, 10, 9, 0)
    crear_venta(perfume, total=10000, abonos=[10000], fecha=viejo)
    crear_gasto(2000, fecha=date(2026, 1, 10))
    crear_gasto(3000, fecha=date(2026, 3, 1))
    dentro = finanzas.movimientos(desde=date(2026, 1, 10), hasta=date(2026, 1, 10))
    assert finanzas.totales_movimientos(dentro) == {"ingresos": 10000, "gastos": 2000, "neto": 8000}
    assert finanzas.movimientos(desde=date(2026, 2, 1))[0]["monto"] == 3000


def test_movimientos_orden_del_mas_reciente_al_mas_antiguo(app):
    crear_gasto(1, fecha=date(2026, 1, 1))
    crear_gasto(2, fecha=date(2026, 6, 1))
    crear_gasto(3, fecha=date(2026, 3, 1))
    assert [m["monto"] for m in finanzas.movimientos()] == [2, 3, 1]


def test_gastos_por_categoria(app):
    crear_gasto(30000, categoria="Publicidad")
    crear_gasto(10000, categoria="Otros")
    filas = finanzas.gastos_por_categoria()
    assert [(f["categoria"], f["monto"], f["porcentaje"]) for f in filas] == [("Publicidad", 30000, 75), ("Otros", 10000, 25)]


def test_mayores_deudas_ordenadas_y_sin_pagadas(app, perfume):
    crear_venta(perfume, cliente="Poca", total=10000, abonos=[9000])
    crear_venta(perfume, cliente="Mucha", total=90000, abonos=[])
    crear_venta(perfume, cliente="Pagada", total=5000, abonos=[5000])
    deudas = finanzas.mayores_deudas()
    assert [(d["pedido"].cliente_nombre, d["debe"]) for d in deudas] == [("Mucha", 90000), ("Poca", 1000)]


def test_grafico_mensual(app, perfume):
    crear_venta(perfume, total=40000, abonos=[40000])
    crear_gasto(10000)
    g = finanzas.grafico_mensual(6)
    assert len(g["barras"]) == 6 and g["tiene_datos"]
    ultimo = g["barras"][-1]
    assert ultimo["ingresos"] == 40000 and ultimo["gastos"] == 10000
    assert ultimo["h1"] > ultimo["h2"] > 0
    assert all(b["ingresos"] == 0 for b in g["barras"][:-1])


def test_grafico_mes_anterior(app, perfume):
    hace_un_mes = datetime.now().replace(day=1) - timedelta(days=5)
    crear_venta(perfume, total=1000, abonos=[1000], fecha=hace_un_mes)
    g = finanzas.grafico_mensual(6)
    assert g["barras"][-2]["ingresos"] == 1000 and g["barras"][-1]["ingresos"] == 0


def test_ayudas_del_grafico():
    assert finanzas._maximo_redondo(0) == 1
    assert [finanzas._maximo_redondo(v) for v in (7, 12, 340, 4900, 120000)] == [10, 20, 500, 5000, 200000]
    assert finanzas.valor_corto(1500000) == "1,5 M" and finanzas.valor_corto(2000000) == "2 M"
    assert finanzas.valor_corto(45000) == "45 mil" and finanzas.valor_corto(800) == "800"


def test_historial_pagina_y_csv(admin_cliente, perfume, perfume2):
    escenario(perfume, perfume2)
    pagina = admin_cliente.get("/admin/historial?tipo=gastos").get_data(as_text=True)
    assert "Frascos" in pagina and "Abono de venta" not in pagina
    csv_texto = admin_cliente.get("/admin/historial.csv").get_data(as_text=True)
    assert "Total ingresos" in csv_texto and "55000" in csv_texto and "Balance" in csv_texto and "35000" in csv_texto
