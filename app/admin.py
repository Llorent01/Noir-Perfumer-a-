import os
import secrets
import time
from flask import Blueprint, render_template, request, redirect, url_for, session, abort, current_app
from sqlalchemy.exc import IntegrityError
from app.auth import admin_requerido
from app.seguridad import token_csrf, token_valido
from app.database import db
from app.models import Perfume, Tamano

admin = Blueprint("admin", __name__, url_prefix="/admin")

GENEROS = ["Hombre", "Mujer", "Unisex"]
TAMANOS = [5, 10, 15, 20, 100]


def precio_valido(texto):
    return texto.isdigit() and int(texto) > 0


def tipo_de_imagen(archivo):
    # Revisa los primeros bytes del archivo para saber si es JPG, PNG o WEBP
    inicio = archivo.read(12)
    archivo.seek(0)
    if inicio[:3] == b"\xff\xd8\xff":
        return "jpg"
    if inicio[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if inicio[:4] == b"RIFF" and inicio[8:12] == b"WEBP":
        return "webp"
    return None


def guardar_tamano(perfume, ml, texto):
    existente = None
    for t in perfume.tamanos:
        if t.ml == ml:
            existente = t

    if texto == "":
        if existente:
            perfume.tamanos.remove(existente)
    elif existente:
        existente.precio = int(texto)
    else:
        perfume.tamanos.append(Tamano(ml=ml, precio=int(texto)))


@admin.route("/perfumes/")
@admin_requerido
def panel():
    buscar = request.args.get("buscar", "").strip()
    texto = "%" + buscar + "%"

    perfumes = Perfume.query.filter(
        db.or_(Perfume.nombre.like(texto), Perfume.marca.like(texto))
    ).order_by(Perfume.id.desc()).all()

    todos = Perfume.query.all()
    datos = {
        "total": len(todos),
        "disponibles": len([p for p in todos if p.disponible == 1]),
        "agotados": len([p for p in todos if p.disponible == 0]),
        "vendidos": len([p for p in todos if p.mas_vendido == 1])
    }

    mensajes = {
        "eliminado": ("Perfume eliminado.", "ok"),
        "guardado": ("Perfume guardado.", "ok"),
        "conpedidos": ("No se puede eliminar: el perfume tiene pedidos registrados.", "error"),
        "error": ("No se pudo completar la acción.", "error")
    }
    mensaje, tipo = mensajes.get(request.args.get("msg"), ("", "ok"))

    return render_template("admin_lista.html", perfumes=perfumes, buscar=buscar,
                           datos=datos, mensaje=mensaje, tipo=tipo, token=token_csrf())


@admin.route("/perfume/nuevo", methods=["GET", "POST"], defaults={"id": 0})
@admin.route("/perfume/<int:id>/editar", methods=["GET", "POST"])
@admin_requerido
def formulario(id=0):
    perfume = None
    if id > 0:
        perfume = db.session.get(Perfume, id)
        if perfume is None:
            abort(404)

    d = {"nombre": "", "marca": "", "genero": "Hombre", "familia": "", "familia_tag": "",
         "notas": "", "descripcion": "", "imagen": "", "mas_vendido": 0, "disponible": 1}
    for ml in TAMANOS:
        d["precio" + str(ml)] = ""

    if perfume:
        for campo in ["nombre", "marca", "genero", "familia", "familia_tag", "notas",
                      "descripcion", "imagen", "mas_vendido", "disponible"]:
            d[campo] = getattr(perfume, campo) or ""
        for t in perfume.tamanos:
            d["precio" + str(t.ml)] = t.precio

    error = ""

    if request.method == "POST":
        if not token_valido():
            return redirect(url_for("admin.panel", msg="error"))

        for campo in ["nombre", "marca", "familia", "familia_tag", "notas", "descripcion"]:
            d[campo] = request.form.get(campo, "").strip()
        d["genero"] = request.form.get("genero", "")
        d["mas_vendido"] = 1 if request.form.get("mas_vendido") else 0
        d["disponible"] = 1 if request.form.get("disponible") else 0
        for ml in TAMANOS:
            d["precio" + str(ml)] = request.form.get("precio" + str(ml), "").strip()

        if d["nombre"] == "" or d["marca"] == "" or d["familia"] == "" or d["familia_tag"] == "":
            error = "Completa nombre, marca, familia y tipo de fragancia."
        elif d["genero"] not in GENEROS:
            error = "Elige un género válido."
        elif not precio_valido(str(d["precio5"])) or not precio_valido(str(d["precio10"])):
            error = "Los precios de 5 ML y 10 ML son obligatorios y deben ser números enteros."
        else:
            for ml in [15, 20, 100]:
                valor = str(d["precio" + str(ml)])
                if valor != "" and not precio_valido(valor):
                    error = "Los precios opcionales deben ser números enteros o quedar vacíos."

        ruta_imagen = d["imagen"]
        archivo = request.files.get("imagen")

        if error == "":
            if archivo and archivo.filename != "":
                extension = tipo_de_imagen(archivo)
                archivo.seek(0, os.SEEK_END)
                peso = archivo.tell()
                archivo.seek(0)
                if extension is None:
                    error = "La imagen debe ser JPG, PNG o WEBP."
                elif peso > 2 * 1024 * 1024:
                    error = "La imagen pesa más de 2 MB."
                else:
                    nombre_archivo = "perfume_" + str(int(time.time())) + "_" + secrets.token_hex(2) + "." + extension
                    carpeta = os.path.join(current_app.static_folder, "img", "Perfume 100ml")
                    os.makedirs(carpeta, exist_ok=True)
                    archivo.save(os.path.join(carpeta, nombre_archivo))
                    ruta_imagen = "img/Perfume 100ml/" + nombre_archivo
            elif id == 0:
                error = "Selecciona una imagen para el perfume."

        if error == "":
            try:
                if perfume is None:
                    perfume = Perfume()
                    db.session.add(perfume)
                perfume.nombre = d["nombre"]
                perfume.marca = d["marca"]
                perfume.genero = d["genero"]
                perfume.familia = d["familia"]
                perfume.familia_tag = d["familia_tag"]
                perfume.notas = d["notas"]
                perfume.descripcion = d["descripcion"]
                perfume.imagen = ruta_imagen
                perfume.mas_vendido = d["mas_vendido"]
                perfume.disponible = d["disponible"]
                for ml in TAMANOS:
                    guardar_tamano(perfume, ml, str(d["precio" + str(ml)]))
                db.session.commit()
                return redirect(url_for("admin.panel", msg="guardado"))
            except IntegrityError:
                db.session.rollback()
                error = "No se pudo guardar el perfume. Revisa los datos e intenta de nuevo."

    etiquetas = [fila[0] for fila in db.session.query(Perfume.familia_tag).distinct().order_by(Perfume.familia_tag)]
    return render_template("admin_formulario.html", d=d, id=id, error=error,
                           generos=GENEROS, etiquetas=etiquetas, token=token_csrf())


@admin.route("/perfume/<int:id>/eliminar", methods=["POST"])
@admin_requerido
def eliminar(id):
    if not token_valido():
        return redirect(url_for("admin.panel", msg="error"))

    perfume = db.session.get(Perfume, id)
    if perfume is None:
        return redirect(url_for("admin.panel", msg="error"))

    try:
        db.session.delete(perfume)
        db.session.commit()
        return redirect(url_for("admin.panel", msg="eliminado"))
    except IntegrityError:
        db.session.rollback()
        return redirect(url_for("admin.panel", msg="conpedidos"))
