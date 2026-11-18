import secrets
from flask import session, request


def token_csrf():
    # Un token por sesión; se envía oculto en cada formulario que cambia datos
    if "token" not in session:
        session["token"] = secrets.token_hex(16)
    return session["token"]


def token_valido():
    enviado = request.form.get("token", "")
    guardado = session.get("token", "")
    return guardado != "" and secrets.compare_digest(enviado, guardado)
