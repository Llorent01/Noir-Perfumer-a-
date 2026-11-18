from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from app.seguridad import token_csrf, token_valido
from app.auth import admin_requerido, hash_clave
from app.database import db
from app.models import Usuario

usuarios = Blueprint("usuarios", __name__, url_prefix="/admin/usuarios")


@usuarios.route("/")
@admin_requerido
def lista():
    buscar = request.args.get("buscar", "").strip()
    texto = "%" + buscar + "%"

    cuentas = Usuario.query.filter(
        db.or_(Usuario.nombre.like(texto), Usuario.correo.like(texto))
    ).order_by(Usuario.id).all()

    todos = Usuario.query.all()
    datos = {
        "total": len(todos),
        "admins": len([u for u in todos if u.rol == "admin"]),
        "clientes": len([u for u in todos if u.rol == "cliente"]),
        "inactivos": len([u for u in todos if u.estado == 0])
    }

    mensajes = {
        "guardado": ("Usuario guardado.", "ok"),
        "eliminado": ("Usuario eliminado. Sus ventas se conservan.", "ok"),
        "propio": ("No puedes eliminar tu propia cuenta.", "error"),
        "error": ("No se pudo completar la acción.", "error")
    }
    mensaje, tipo = mensajes.get(request.args.get("msg"), ("", "ok"))

    return render_template("admin_usuarios.html", cuentas=cuentas, buscar=buscar,
                           datos=datos, mensaje=mensaje, tipo=tipo, token=token_csrf())


@usuarios.route("/nuevo", methods=["GET", "POST"], defaults={"id": 0})
@usuarios.route("/<int:id>/editar", methods=["GET", "POST"])
@admin_requerido
def formulario(id):
    usuario = None
    if id > 0:
        usuario = db.session.get(Usuario, id)
        if usuario is None:
            abort(404)

    es_propio = usuario is not None and usuario.id == current_user.id

    d = {"nombre": "", "correo": "", "rol": "cliente", "estado": 1}
    if usuario:
        d = {"nombre": usuario.nombre, "correo": usuario.correo, "rol": usuario.rol, "estado": usuario.estado}

    error = ""

    if request.method == "POST":
        if not token_valido():
            return redirect(url_for("usuarios.lista", msg="error"))

        d["nombre"] = request.form.get("nombre", "").strip()
        d["correo"] = request.form.get("correo", "").strip().lower()
        d["rol"] = request.form.get("rol", "")
        d["estado"] = 1 if request.form.get("estado") else 0
        clave = request.form.get("contrasena", "")

        # Un administrador no puede quitarse su rol ni desactivarse
        if es_propio:
            d["rol"] = "admin"
            d["estado"] = 1

        repetido = Usuario.query.filter_by(correo=d["correo"]).first()

        if d["nombre"] == "" or d["correo"] == "":
            error = "Completa nombre y correo."
        elif "@" not in d["correo"] or "." not in d["correo"]:
            error = "El correo no es válido."
        elif d["rol"] not in ["cliente", "admin"]:
            error = "Elige un rol válido."
        elif repetido and (usuario is None or repetido.id != usuario.id):
            error = "Ya existe una cuenta con ese correo."
        elif usuario is None and len(clave) < 6:
            error = "La contraseña debe tener mínimo 6 caracteres."
        elif clave != "" and len(clave) < 6:
            error = "La nueva contraseña debe tener mínimo 6 caracteres."

        if error == "":
            try:
                if usuario is None:
                    usuario = Usuario()
                    db.session.add(usuario)
                usuario.nombre = d["nombre"]
                usuario.correo = d["correo"]
                usuario.rol = d["rol"]
                usuario.estado = d["estado"]
                if clave != "":
                    usuario.contrasena = hash_clave(clave)
                db.session.commit()
                return redirect(url_for("usuarios.lista", msg="guardado"))
            except IntegrityError:
                db.session.rollback()
                error = "No se pudo guardar el usuario. Revisa los datos e intenta de nuevo."

    return render_template("admin_usuario_form.html", d=d, id=id, error=error,
                           es_propio=es_propio, token=token_csrf())


@usuarios.route("/<int:id>/eliminar", methods=["POST"])
@admin_requerido
def eliminar(id):
    if not token_valido():
        return redirect(url_for("usuarios.lista", msg="error"))

    if id == current_user.id:
        return redirect(url_for("usuarios.lista", msg="propio"))

    usuario = db.session.get(Usuario, id)
    if usuario is None:
        return redirect(url_for("usuarios.lista", msg="error"))

    try:
        db.session.delete(usuario)
        db.session.commit()
        return redirect(url_for("usuarios.lista", msg="eliminado"))
    except IntegrityError:
        db.session.rollback()
        return redirect(url_for("usuarios.lista", msg="error"))
