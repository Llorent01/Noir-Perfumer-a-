from datetime import date, timedelta
from conftest import TOKEN, crear_gasto
from app.database import db
from app.models import Gasto


def gasto(**cambios):
    datos = {"token": TOKEN, "fecha": date.today().isoformat(), "concepto": "Frascos de vidrio",
             "categoria": "Envases y empaques", "monto": "35000", "nota": "Pedido a proveedor"}
    datos.update(cambios)
    return datos


def test_registrar_gasto(admin_cliente, admin):
    r = admin_cliente.post("/admin/gastos/nuevo", data=gasto())
    assert "msg=guardado" in r.headers["Location"]
    g = Gasto.query.one()
    assert (g.monto, g.concepto, g.usuario_id, g.nota) == (35000, "Frascos de vidrio", admin.id, "Pedido a proveedor")


def test_validaciones_de_gasto(admin_cliente):
    manana = (date.today() + timedelta(days=1)).isoformat()
    casos = [({"concepto": ""}, "en qué se gastó"), ({"monto": "0"}, "mayor a 0"), ({"monto": "-4"}, "mayor a 0"),
             ({"monto": "12.5"}, "mayor a 0"), ({"categoria": "Lujos"}, "categoría"), ({"fecha": manana}, "futura"),
             ({"fecha": "basura"}, "fecha no es válida"), ({"concepto": "x" * 121}, "demasiado largo")]
    for cambio, texto in casos:
        assert texto in admin_cliente.post("/admin/gastos/nuevo", data=gasto(**cambio)).get_data(as_text=True), texto
    assert Gasto.query.count() == 0


def test_editar_y_eliminar(admin_cliente):
    g = crear_gasto(10000)
    admin_cliente.post(f"/admin/gastos/{g.id}/editar", data=gasto(monto="12000", concepto="Editado", nota=""))
    db.session.refresh(g)
    assert (g.monto, g.concepto, g.nota) == (12000, "Editado", None)
    admin_cliente.post(f"/admin/gastos/{g.id}/eliminar", data={"token": TOKEN})
    assert Gasto.query.count() == 0


def test_sin_token_no_guarda_ni_borra(admin_cliente):
    admin_cliente.post("/admin/gastos/nuevo", data=gasto(token="falso"))
    g = crear_gasto(5000)
    admin_cliente.post(f"/admin/gastos/{g.id}/eliminar", data={"token": "falso"})
    assert Gasto.query.count() == 1


def test_filtros_de_la_lista(admin_cliente):
    crear_gasto(1000, concepto="Instagram ads", categoria="Publicidad", fecha=date(2026, 1, 10))
    crear_gasto(2000, concepto="Cajas", categoria="Envases y empaques", fecha=date(2026, 3, 10))
    pag = lambda q: admin_cliente.get("/admin/gastos/" + q).get_data(as_text=True)
    assert "Cajas" in pag("?buscar=caj") and "Instagram" not in pag("?buscar=caj")
    assert "Instagram" in pag("?categoria=Publicidad") and "Cajas" not in pag("?categoria=Publicidad")
    assert "Cajas" in pag("?desde=2026-02-01") and "Instagram" not in pag("?desde=2026-02-01")
    assert "Instagram" in pag("?hasta=2026-02-01") and "Cajas" not in pag("?hasta=2026-02-01")


def test_gasto_inexistente_da_404(admin_cliente):
    assert admin_cliente.get("/admin/gastos/999/editar").status_code == 404
