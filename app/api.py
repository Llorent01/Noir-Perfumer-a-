from flask import Blueprint, jsonify, request, url_for
from app.auth import admin_requerido
from app.database import db
from app.models import Perfume, Pedido

api = Blueprint("api", __name__, url_prefix="/admin/api")


@api.route("/perfumes")
@admin_requerido
def perfumes():
    texto = "%" + request.args.get("q", "").strip() + "%"
    lista = Perfume.query.filter(
        db.or_(Perfume.nombre.like(texto), Perfume.marca.like(texto))
    ).order_by(Perfume.id.desc()).all()

    resultado = []
    for p in lista:
        precios = {t.ml: t.precio for t in p.tamanos}
        resultado.append({
            "id": p.id,
            "nombre": p.nombre,
            "marca": p.marca,
            "familia_tag": p.familia_tag,
            "genero": p.genero,
            "imagen": url_for("static", filename=p.imagen) if p.imagen else "",
            "mas_vendido": p.mas_vendido == 1,
            "disponible": p.disponible == 1,
            "precio5": precios.get(5),
            "precio10": precios.get(10),
            "precio100": precios.get(100),
            "url_editar": url_for("admin.formulario", id=p.id),
            "url_eliminar": url_for("admin.eliminar", id=p.id)
        })
    return jsonify({"total": len(resultado), "perfumes": resultado})


@api.route("/ventas")
@admin_requerido
def ventas():
    texto = "%" + request.args.get("q", "").strip() + "%"
    pedidos = Pedido.query.filter(Pedido.cliente_nombre.like(texto)).order_by(Pedido.fecha.desc()).all()

    if request.args.get("estado") == "deuda":
        pedidos = [p for p in pedidos if p.debe > 0]

    resultado = []
    for p in pedidos:
        linea = p.detalle
        resultado.append({
            "id": p.id,
            "fecha": p.fecha.strftime("%d/%m/%Y %H:%M"),
            "cliente": p.cliente_nombre,
            "perfume": linea.perfume.nombre if linea else "",
            "detalle": str(linea.cantidad) + " × " + str(linea.ml) + " ML" if linea else "",
            "total": p.total,
            "abonado": p.abonado,
            "debe": p.debe,
            "url": url_for("ventas.detalle", id=p.id)
        })
    return jsonify({"total": len(resultado), "ventas": resultado})
