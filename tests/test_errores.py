from sqlalchemy.exc import OperationalError


def test_pagina_404_amigable(cliente):
    r = cliente.get("/no-existe")
    assert r.status_code == 404 and "Página no encontrada" in r.get_data(as_text=True)


def test_pagina_403_amigable(cliente_normal):
    r = cliente_normal.get("/admin/")
    assert r.status_code == 403 and "Acceso denegado" in r.get_data(as_text=True)


def test_405_amigable(cliente):
    assert cliente.get("/logout").status_code == 405


def test_base_de_datos_caida_no_muestra_detalles(app):
    @app.route("/explota")
    def explota():
        raise OperationalError("SELECT secreto", {}, Exception("password=abc123"))

    r = app.test_client().get("/explota")
    texto = r.get_data(as_text=True)
    assert r.status_code == 503 and "MySQL esté encendido" in texto
    assert "secreto" not in texto and "abc123" not in texto


def test_error_inesperado_no_muestra_detalles(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/falla")
    def falla():
        raise RuntimeError("detalle-interno-123")

    r = app.test_client().get("/falla")
    assert r.status_code == 500 and "detalle-interno-123" not in r.get_data(as_text=True)


def test_prueba_bd(cliente, perfume):
    assert cliente.get("/prueba-bd").get_json() == {"perfumes": 1, "usuarios": 0}
