import csv
import io
from datetime import date, datetime
from flask import Response


def leer_fecha(texto):
    # Convierte "2026-11-15" en fecha; si viene vacío o mal escrito devuelve None
    try:
        return datetime.strptime(texto.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def pesos(valor):
    numero = int(valor or 0)
    texto = "$" + "{:,}".format(abs(numero)).replace(",", ".")
    return "-" + texto if numero < 0 else texto


def texto_seguro_csv(valor):
    # Evita que Excel interprete como fórmula un texto que empieza con = + - @
    texto = str(valor)
    if texto[:1] in ("=", "+", "-", "@"):
        return "'" + texto
    return texto


def respuesta_csv(nombre_archivo, encabezados, filas):
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(encabezados)
    for fila in filas:
        escritor.writerow([texto_seguro_csv(c) if isinstance(c, str) else c for c in fila])
    # El BOM hace que Excel muestre bien las tildes y la ñ
    contenido = "﻿" + salida.getvalue()
    return Response(contenido, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=" + nombre_archivo})
