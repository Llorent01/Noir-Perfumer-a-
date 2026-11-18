from datetime import date
from flask import Blueprint, render_template, request
from app import finanzas
from app.auth import admin_requerido
from app.utilidades import leer_fecha, respuesta_csv

dashboard = Blueprint("dashboard", __name__, url_prefix="/admin")


@dashboard.route("/")
@admin_requerido
def inicio():
    return render_template(
        "admin_dashboard.html",
        r=finanzas.resumen(),
        grafico=finanzas.grafico_mensual(6),
        categorias=finanzas.gastos_por_categoria(),
        deudas=finanzas.mayores_deudas(5),
        ventas=finanzas.ultimas_ventas(5),
        movimientos=finanzas.movimientos()[:8],
        hoy=date.today(),
    )


def filtros_historial(args):
    tipo = args.get("tipo", "todos")
    if tipo not in ("todos", "ingresos", "gastos"):
        tipo = "todos"
    desde = leer_fecha(args.get("desde", ""))
    hasta = leer_fecha(args.get("hasta", ""))
    buscar = args.get("buscar", "").strip()
    return tipo, desde, hasta, buscar


@dashboard.route("/historial")
@admin_requerido
def historial():
    tipo, desde, hasta, buscar = filtros_historial(request.args)
    lista = finanzas.movimientos(desde, hasta, tipo, buscar)
    return render_template("admin_historial.html", movimientos=lista, totales=finanzas.totales_movimientos(lista),
                           tipo=tipo, buscar=buscar,
                           desde=desde.isoformat() if desde else "", hasta=hasta.isoformat() if hasta else "")


@dashboard.route("/historial.csv")
@admin_requerido
def historial_csv():
    tipo, desde, hasta, buscar = filtros_historial(request.args)
    lista = finanzas.movimientos(desde, hasta, tipo, buscar)
    filas = []
    for m in lista:
        filas.append([m["fecha"].strftime("%d/%m/%Y %H:%M" if m["con_hora"] else "%d/%m/%Y"),
                      "Ingreso" if m["tipo"] == "ingreso" else "Gasto", m["categoria"], m["concepto"],
                      m["detalle"], m["monto"] if m["tipo"] == "ingreso" else -m["monto"]])
    t = finanzas.totales_movimientos(lista)
    filas.append([])
    filas.append(["", "", "", "Total ingresos", "", t["ingresos"]])
    filas.append(["", "", "", "Total gastos", "", -t["gastos"]])
    filas.append(["", "", "", "Balance", "", t["neto"]])
    return respuesta_csv("historial_" + date.today().strftime("%Y%m%d") + ".csv",
                         ["Fecha", "Tipo", "Categoría", "Concepto", "Detalle", "Monto"], filas)
