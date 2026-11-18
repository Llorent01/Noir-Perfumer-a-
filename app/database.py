import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def armar_url():
    # Para pruebas se puede usar otra base completa
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    host = os.getenv("MYSQL_HOST", "localhost")
    puerto = os.getenv("MYSQL_PORT", "3306")
    usuario = os.getenv("MYSQL_USER", "root")
    clave = os.getenv("MYSQL_PASSWORD", "")
    nombre = os.getenv("MYSQL_DATABASE", "noir")
    return f"mysql+pymysql://{usuario}:{clave}@{host}:{puerto}/{nombre}?charset=utf8mb4"
