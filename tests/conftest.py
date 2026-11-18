import os
import sys

# La base de pruebas es SQLite en memoria: no toca tu MySQL.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "clave-de-pruebas"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
import pytest
from flask import g
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app import crear_app
from app.database import db
from app.models import Usuario, Perfume, Tamano, Pedido, DetallePedido, Abono, Gasto

TOKEN = "token-de-pruebas"
CLAVE = "clave123"


@event.listens_for(Engine, "connect")
def activar_llaves_foraneas(conexion, registro):
    # MySQL hace cumplir las llaves foráneas; SQLite solo si se lo pedimos
    try:
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


def hash_de(clave):
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


@pytest.fixture
def app(tmp_path):
    aplicacion = crear_app()
    aplicacion.config["TESTING"] = True
    aplicacion.static_folder = str(tmp_path)

    # En las pruebas el contexto de la app dura todo el test y Flask-Login guarda al usuario en "g".
    # Se limpia al terminar cada petición para que un cliente no herede la sesión de otro.
    @aplicacion.teardown_request
    def limpiar_usuario(error):
        g.pop("_login_user", None)

    with aplicacion.app_context():
        db.create_all()
        yield aplicacion
        db.session.remove()
        db.drop_all()


def con_token(cliente):
    with cliente.session_transaction() as sesion:
        sesion["token"] = TOKEN
    return cliente


@pytest.fixture
def cliente(app):
    return con_token(app.test_client())


def crear_usuario(nombre, correo, rol="cliente", estado=1):
    usuario = Usuario(nombre=nombre, correo=correo, contrasena=hash_de(CLAVE), rol=rol, estado=estado)
    db.session.add(usuario)
    db.session.commit()
    return usuario


def iniciar_sesion(cliente, correo):
    return cliente.post("/login", data={"correo": correo, "contrasena": CLAVE, "token": TOKEN})


@pytest.fixture
def admin(app):
    return crear_usuario("Admin Uno", "admin@noir.co", rol="admin")


@pytest.fixture
def admin_cliente(app, admin):
    c = con_token(app.test_client())
    iniciar_sesion(c, "admin@noir.co")
    return c


@pytest.fixture
def cliente_normal(app):
    crear_usuario("Cliente Uno", "cliente@noir.co")
    c = con_token(app.test_client())
    iniciar_sesion(c, "cliente@noir.co")
    return c


@pytest.fixture
def perfume(app):
    p = Perfume(nombre="9PM", marca="Afnan", genero="Hombre", familia="Oriental Especiado",
                familia_tag="Oriental", imagen="img/a.jpg", mas_vendido=1)
    p.tamanos = [Tamano(ml=5, precio=25000), Tamano(ml=10, precio=45000), Tamano(ml=100, precio=280000)]
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def perfume2(app):
    p = Perfume(nombre="Hawas Fire", marca="Rasasi", genero="Hombre", familia="Amaderado",
                familia_tag="Amaderado", imagen="img/b.jpg")
    p.tamanos = [Tamano(ml=5, precio=25000), Tamano(ml=10, precio=45000)]
    db.session.add(p)
    db.session.commit()
    return p


def crear_venta(perfume, cliente="Ana", ml=5, cantidad=1, total=25000, abonos=(), fecha=None):
    pedido = Pedido(cliente_nombre=cliente, total=total)
    if fecha:
        pedido.fecha = fecha
    pedido.detalles.append(DetallePedido(perfume_id=perfume.id, ml=ml, cantidad=cantidad, precio=25000))
    for monto in abonos:
        pedido.abonos.append(Abono(monto=monto, fecha=fecha) if fecha else Abono(monto=monto))
    db.session.add(pedido)
    db.session.commit()
    return pedido


def crear_gasto(monto, concepto="Frascos", categoria="Envases y empaques", fecha=None):
    from datetime import date
    gasto = Gasto(fecha=fecha or date.today(), concepto=concepto, categoria=categoria, monto=monto)
    db.session.add(gasto)
    db.session.commit()
    return gasto
