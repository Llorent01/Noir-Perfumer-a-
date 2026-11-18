from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.auth import admin_requerido
from app.database import db
from app.finanzas import CATEGORIAS_GASTO
from app.models import Gasto
from app.seguridad import token_csrf, token_valido
from app.utilidades import leer_fecha

gastos = Blueprint("gastos", __name__, url_prefix="/admin/gastos")


def filtrar(args):
    buscar = args.get("buscar", "").strip()
    categoria = args.get("categoria", "")
    desde = leer_fecha(args.get("desde", ""))
    hasta = leer_fecha(args.get("hasta", ""))

    consulta = Gasto.query
    if buscar:
        consulta = consulta.filter(Gasto.concepto.like("%" + buscar + "%"))
    if categoria in CATEGORIAS_GASTO:
        consulta = consulta.filter(Gasto.categoria == categoria)
    if desde:
        consulta = consulta.filter(Gasto.fecha >= desde)
    if hasta:
        consulta = consulta.filter(Gasto.fecha <= hasta)
    return consulta.order_by(Gasto.fecha.desc(), Gasto.id.desc()).all(), buscar, categoria, desde, hasta


@gastos.route("/")
@admin_requerido
def lista():
    lista_gastos, buscar, categoria, desde, hasta = filtrar(request.args)

    mensajes = {
        "guardado": ("Gasto guardado.", "ok"),
        "eliminado": ("Gasto eliminado.", "ok"),
        "error": ("No se pudo completar la acción.", "error")
    }
    mensaje, tipo = mensajes.get(request.args.get("msg"), ("", "ok"))

    return render_template("admin_gastos.html", gastos=lista_gastos, buscar=buscar, categoria=categoria,
                           desde=desde.isoformat() if desde else "", hasta=hasta.isoformat() if hasta else "",
                           categorias=CATEGORIAS_GASTO, total=sum(g.monto for g in lista_gastos),
                           mensaje=mensaje, tipo=tipo, token=token_csrf())


@gastos.route("/nuevo", methods=["GET", "POST"], defaults={"id": 0})
@gastos.route("/<int:id>/editar", methods=["GET", "POST"])
@admin_requerido
def formulario(id):
    gasto = None
    if id > 0:
        gasto = db.session.get(Gasto, id)
        if gasto is None:
            abort(404)

    d = {"fecha": date.today().isoformat(), "concepto": "", "categoria": CATEGORIAS_GASTO[0], "monto": "", "nota": ""}
    if gasto:
        d = {"fecha": gasto.fecha.isoformat(), "concepto": gasto.concepto, "categoria": gasto.categoria,
             "monto": gasto.monto, "nota": gasto.nota or ""}
    error = ""

    if request.method == "POST":
        if not token_valido():
            return redirect(url_for("gastos.lista", msg="error"))

        for campo in d:
            d[campo] = request.form.get(campo, "").strip()
        fecha = leer_fecha(d["fecha"])

        if d["concepto"] == "":
            error = "Escribe en qué se gastó el dinero."
        elif len(d["concepto"]) > 120:
            error = "El concepto es demasiado largo (máximo 120 caracteres)."
        elif d["categoria"] not in CATEGORIAS_GASTO:
            error = "Elige una categoría válida."
        elif fecha is None:
            error = "La fecha no es válida."
        elif fecha > date.today():
            error = "La fecha del gasto no puede ser futura."
        elif not (d["monto"].isdigit() and int(d["monto"]) > 0):
            error = "El monto debe ser un número entero mayor a 0."
        elif len(d["nota"]) > 255:
            error = "La nota es demasiado larga (máximo 255 caracteres)."

        if error == "":
            try:
                if gasto is None:
                    gasto = Gasto(usuario_id=current_user.id)
                    db.session.add(gasto)
                gasto.fecha = fecha
                gasto.concepto = d["concepto"]
                gasto.categoria = d["categoria"]
                gasto.monto = int(d["monto"])
                gasto.nota = d["nota"] or None
                db.session.commit()
                return redirect(url_for("gastos.lista", msg="guardado"))
            except IntegrityError:
                db.session.rollback()
                error = "No se pudo guardar el gasto. Revisa los datos e intenta de nuevo."

    return render_template("admin_gasto_form.html", d=d, id=id, error=error, categorias=CATEGORIAS_GASTO,
                           hoy=date.today().isoformat(), token=token_csrf())


@gastos.route("/<int:id>/eliminar", methods=["POST"])
@admin_requerido
def eliminar(id):
    if not token_valido():
        return redirect(url_for("gastos.lista", msg="error"))

    gasto = db.session.get(Gasto, id)
    if gasto is None:
        return redirect(url_for("gastos.lista", msg="error"))
    db.session.delete(gasto)
    db.session.commit()
    return redirect(url_for("gastos.lista", msg="eliminado"))
