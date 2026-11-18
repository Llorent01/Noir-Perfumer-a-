import re
import bcrypt
from conftest import TOKEN, CLAVE, crear_usuario, iniciar_sesion, con_token
from app.models import Usuario


def test_login_correcto_lleva_a_cuenta(app, cliente, admin):
    r = iniciar_sesion(cliente, "admin@noir.co")
    assert r.status_code == 302 and r.headers["Location"].endswith("/cuenta")
    assert cliente.get("/cuenta").status_code == 200


def test_login_con_hash_de_php_2y(app, cliente):
    # Los usuarios creados con PHP guardan el hash con $2y$; deben poder entrar
    hash_php = bcrypt.hashpw(CLAVE.encode(), bcrypt.gensalt()).decode().replace("$2b$", "$2y$", 1)
    from app.database import db
    db.session.add(Usuario(nombre="Php", correo="php@noir.co", contrasena=hash_php, rol="cliente"))
    db.session.commit()
    assert iniciar_sesion(cliente, "php@noir.co").status_code == 302


def test_login_clave_incorrecta(app, cliente, admin):
    r = cliente.post("/login", data={"correo": "admin@noir.co", "contrasena": "mala", "token": TOKEN})
    assert r.status_code == 200 and "incorrectos" in r.get_data(as_text=True)


def test_login_sin_token_se_rechaza(app, cliente, admin):
    r = cliente.post("/login", data={"correo": "admin@noir.co", "contrasena": CLAVE})
    assert r.status_code == 200 and "expiró" in r.get_data(as_text=True)


def test_cuenta_inactiva_no_entra(app, cliente):
    crear_usuario("Inactivo", "off@noir.co", estado=0)
    r = cliente.post("/login", data={"correo": "off@noir.co", "contrasena": CLAVE, "token": TOKEN})
    assert "incorrectos" in r.get_data(as_text=True)


def test_registro_crea_cliente(app, cliente):
    datos = {"nombre": "Ana", "correo": "ANA@x.co", "contrasena": "123456", "confirmar": "123456", "token": TOKEN}
    r = cliente.post("/registro", data=datos)
    assert r.status_code == 302
    usuario = Usuario.query.filter_by(correo="ana@x.co").first()
    assert usuario.rol == "cliente" and usuario.contrasena.startswith("$2")


def test_registro_validaciones(app, cliente, admin):
    base = {"nombre": "Ana", "correo": "ana@x.co", "contrasena": "123456", "confirmar": "123456", "token": TOKEN}
    casos = [({"contrasena": "123", "confirmar": "123"}, "mínimo 6"),
             ({"confirmar": "999999"}, "no coinciden"),
             ({"correo": "malcorreo"}, "no es válido"),
             ({"correo": "admin@noir.co"}, "Ya existe"),
             ({"nombre": ""}, "Completa")]
    for cambio, texto in casos:
        r = cliente.post("/registro", data=dict(base, **cambio))
        assert texto in r.get_data(as_text=True), texto
    assert Usuario.query.count() == 1


def test_logout_solo_por_post_con_token(app, admin_cliente):
    assert admin_cliente.get("/logout").status_code == 405
    admin_cliente.post("/logout", data={"token": "falso"})
    assert admin_cliente.get("/cuenta").status_code == 200  # token malo: sigue dentro
    admin_cliente.post("/logout", data={"token": TOKEN})
    assert admin_cliente.get("/cuenta").status_code == 302


def test_cuenta_requiere_login(app, cliente):
    r = cliente.get("/cuenta")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_panel_admin_prohibido_para_cliente(app, cliente_normal):
    for ruta in ["/admin/", "/admin/ventas/", "/admin/gastos/", "/admin/reportes/", "/admin/usuarios/",
                 "/admin/historial", "/admin/perfumes/", "/admin/api/ventas"]:
        assert cliente_normal.get(ruta).status_code == 403, ruta


def test_panel_admin_pide_login(app, cliente):
    for ruta in ["/admin/", "/admin/ventas/", "/admin/gastos/", "/admin/reportes/exportar.csv"]:
        r = cliente.get(ruta)
        assert r.status_code == 302 and "/login" in r.headers["Location"], ruta
