from conftest import TOKEN, crear_usuario, crear_venta, iniciar_sesion
from app.database import db
from app.models import Usuario, Pedido


def nuevo(**cambios):
    datos = {"nombre": "Luis", "correo": "luis@x.co", "rol": "cliente", "contrasena": "abcdef", "estado": "1", "token": TOKEN}
    datos.update(cambios)
    return datos


def test_lista_y_busqueda(admin_cliente, cliente_normal=None):
    crear_usuario("Zoe Perez", "zoe@x.co")
    r = admin_cliente.get("/admin/usuarios/?buscar=zoe")
    texto = r.get_data(as_text=True)
    assert "zoe@x.co" in texto and "admin@noir.co" not in texto


def test_crear_usuario_admin(admin_cliente):
    r = admin_cliente.post("/admin/usuarios/nuevo", data=nuevo(rol="admin"))
    assert r.status_code == 302
    assert Usuario.query.filter_by(correo="luis@x.co").first().rol == "admin"


def test_crear_validaciones(admin_cliente):
    casos = [({"correo": "malo"}, "no es válido"), ({"contrasena": "123"}, "mínimo 6"),
             ({"correo": "admin@noir.co"}, "Ya existe"), ({"rol": "root"}, "rol válido"), ({"nombre": ""}, "Completa")]
    for cambio, texto in casos:
        r = admin_cliente.post("/admin/usuarios/nuevo", data=nuevo(**cambio))
        assert texto in r.get_data(as_text=True), texto


def test_editar_conserva_clave_si_va_vacia(admin_cliente):
    otro = crear_usuario("Otro", "otro@x.co")
    antes = otro.contrasena
    admin_cliente.post(f"/admin/usuarios/{otro.id}/editar", data=nuevo(nombre="Otro editado", correo="otro@x.co", contrasena="", estado="1"))
    db.session.refresh(otro)
    assert otro.nombre == "Otro editado" and otro.contrasena == antes


def test_desactivar_impide_entrar(app, admin_cliente):
    otro = crear_usuario("Otro", "otro@x.co")
    admin_cliente.post(f"/admin/usuarios/{otro.id}/editar", data=nuevo(correo="otro@x.co", contrasena="", estado=""))
    entrada = iniciar_sesion(app.test_client(), "otro@x.co")
    assert entrada.status_code == 200


def test_admin_no_puede_quitarse_rol_ni_desactivarse(admin_cliente, admin):
    admin_cliente.post(f"/admin/usuarios/{admin.id}/editar",
                       data=nuevo(nombre="Admin Uno", correo="admin@noir.co", rol="cliente", estado="", contrasena=""))
    db.session.refresh(admin)
    assert admin.rol == "admin" and admin.estado == 1


def test_admin_no_puede_eliminarse(admin_cliente, admin):
    r = admin_cliente.post(f"/admin/usuarios/{admin.id}/eliminar", data={"token": TOKEN})
    assert "msg=propio" in r.headers["Location"]
    assert db.session.get(Usuario, admin.id) is not None


def test_eliminar_conserva_sus_ventas(admin_cliente, perfume):
    cli = crear_usuario("Cli", "cli@x.co")
    venta = crear_venta(perfume)
    venta.usuario_id = cli.id
    db.session.commit()
    admin_cliente.post(f"/admin/usuarios/{cli.id}/eliminar", data={"token": TOKEN})
    assert db.session.get(Usuario, cli.id) is None
    db.session.refresh(venta)
    assert db.session.get(Pedido, venta.id) is not None and venta.usuario_id is None


def test_eliminar_sin_token_no_borra(admin_cliente):
    otro = crear_usuario("Otro", "otro@x.co")
    admin_cliente.post(f"/admin/usuarios/{otro.id}/eliminar", data={"token": "falso"})
    assert db.session.get(Usuario, otro.id) is not None
