from conftest import TOKEN, crear_venta
from app.database import db
from app.models import Pedido, Abono


def venta(perfume, **cambios):
    datos = {"token": TOKEN, "cliente": "Ana", "perfume_id": str(perfume.id), "ml": "5", "cantidad": "2",
             "total": "50000", "abono": "20000"}
    datos.update(cambios)
    return datos


def test_registrar_venta_con_deuda(admin_cliente, perfume):
    r = admin_cliente.post("/admin/ventas/nueva", data=venta(perfume))
    assert "msg=registrada" in r.headers["Location"]
    p = Pedido.query.one()
    assert (p.total, p.abonado, p.debe) == (50000, 20000, 30000)
    assert p.detalle.ml == 5 and p.detalle.cantidad == 2 and p.detalle.precio == 25000


def test_venta_pagada_y_sin_abono(admin_cliente, perfume):
    admin_cliente.post("/admin/ventas/nueva", data=venta(perfume, abono="50000"))
    admin_cliente.post("/admin/ventas/nueva", data=venta(perfume, cliente="Luis", abono=""))
    pagada, sin_pago = Pedido.query.order_by(Pedido.id).all()
    assert pagada.debe == 0 and sin_pago.abonado == 0 and sin_pago.debe == 50000 and len(sin_pago.abonos) == 0


def test_validaciones_de_venta(admin_cliente, perfume):
    casos = [({"cliente": ""}, "nombre del cliente"), ({"perfume_id": ""}, "Elige un perfume"),
             ({"ml": "7"}, "presentación válida"), ({"cantidad": "0"}, "cantidad"), ({"total": "0"}, "total"),
             ({"abono": "60000"}, "mayor que el total"), ({"abono": "x"}, "número entero"),
             ({"ml": "100", "total": "1"}, None)]
    for cambio, texto in casos[:-1]:
        assert texto in admin_cliente.post("/admin/ventas/nueva", data=venta(perfume, **cambio)).get_data(as_text=True), texto
    assert Pedido.query.count() == 0


def test_presentacion_inexistente_en_el_perfume(admin_cliente, perfume2):
    r = admin_cliente.post("/admin/ventas/nueva", data=venta(perfume2, ml="100"))
    assert "no tiene presentación" in r.get_data(as_text=True) and Pedido.query.count() == 0


def test_abonos_hasta_completar_pago(admin_cliente, perfume):
    p = crear_venta(perfume, total=50000, abonos=[10000])
    admin_cliente.post(f"/admin/ventas/{p.id}/abono", data={"token": TOKEN, "monto": "15000"})
    db.session.refresh(p)
    assert (p.abonado, p.debe) == (25000, 25000)
    admin_cliente.post(f"/admin/ventas/{p.id}/abono", data={"token": TOKEN, "monto": "25000"})
    db.session.refresh(p)
    assert p.debe == 0 and len(p.abonos) == 3


def test_abono_mayor_a_la_deuda_se_rechaza(admin_cliente, perfume):
    p = crear_venta(perfume, total=50000, abonos=[40000])
    r = admin_cliente.post(f"/admin/ventas/{p.id}/abono", data={"token": TOKEN, "monto": "10001"})
    assert "mayor que lo que debe" in r.get_data(as_text=True)
    for malo in ["0", "-5", "abc", ""]:
        admin_cliente.post(f"/admin/ventas/{p.id}/abono", data={"token": TOKEN, "monto": malo})
    db.session.refresh(p)
    assert p.abonado == 40000


def test_eliminar_abono_y_venta(admin_cliente, perfume):
    p = crear_venta(perfume, total=50000, abonos=[10000, 5000])
    abono = p.abonos[0]
    admin_cliente.post(f"/admin/ventas/{p.id}/abono/{abono.id}/eliminar", data={"token": TOKEN})
    db.session.refresh(p)
    assert p.abonado == 5000
    admin_cliente.post(f"/admin/ventas/{p.id}/eliminar", data={"token": TOKEN})
    assert Pedido.query.count() == 0 and Abono.query.count() == 0


def test_no_se_elimina_abono_de_otra_venta(admin_cliente, perfume):
    a = crear_venta(perfume, abonos=[1000])
    b = crear_venta(perfume, cliente="Otra", abonos=[2000])
    r = admin_cliente.post(f"/admin/ventas/{a.id}/abono/{b.abonos[0].id}/eliminar", data={"token": TOKEN})
    assert r.status_code == 404 and Abono.query.count() == 2


def test_lista_busqueda_y_filtro_de_deuda(admin_cliente, perfume):
    crear_venta(perfume, cliente="Ana", total=50000, abonos=[10000])
    crear_venta(perfume, cliente="Luis", total=50000, abonos=[50000])
    todo = admin_cliente.get("/admin/ventas/").get_data(as_text=True)
    assert "Ana" in todo and "Luis" in todo
    deuda = admin_cliente.get("/admin/ventas/?estado=deuda").get_data(as_text=True)
    assert "Ana" in deuda and "Luis" not in deuda
    assert "Luis" not in admin_cliente.get("/admin/ventas/?buscar=ana").get_data(as_text=True)


def test_sin_token_no_cambia_nada(admin_cliente, perfume):
    admin_cliente.post("/admin/ventas/nueva", data=venta(perfume, token="falso"))
    assert Pedido.query.count() == 0
