from flask import Blueprint, jsonify, request
from flask_mail import Message
from app import mail

contacts_bp = Blueprint('contacts', __name__, url_prefix='/contacts')

@contacts_bp.route("", methods=['POST'])
def post_contact():
    try:
        data = request.get_json()
        
        nombre = data.get("nombre")
        numero = data.get("numero")
        detalles = data.get("detalles")

        if not all([nombre, numero, detalles]):
            return jsonify({"error": "Faltan campos obligatorios"}), 400

        # Crear el mensaje de correo
        msg = Message(
            subject=f"Nuevo mensaje de contacto - {nombre}",
            recipients=["ogluis1596@gmail.com"],  # Tu correo donde recibirás los mensajes
            body=f"""
Has recibido un nuevo mensaje de contacto:

Nombre: {nombre}
Teléfono: {numero}

Mensaje:
{detalles}

---
Este mensaje fue enviado desde el formulario de contacto de la pagina web.de ls1713
            """
        )
        
        # Enviar el correo
        mail.send(msg)
        
        return jsonify({
            "message": "Mensaje enviado exitosamente",
            "data": {
                "nombre": nombre,
                "numero": numero,
                "detalles": detalles
            }
        }), 201
        
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": f"Error al enviar el mensaje: {str(e)}"}), 500