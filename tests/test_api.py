from conftest import crear_venta


def test_api_perfumes_busca_por_nombre_y_marca(admin_cliente, perfume, perfume2):
    datos = admin_cliente.get("/admin/api/perfumes?q=afn").get_json()
    assert datos["total"] == 1 and datos["perfumes"][0]["nombre"] == "9PM"
    p = datos["perfumes"][0]
    assert (p["precio5"], p["precio10"], p["precio100"]) == (25000, 45000, 280000) and p["mas_vendido"] is True
    assert admin_cliente.get("/admin/api/perfumes?q=haw").get_json()["total"] == 1
    assert admin_cliente.get("/admin/api/perfumes?q=zzz").get_json()["total"] == 0
    assert admin_cliente.get("/admin/api/perfumes").get_json()["total"] == 2


def test_api_ventas_busca_y_filtra_deuda(admin_cliente, perfume):
    crear_venta(perfume, cliente="Ana", cantidad=2, total=50000, abonos=[10000])
    crear_venta(perfume, cliente="Luis", total=25000, abonos=[25000])
    assert admin_cliente.get("/admin/api/ventas?q=ana").get_json()["total"] == 1
    deuda = admin_cliente.get("/admin/api/ventas?estado=deuda").get_json()
    assert deuda["total"] == 1
    v = deuda["ventas"][0]
    assert (v["cliente"], v["total"], v["abonado"], v["debe"], v["detalle"]) == ("Ana", 50000, 10000, 40000, "2 × 5 ML")


def test_api_busqueda_con_caracteres_especiales_no_rompe(admin_cliente, perfume):
    for q in ["%", "_", "' OR 1=1 --", "<script>"]:
        assert admin_cliente.get("/admin/api/perfumes", query_string={"q": q}).status_code == 200


def test_api_solo_para_admins(cliente, cliente_normal):
    assert cliente.get("/admin/api/ventas").status_code == 302
    assert cliente_normal.get("/admin/api/ventas").status_code == 403


def test_api_publica_de_la_tienda(cliente, perfume):
    datos = cliente.get("/api/perfumes").get_json()
    assert datos[0]["name"] == "9PM" and datos[0]["price5"] == 25000 and datos[0]["full100"] == 280000
    assert datos[0]["image"].startswith("/static/") and datos[0]["inStock"] is True


def test_tienda_es_publica(cliente):
    assert cliente.get("/").status_code == 200
