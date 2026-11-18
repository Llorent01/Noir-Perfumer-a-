from datetime import date, datetime
from flask_login import UserMixin
from app.database import db


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    contrasena = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.Enum("cliente", "admin"), nullable=False, default="cliente")
    estado = db.Column(db.SmallInteger, nullable=False, default=1)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.now)


class Perfume(db.Model):
    __tablename__ = "perfumes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    marca = db.Column(db.String(80), nullable=False)
    genero = db.Column(db.String(20), nullable=False)
    familia = db.Column(db.String(80), nullable=False)
    familia_tag = db.Column(db.String(40), nullable=False)
    notas = db.Column(db.Text)
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(255))
    mas_vendido = db.Column(db.SmallInteger, nullable=False, default=0)
    disponible = db.Column(db.SmallInteger, nullable=False, default=1)

    tamanos = db.relationship("Tamano", backref="perfume", cascade="all, delete-orphan")


class Tamano(db.Model):
    __tablename__ = "tamanos"

    id = db.Column(db.Integer, primary_key=True)
    perfume_id = db.Column(db.Integer, db.ForeignKey("perfumes.id", ondelete="CASCADE"), nullable=False)
    ml = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Integer, nullable=False)


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))
    cliente_nombre = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.now)
    total = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="registrado")

    detalles = db.relationship("DetallePedido", backref="pedido", cascade="all, delete-orphan")
    abonos = db.relationship("Abono", backref="pedido", cascade="all, delete-orphan", order_by="Abono.fecha")

    @property
    def detalle(self):
        return self.detalles[0] if self.detalles else None

    @property
    def abonado(self):
        return sum(a.monto for a in self.abonos)

    @property
    def debe(self):
        return self.total - self.abonado


class DetallePedido(db.Model):
    __tablename__ = "detalle_pedido"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    perfume_id = db.Column(db.Integer, db.ForeignKey("perfumes.id"), nullable=False)
    ml = db.Column(db.Integer, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Integer, nullable=False)

    perfume = db.relationship("Perfume")


class Abono(db.Model):
    __tablename__ = "abonos"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    monto = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.now)


class Gasto(db.Model):
    __tablename__ = "gastos"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    concepto = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(40), nullable=False)
    monto = db.Column(db.Integer, nullable=False)
    nota = db.Column(db.String(255))
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))
    creado = db.Column(db.DateTime, nullable=False, default=datetime.now)

    usuario = db.relationship("Usuario")
