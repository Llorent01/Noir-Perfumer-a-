import os
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.exc import OperationalError, SQLAlchemyError
from app.database import db, armar_url
from app.models import Perfume, Usuario
from app.seguridad import token_csrf
from app.utilidades import pesos
from app.auth import auth, login_manager
from app.tienda import tienda
from app.admin import admin
from app.ventas import ventas
from app.usuarios import usuarios
from app.api import api
from app.gastos import gastos
from app.dashboard import dashboard
from app.reportes import reportes


def crear_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-de-desarrollo")
    app.config["SQLALCHEMY_DATABASE_URI"] = armar_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Evita el error "MySQL server has gone away" cuando una conexión lleva mucho tiempo inactiva
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 280}
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

    db.init_app(app)
    login_manager.init_app(app)
    for blueprint in (auth, tienda, admin, ventas, usuarios, api, gastos, dashboard, reportes):
        app.register_blueprint(blueprint)

    app.jinja_env.globals["token_csrf"] = token_csrf
    app.jinja_env.filters["pesos"] = pesos
    app.jinja_env.filters["fecha"] = lambda valor: valor.strftime("%d/%m/%Y %H:%M")
    app.jinja_env.filters["dia"] = lambda valor: valor.strftime("%d/%m/%Y")

    # Páginas de error amigables: nunca se muestran detalles técnicos al usuario
    def pagina_error(codigo, titulo, mensaje):
        return render_template("error.html", codigo=codigo, titulo=titulo, mensaje=mensaje), codigo

    @app.errorhandler(403)
    def error_403(e):
        return pagina_error(403, "Acceso denegado", "No tienes permiso para ver esta página.")

    @app.errorhandler(404)
    def error_404(e):
        return pagina_error(404, "Página no encontrada", "La página que buscas no existe o fue movida.")

    @app.errorhandler(405)
    def error_405(e):
        return pagina_error(405, "Acción no permitida", "Esa acción no está disponible desde aquí.")

    @app.errorhandler(413)
    def error_413(e):
        return pagina_error(413, "Archivo muy grande", "El archivo supera el tamaño permitido.")

    @app.errorhandler(OperationalError)
    def error_conexion(e):
        db.session.rollback()
        return pagina_error(503, "Sin conexión a la base de datos",
                            "No pudimos conectar con la base de datos. Revisa que MySQL esté encendido e intenta de nuevo.")

    @app.errorhandler(SQLAlchemyError)
    def error_base_datos(e):
        db.session.rollback()
        return pagina_error(500, "No se pudo completar la acción", "Ocurrió un problema con los datos. Intenta de nuevo.")

    @app.errorhandler(500)
    def error_500(e):
        return pagina_error(500, "Algo salió mal", "Ocurrió un error inesperado. Intenta de nuevo en un momento.")

    # Ruta para comprobar que la conexión funciona
    @app.route("/prueba-bd")
    def prueba_bd():
        return jsonify({"perfumes": Perfume.query.count(), "usuarios": Usuario.query.count()})

    return app
