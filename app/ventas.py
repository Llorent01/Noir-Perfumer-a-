from flask import Blueprint, render_template, request, redirect, url_for, abort
from sqlalchemy.exc import IntegrityError
from app.seguridad import token_csrf, token_valido
from app.auth import admin_requerido
from app.database import db
from app.models import Perfume, Pedido, DetallePedido, Abono

ventas = Blueprint("ventas", __name__, url_prefix="/admin/ventas")

PRESENTACIONES = [5, 10, 100]


def entero_positivo(texto):
    return texto.isdigit() and int(texto) > 0


def precios_por_perfume():
    # {id_perfume: {"5": 25000, "10": 45000, "100": 300000}} para sugerir el total
    mapa = {}
    for p in Perfume.query.all():
        mapa[p.id] = {str(t.ml): t.precio for t in p.tamanos}
    return mapa


@ventas.route("/")
@admin_requerido
def lista():
    buscar = request.args.get("buscar", "").strip()
    solo_deuda = request.args.get("estado") == "deuda"

    consulta = Pedido.query.filter(Pedido.cliente_nombre.like("%" + buscar + "%"))
    pedidos = consulta.order_by(Pedido.fecha.desc()).all()
    if solo_deuda:
        pedidos = [p for p in pedidos if p.debe > 0]

    todos = Pedido.query.all()
    datos = {
        "cantidad": len(todos),
        "vendido": sum(p.total for p in todos),
        "cobrado": sum(p.abonado for p in todos),
        "por_cobrar": sum(p.debe for p in todos)
    }

    mensajes = {
        "registrada": ("Venta registrada.", "ok"),
        "eliminada": ("Venta eliminada.", "ok"),
        "error": ("No se pudo completar la acción.", "error")
    }
    mensaje, tipo = mensajes.get(request.args.get("msg"), ("", "ok"))

    return render_template("admin_ventas.html", pedidos=pedidos, buscar=buscar,
                           solo_deuda=solo_deuda, datos=datos, mensaje=mensaje, tipo=tipo)


@ventas.route("/nueva", methods=["GET", "POST"])
@admin_requerido
def nueva():
    d = {"cliente": "", "perfume_id": "", "ml": "5", "cantidad": "1", "total": "", "abono": ""}
    error = ""

    if request.method == "POST":
        if not token_valido():
            return redirect(url_for("ventas.lista", msg="error"))

        for campo in d:
            d[campo] = request.form.get(campo, "").strip()

        perfume = None
        if d["perfume_id"].isdigit():
            perfume = db.session.get(Perfume, int(d["perfume_id"]))

        if d["cliente"] == "":
            error = "Escribe el nombre del cliente."
        elif perfume is None:
            error = "Elige un perfume."
        elif d["ml"] not in [str(m) for m in PRESENTACIONES]:
            error = "Elige una presentación válida."
        elif not entero_positivo(d["cantidad"]):
            error = "La cantidad debe ser un número entero mayor a 0."
        elif not entero_positivo(d["total"]):
            error = "El total debe ser un número entero mayor a 0."
        elif d["abono"] != "" and not d["abono"].isdigit():
            error = "Lo que pagó debe ser un número entero (puede ser 0)."
        elif int(d["abono"] or 0) > int(d["total"]):
            error = "Lo que pagó no puede ser mayor que el total."
        else:
            ml = int(d["ml"])
            precio = None
            for t in perfume.tamanos:
                if t.ml == ml:
                    precio = t.precio
            if precio is None:
                error = "Ese perfume no tiene presentación de " + str(ml) + " ML."

        if error == "":
            try:
                pedido = Pedido(cliente_nombre=d["cliente"], total=int(d["total"]), estado="registrado")
                pedido.detalles.append(DetallePedido(perfume_id=perfume.id, ml=ml,
                                                     cantidad=int(d["cantidad"]), precio=precio))
                if int(d["abono"] or 0) > 0:
                    pedido.abonos.append(Abono(monto=int(d["abono"])))
                db.session.add(pedido)
                db.session.commit()
                return redirect(url_for("ventas.lista", msg="registrada"))
            except IntegrityError:
                db.session.rollback()
                error = "No se pudo registrar la venta. Intenta de nuevo."

    perfumes = Perfume.query.order_by(Perfume.nombre).all()
    return render_template("admin_venta_form.html", d=d, error=error, perfumes=perfumes,
                           precios=precios_por_perfume(), token=token_csrf())


def mostrar_detalle(pedido, error="", mensaje=""):
    return render_template("admin_venta_detalle.html", p=pedido, error=error,
                           mensaje=mensaje, token=token_csrf())


@ventas.route("/<int:id>")
@admin_requerido
def detalle(id):
    pedido = db.session.get(Pedido, id)
    if pedido is None:
        abort(404)
    mensajes = {"abono": "Abono registrado.", "abonoeliminado": "Abono eliminado."}
    return mostrar_detalle(pedido, mensaje=mensajes.get(request.args.get("msg"), ""))


@ventas.route("/<int:id>/abono", methods=["POST"])
@admin_requerido
def nuevo_abono(id):
    pedido = db.session.get(Pedido, id)
    if pedido is None:
        abort(404)
    if not token_valido():
        return redirect(url_for("ventas.lista", msg="error"))

    monto = request.form.get("monto", "").strip()
    if not entero_positivo(monto):
        return mostrar_detalle(pedido, error="El abono debe ser un número entero mayor a 0.")
    if int(monto) > pedido.debe:
        return mostrar_detalle(pedido, error="El abono no puede ser mayor que lo que debe el cliente.")

    try:
        pedido.abonos.append(Abono(monto=int(monto)))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return mostrar_detalle(pedido, error="No se pudo guardar el abono. Intenta de nuevo.")
    return redirect(url_for("ventas.detalle", id=id, msg="abono"))


@ventas.route("/<int:id>/abono/<int:abono_id>/eliminar", methods=["POST"])
@admin_requerido
def eliminar_abono(id, abono_id):
    if not token_valido():
        return redirect(url_for("ventas.lista", msg="error"))

    abono = db.session.get(Abono, abono_id)
    if abono is None or abono.pedido_id != id:
        abort(404)
    db.session.delete(abono)
    db.session.commit()
    return redirect(url_for("ventas.detalle", id=id, msg="abonoeliminado"))


@ventas.route("/<int:id>/eliminar", methods=["POST"])
@admin_requerido
def eliminar(id):
    if not token_valido():
        return redirect(url_for("ventas.lista", msg="error"))

    pedido = db.session.get(Pedido, id)
    if pedido is None:
        return redirect(url_for("ventas.lista", msg="error"))
    db.session.delete(pedido)
    db.session.commit()
    return redirect(url_for("ventas.lista", msg="eliminada"))
