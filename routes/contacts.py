from flask import Blueprint, jsonify, current_app
from flask_mail import Message
from werkzeug.exceptions import ServiceUnavailable
from extensions import mail
from validation import payload, text

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")

@contacts_bp.route("", methods=["POST"])
def post_contact():
    data = payload()
    name = text(data, "nombre")
    phone = text(data, "numero")
    details = text(data, "detalles", 10000)
    recipient = current_app.config.get("CONTACT_EMAIL")
    if not recipient:
        raise ServiceUnavailable("El formulario de contacto no está configurado. Contáctanos por teléfono.")
    message = Message(subject="Nuevo mensaje de contacto",
                      recipients=[recipient],
                      body=f"Nombre: {name}\nTeléfono: {phone}\n\n{details}")
    try:
        mail.send(message)
    except Exception:
        current_app.logger.exception("No se pudo enviar el correo de contacto")
        raise ServiceUnavailable("No pudimos enviar el mensaje. Intenta más tarde.")
    return jsonify(message="Mensaje enviado exitosamente"), 201

