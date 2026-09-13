from datetime import datetime, timezone
from urllib.parse import urlparse
from flask import request
from werkzeug.exceptions import BadRequest, NotFound

def payload():
    data = request.get_json()
    if not isinstance(data, dict):
        raise BadRequest("El cuerpo debe ser un objeto JSON")
    return data

def text(data, key, maximum=100, optional=False):
    value = data.get(key, "" if optional else None)
    if not isinstance(value, str) or (not optional and not value.strip()) or len(value) > maximum:
        raise BadRequest(f"Campo inválido: {key}")
    return value.strip()

def integer(value, field, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).isdigit():
        raise BadRequest(f"Entero inválido: {field}")
    value = int(value)
    if value < minimum or (maximum is not None and value > maximum):
        raise BadRequest(f"Valor fuera de rango: {field}")
    return value

def enum_value(kind, value, field):
    if isinstance(value, str):
        for member in kind:
            if value.lower() in (member.name.lower(), member.value.lower()):
                return member
    raise BadRequest(f"Valor inválido: {field}")

def date_value(value, future=False):
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError()
        date = date.astimezone(timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, AttributeError):
        raise BadRequest("La fecha debe incluir fecha, hora y zona horaria ISO 8601")
    if future and date <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise BadRequest("La cita debe tener una fecha futura")
    return date

def existing(model, identifier):
    from models import db
    item = db.session.get(model, integer(identifier, "id", 1))
    if item is None:
        raise NotFound("Registro no encontrado")
    return item

def video_url(data):
    value = text(data, "video_url", 200)
    parsed = urlparse(value)
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        raise BadRequest("El video debe tener una URL HTTP(S) válida")
    return value

