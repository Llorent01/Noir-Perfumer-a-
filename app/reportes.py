from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request
from app import finanzas
from app.auth import admin_requerido
from app.database import db
from app.models import Pedido, DetallePedido, Perfume
from app.utilidades import leer_fecha, respuesta_csv

reportes = Blueprint("reportes", __name__, url_prefix="/admin/reportes")

PRESENTACIONES = [5, 10, 100]


def leer_filtros(args):
    perfume_id = args.get("perfume", "")
    ml = args.get("ml", "")
    return {
        "desde": leer_fecha(args.get("desde", "")),
        "hasta": leer_fecha(args.get("hasta", "")),
        "perfume": int(perfume_id) if perfume_id.isdigit() else None,
        "marca": args.get("marca", "").strip(),
        "ml": int(ml) if ml.isdigit() and int(ml) in PRESENTACIONES else None,
    }


def consultar(f):
    consulta = (db.session.query(Pedido, DetallePedido, Perfume)
                .join(DetallePedido, DetallePedido.pedido_id == Pedido.id)
                .join(Perfume, Perfume.id == DetallePedido.perfume_id))
    if f["desde"]:
        consulta = consulta.filter(Pedido.fecha >= datetime.combine(f["desde"], datetime.min.time()))
    if f["hasta"]:
        consulta = consulta.filter(Pedido.fecha < datetime.combine(f["hasta"] + timedelta(days=1), datetime.min.time()))
    if f["perfume"]:
        consulta = consulta.filter(Perfume.id == f["perfume"])
    if f["marca"]:
        consulta = consulta.filter(Perfume.marca == f["marca"])
    if f["ml"]:
        consulta = consulta.filter(DetallePedido.ml == f["ml"])

    filas = []
    for pedido, detalle, perfume in consulta.order_by(Pedido.fecha.desc(), Pedido.id.desc()).all():
        filas.append({"id": pedido.id, "fecha": pedido.fecha, "cliente": pedido.cliente_nombre,
                      "perfume": perfume.nombre, "marca": perfume.marca, "ml": detalle.ml,
                      "cantidad": detalle.cantidad, "total": pedido.total,
                      "abonado": pedido.abonado, "debe": pedido.debe})
    return filas


def totales(filas):
    vendido = sum(f["total"] for f in filas)
    abonado = sum(f["abonado"] for f in filas)
    return {"ventas": len(filas), "unidades": sum(f["cantidad"] for f in filas),
            "vendido": vendido, "abonado": abonado, "por_cobrar": vendido - abonado}


def por_periodo(filas):
    # Si el rango es corto se agrupa por día; si es largo, por mes
    if not filas:
        return "dia", []
    fechas = [f["fecha"].date() for f in filas]
    agrupar = "dia" if (max(fechas) - min(fechas)).days <= 62 else "mes"

    acumulado = {}
    for f in filas:
        d = f["fecha"].date()
        clave = d.isoformat() if agrupar == "dia" else d.strftime("%Y-%m")
        if clave not in acumulado:
            acumulado[clave] = {"vendido": 0, "ventas": 0}
        acumulado[clave]["vendido"] += f["total"]
        acumulado[clave]["ventas"] += 1

    lista = []
    for clave in sorted(acumulado):
        if agrupar == "dia":
            etiqueta = datetime.strptime(clave, "%Y-%m-%d").strftime("%d/%m")
            nombre = datetime.strptime(clave, "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            anio, mes = clave.split("-")
            etiqueta = finanzas.MESES[int(mes) - 1] + " " + anio[2:]
            nombre = finanzas.MESES[int(mes) - 1] + " " + anio
        lista.append({"etiqueta": etiqueta, "nombre": nombre, "vendido": acumulado[clave]["vendido"],
                      "ventas": acumulado[clave]["ventas"]})
    return agrupar, lista


def grafico(periodos):
    ancho, alto = 640, 260
    izq, der, arriba, abajo = 64, 14, 16, 40
    area_w, area_h = ancho - izq - der, alto - arriba - abajo
    tope = finanzas._maximo_redondo(max([p["vendido"] for p in periodos] + [0]))
    cada = max(1, -(-len(periodos) // 10))  # muestra máximo ~10 etiquetas
    grupo = area_w / max(len(periodos), 1)
    barra = min(46, grupo * 0.62)

    barras = []
    for i, p in enumerate(periodos):
        h = area_h * p["vendido"] / tope
        centro = izq + grupo * i + grupo / 2
        barras.append({"x": round(centro - barra / 2, 1), "y": round(arriba + area_h - h, 1), "h": round(h, 1),
                       "w": round(barra, 1), "centro": round(centro, 1), "mostrar": i % cada == 0,
                       "etiqueta": p["etiqueta"], "texto": p["nombre"] + ": " + finanzas_pesos(p["vendido"])})
    ejes = [{"y": round(arriba + area_h - area_h * k / 4, 1), "texto": finanzas.valor_corto(tope * k / 4)} for k in range(5)]
    return {"ancho": ancho, "alto": alto, "izq": izq, "der": ancho - der, "barras": barras, "ejes": ejes}


def finanzas_pesos(valor):
    return "$" + "{:,}".format(int(valor)).replace(",", ".")


@reportes.route("/")
@admin_requerido
def inicio():
    f = leer_filtros(request.args)
    filas = consultar(f)
    agrupar, periodos = por_periodo(filas)

    marcas = [m[0] for m in db.session.query(Perfume.marca).distinct().order_by(Perfume.marca).all()]
    perfumes = Perfume.query.order_by(Perfume.nombre).all()
    texto = {"desde": f["desde"].isoformat() if f["desde"] else "", "hasta": f["hasta"].isoformat() if f["hasta"] else "",
             "perfume": str(f["perfume"] or ""), "marca": f["marca"], "ml": str(f["ml"] or "")}

    return render_template("admin_reportes.html", filas=filas, t=totales(filas), periodos=periodos, agrupar=agrupar,
                           grafico=grafico(periodos), f=texto, marcas=marcas, perfumes=perfumes,
                           presentaciones=PRESENTACIONES, consulta=request.query_string.decode())


@reportes.route("/exportar.csv")
@admin_requerido
def exportar():
    f = leer_filtros(request.args)
    filas = consultar(f)
    salida = []
    for r in filas:
        salida.append([r["id"], r["fecha"].strftime("%d/%m/%Y %H:%M"), r["cliente"], r["perfume"], r["marca"],
                       r["ml"], r["cantidad"], r["total"], r["abonado"], r["debe"]])
    t = totales(filas)
    salida.append([])
    salida.append(["", "", "", "", "", "", "Total (" + str(t["ventas"]) + " ventas)", t["vendido"], t["abonado"], t["por_cobrar"]])
    return respuesta_csv("reporte_ventas_" + date.today().strftime("%Y%m%d") + ".csv",
                         ["Venta", "Fecha", "Cliente", "Perfume", "Marca", "Presentación (ML)", "Cantidad",
                          "Total", "Abonado", "Debe"], salida)
