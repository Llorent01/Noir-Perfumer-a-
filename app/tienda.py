from flask import Blueprint, render_template, jsonify
from app.models import Perfume

tienda = Blueprint("tienda", __name__)


@tienda.route("/")
def inicio():
    return render_template("tienda.html")


@tienda.route("/api/perfumes")
def api_perfumes():
    lista = []
    for p in Perfume.query.order_by(Perfume.id).all():
        perfume = {
            "id": p.id,
            "image": "/static/" + (p.imagen or ""),
            "name": p.nombre,
            "brand": p.marca,
            "gender": p.genero,
            "family": p.familia,
            "familyTag": p.familia_tag,
            "notes": p.notas,
            "desc": p.descripcion,
            "bestSeller": p.mas_vendido == 1,
            "inStock": p.disponible == 1
        }
        for t in p.tamanos:
            if t.ml == 100:
                perfume["full100"] = t.precio
            else:
                perfume["price" + str(t.ml)] = t.precio
        lista.append(perfume)
    return jsonify(lista)
