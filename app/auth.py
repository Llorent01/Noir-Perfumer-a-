from functools import wraps
import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, abort
from sqlalchemy.exc import IntegrityError
from app.seguridad import token_valido
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from app.database import db
from app.models import Usuario

auth = Blueprint("auth", __name__)

login_manager = LoginManager()
login_manager.login_view = "auth.login"


@login_manager.user_loader
def cargar_usuario(id):
    return db.session.get(Usuario, int(id))


def admin_requerido(funcion):
    @wraps(funcion)
    @login_required
    def revisar(*args, **kwargs):
        if current_user.rol != "admin":
            abort(403)
        return funcion(*args, **kwargs)
    return revisar


def clave_correcta(clave, hash_guardado):
    # Los hashes de PHP empiezan con $2y$, bcrypt los entiende igual
    try:
        return bcrypt.checkpw(clave.encode("utf-8"), hash_guardado.encode("utf-8"))
    except ValueError:
        return False


def hash_clave(clave):
    return bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.cuenta"))

    error = ""
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")

        if not token_valido():
            error = "La sesión expiró. Recarga la página e intenta de nuevo."
        elif correo == "" or contrasena == "":
            error = "Completa todos los campos."
        else:
            usuario = Usuario.query.filter_by(correo=correo, estado=1).first()
            if usuario and clave_correcta(contrasena, usuario.contrasena):
                login_user(usuario)
                return redirect(url_for("auth.cuenta"))
            error = "Correo o contraseña incorrectos."

    return render_template("login.html", error=error, mensaje=request.args.get("registro"))


@auth.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("auth.cuenta"))

    error = ""
    nombre = ""
    correo = ""
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")
        confirmar = request.form.get("confirmar", "")

        if not token_valido():
            error = "La sesión expiró. Recarga la página e intenta de nuevo."
        elif nombre == "" or correo == "" or contrasena == "":
            error = "Completa todos los campos."
        elif "@" not in correo or "." not in correo:
            error = "El correo no es válido."
        elif len(contrasena) < 6:
            error = "La contraseña debe tener mínimo 6 caracteres."
        elif contrasena != confirmar:
            error = "Las contraseñas no coinciden."
        elif Usuario.query.filter_by(correo=correo).first():
            error = "Ya existe una cuenta con ese correo."
        else:
            hash_nuevo = bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            nuevo = Usuario(nombre=nombre, correo=correo, contrasena=hash_nuevo, rol="cliente")
            try:
                db.session.add(nuevo)
                db.session.commit()
                return redirect(url_for("auth.login", registro="ok"))
            except IntegrityError:
                db.session.rollback()
                error = "No se pudo crear la cuenta. Es posible que el correo ya esté registrado."

    return render_template("registro.html", error=error, nombre=nombre, correo=correo)


@auth.route("/cuenta")
@login_required
def cuenta():
    return render_template("cuenta.html")


@auth.route("/logout", methods=["POST"])
def logout():
    if token_valido():
        logout_user()
    return redirect(url_for("auth.login"))

