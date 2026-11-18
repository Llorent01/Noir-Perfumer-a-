# Cálculos de dinero del negocio. Todo se maneja en pesos enteros para evitar errores de redondeo.
#
#   Vendido    = suma del total de todas las ventas
#   Cobrado    = suma de todos los abonos (dinero que realmente entró)
#   Por cobrar = Vendido - Cobrado
#   Gastos     = suma de todos los gastos registrados
#   En mano    = Cobrado - Gastos
#   Ganancia   = Vendido - Gastos  (cuando se cobre todo lo pendiente)

from datetime import date, datetime, timedelta
from sqlalchemy import func, desc
from app.database import db
from app.models import Pedido, Abono, Gasto

CATEGORIAS_GASTO = [
    "Compra de perfumes",
    "Envases y empaques",
    "Publicidad",
    "Envíos y transporte",
    "Servicios",
    "Otros",
]

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _entero(valor):
    return int(valor or 0)


def inicio_de_mes(hoy=None):
    hoy = hoy or date.today()
    return datetime(hoy.year, hoy.month, 1)


def resumen():
    vendido = _entero(db.session.query(func.sum(Pedido.total)).scalar())
    cobrado = _entero(db.session.query(func.sum(Abono.monto)).scalar())
    gastos = _entero(db.session.query(func.sum(Gasto.monto)).scalar())
    ventas = db.session.query(func.count(Pedido.id)).scalar() or 0

    mes = inicio_de_mes()
    cobrado_mes = _entero(db.session.query(func.sum(Abono.monto)).filter(Abono.fecha >= mes).scalar())
    gastos_mes = _entero(db.session.query(func.sum(Gasto.monto)).filter(Gasto.fecha >= mes.date()).scalar())
    vendido_mes = _entero(db.session.query(func.sum(Pedido.total)).filter(Pedido.fecha >= mes).scalar())

    return {
        "ventas": ventas,
        "vendido": vendido,
        "cobrado": cobrado,
        "por_cobrar": vendido - cobrado,
        "gastos": gastos,
        "en_mano": cobrado - gastos,
        "ganancia": vendido - gastos,
        "vendido_mes": vendido_mes,
        "cobrado_mes": cobrado_mes,
        "gastos_mes": gastos_mes,
    }


def gastos_por_categoria():
    filas = (db.session.query(Gasto.categoria, func.sum(Gasto.monto))
             .group_by(Gasto.categoria).order_by(desc(func.sum(Gasto.monto))).all())
    total = sum(_entero(f[1]) for f in filas)
    resultado = []
    for categoria, monto in filas:
        monto = _entero(monto)
        resultado.append({"categoria": categoria, "monto": monto,
                          "porcentaje": round(monto * 100 / total) if total else 0})
    return resultado


def mayores_deudas(limite=5):
    pagado = (db.session.query(Abono.pedido_id.label("pid"), func.sum(Abono.monto).label("pagado"))
              .group_by(Abono.pedido_id).subquery())
    debe = Pedido.total - func.coalesce(pagado.c.pagado, 0)
    filas = (db.session.query(Pedido, debe.label("debe"))
             .outerjoin(pagado, pagado.c.pid == Pedido.id)
             .filter(debe > 0).order_by(desc("debe")).limit(limite).all())
    return [{"pedido": p, "debe": _entero(d)} for p, d in filas]


def ultimas_ventas(limite=5):
    return Pedido.query.order_by(Pedido.fecha.desc(), Pedido.id.desc()).limit(limite).all()


