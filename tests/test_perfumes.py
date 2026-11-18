import io
import os
from conftest import TOKEN, crear_venta
from app.database import db
from app.models import Perfume

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def datos(**cambios):
    base = {"token": TOKEN, "nombre": "Nuevo", "marca": "Marca", "genero": "Hombre", "familia": "Fam",
            "familia_tag": "Tag", "precio5": "25000", "precio10": "45000", "disponible": "1",
            "imagen": (io.BytesIO(PNG), "foto.png")}
    base.update(cambios)
    return base


def enviar(c, url, **cambios):
    return c.post(url, data=datos(**cambios), content_type="multipart/form-data")


def test_lista_busqueda(admin_cliente, perfume, perfume2):
    texto = admin_cliente.get("/admin/perfumes/?buscar=afn").get_data(as_text=True)
    assert "9PM" in texto and "Hawas" not in texto


def test_crear_perfume_con_imagen_y_precios(app, admin_cliente):
    r = enviar(admin_cliente, "/admin/perfume/nuevo", precio100="300000", precio15="60000")
    assert r.status_code == 302
    p = Perfume.query.filter_by(nombre="Nuevo").first()
    assert {t.ml: t.precio for t in p.tamanos} == {5: 25000, 10: 45000, 15: 60000, 100: 300000}
    assert p.imagen.startswith("img/Perfume 100ml/") and os.path.exists(os.path.join(app.static_folder, p.imagen))


def test_validaciones_de_perfume(admin_cliente):
    casos = [({"precio5": "abc"}, "obligatorios"), ({"precio10": ""}, "obligatorios"), ({"nombre": ""}, "Completa"),
             ({"genero": "Otro"}, "género"), ({"precio100": "-5"}, "opcionales"),
             ({"imagen": (io.BytesIO(b"no soy imagen"), "x.png")}, "JPG, PNG o WEBP")]
    for cambio, texto in casos:
        assert texto in enviar(admin_cliente, "/admin/perfume/nuevo", **cambio).get_data(as_text=True), texto
    assert Perfume.query.count() == 0


def test_imagen_obligatoria_al_crear_pero_no_al_editar(admin_cliente, perfume):
    assert "imagen" in enviar(admin_cliente, "/admin/perfume/nuevo", imagen=(io.BytesIO(b""), "")).get_data(as_text=True).lower()
    r = enviar(admin_cliente, f"/admin/perfume/{perfume.id}/editar", nombre="9PM Editado", imagen=(io.BytesIO(b""), ""))
    assert r.status_code == 302
    db.session.refresh(perfume)
    assert perfume.nombre == "9PM Editado" and perfume.imagen == "img/a.jpg"


def test_editar_quita_presentacion_vacia(admin_cliente, perfume):
    enviar(admin_cliente, f"/admin/perfume/{perfume.id}/editar", precio100="", imagen=(io.BytesIO(b""), ""))
    db.session.refresh(perfume)
    assert sorted(t.ml for t in perfume.tamanos) == [5, 10]


def test_sin_token_no_guarda(admin_cliente):
    enviar(admin_cliente, "/admin/perfume/nuevo", token="falso")
    assert Perfume.query.count() == 0


def test_eliminar_perfume(admin_cliente, perfume):
    r = admin_cliente.post(f"/admin/perfume/{perfume.id}/eliminar", data={"token": TOKEN})
    assert "msg=eliminado" in r.headers["Location"] and Perfume.query.count() == 0


def test_no_elimina_perfume_con_ventas(admin_cliente, perfume):
    crear_venta(perfume)
    r = admin_cliente.post(f"/admin/perfume/{perfume.id}/eliminar", data={"token": TOKEN})
    assert "conpedidos" in r.headers["Location"] and Perfume.query.count() == 1


def test_perfume_inexistente_da_404(admin_cliente):
    assert admin_cliente.get("/admin/perfume/999/editar").status_code == 404