def movimientos(desde=None, hasta=None, tipo="todos", buscar=""):
    """Dinero que entra (abonos) y dinero que sale (gastos), del más reciente al más antiguo."""
    lista = []

    if tipo in ("todos", "ingresos"):
        consulta = db.session.query(Abono, Pedido).join(Pedido, Abono.pedido_id == Pedido.id)
        if desde:
            consulta = consulta.filter(Abono.fecha >= datetime.combine(desde, datetime.min.time()))
        if hasta:
            consulta = consulta.filter(Abono.fecha < datetime.combine(hasta + timedelta(days=1), datetime.min.time()))
        for abono, pedido in consulta.all():
            linea = pedido.detalle
            detalle = pedido.cliente_nombre
            if linea:
                detalle += " · " + linea.perfume.nombre + " " + str(linea.ml) + " ML"
            lista.append({"fecha": abono.fecha, "con_hora": True, "tipo": "ingreso",
                          "concepto": "Abono de venta #" + str(pedido.id), "detalle": detalle,
                          "categoria": "Venta", "monto": abono.monto, "url": "/admin/ventas/" + str(pedido.id)})

    if tipo in ("todos", "gastos"):
        consulta = Gasto.query
        if desde:
            consulta = consulta.filter(Gasto.fecha >= desde)
        if hasta:
            consulta = consulta.filter(Gasto.fecha <= hasta)
        for g in consulta.all():
            lista.append({"fecha": datetime.combine(g.fecha, datetime.min.time()), "con_hora": False,
                          "tipo": "gasto", "concepto": g.concepto, "detalle": g.nota or "",
                          "categoria": g.categoria, "monto": g.monto, "url": "/admin/gastos/" + str(g.id) + "/editar"})

    texto = buscar.strip().lower()
    if texto:
        lista = [m for m in lista if texto in (m["concepto"] + " " + m["detalle"] + " " + m["categoria"]).lower()]

    lista.sort(key=lambda m: m["fecha"], reverse=True)
    return lista


def totales_movimientos(lista):
    ingresos = sum(m["monto"] for m in lista if m["tipo"] == "ingreso")
    gastos = sum(m["monto"] for m in lista if m["tipo"] == "gasto")
    return {"ingresos": ingresos, "gastos": gastos, "neto": ingresos - gastos}


def _maximo_redondo(valor):
    # Sube el máximo a 1, 2, 5 o 10 por una potencia de diez para que los ejes se lean fácil
    if valor <= 0:
        return 1
    potencia = 1
    while potencia * 10 <= valor:
        potencia *= 10
    for paso in (1, 2, 5, 10):
        if paso * potencia >= valor:
            return paso * potencia
    return 10 * potencia


def valor_corto(valor):
    if valor >= 1000000:
        return ("%.1f" % (valor / 1000000)).replace(".", ",").replace(",0", "") + " M"
    if valor >= 1000:
        return str(int(valor / 1000)) + " mil"
    return str(int(valor))


def grafico_mensual(cantidad=6):
    """Ingresos cobrados contra gastos de los últimos meses, ya calculado como barras SVG."""
    hoy = date.today()
    meses = []
    anio, mes = hoy.year, hoy.month
    for _ in range(cantidad):
        meses.append((anio, mes))
        mes -= 1
        if mes == 0:
            mes, anio = 12, anio - 1
    meses.reverse()

    primero = datetime(meses[0][0], meses[0][1], 1)
    ingresos = {m: 0 for m in meses}
    gastos = {m: 0 for m in meses}
    for abono in Abono.query.filter(Abono.fecha >= primero).all():
        clave = (abono.fecha.year, abono.fecha.month)
        if clave in ingresos:
            ingresos[clave] += abono.monto
    for gasto in Gasto.query.filter(Gasto.fecha >= primero.date()).all():
        clave = (gasto.fecha.year, gasto.fecha.month)
        if clave in gastos:
            gastos[clave] += gasto.monto

    ancho, alto = 640, 270
    izq, der, arriba, abajo = 64, 14, 16, 40
    area_w = ancho - izq - der
    area_h = alto - arriba - abajo
    tope = _maximo_redondo(max(list(ingresos.values()) + list(gastos.values()) + [0]))
    grupo = area_w / len(meses)
    barra = min(30, grupo / 3)

    barras = []
    for i, clave in enumerate(meses):
        centro = izq + grupo * i + grupo / 2
        h1 = area_h * ingresos[clave] / tope
        h2 = area_h * gastos[clave] / tope
        barras.append({
            "etiqueta": MESES[clave[1] - 1],
            "centro": round(centro, 1),
            "x1": round(centro - barra - 2, 1), "h1": round(h1, 1), "y1": round(arriba + area_h - h1, 1),
            "x2": round(centro + 2, 1), "h2": round(h2, 1), "y2": round(arriba + area_h - h2, 1),
            "ingresos": ingresos[clave], "gastos": gastos[clave], "ancho_barra": round(barra, 1),
        })

    ejes = []
    for k in range(5):
        valor = tope * k / 4
        ejes.append({"y": round(arriba + area_h - area_h * k / 4, 1), "texto": valor_corto(valor)})

    return {"ancho": ancho, "alto": alto, "izq": izq, "der": ancho - der, "base": arriba + area_h,
            "barras": barras, "ejes": ejes, "tiene_datos": tope > 1 or any(ingresos.values()) or any(gastos.values())}
