from flask import Blueprint, jsonify, request
from models import db
from models.appointment import Appointments
from datetime import datetime

appointments_bp = Blueprint('appointments', __name__, url_prefix='/appointments')

# Endpoint para crear una nueva cita
@appointments_bp.route("/", methods=['POST'])
def post_appointment():
    try:
        data = request.get_json()
        print("Received data:", data)  # Log the incoming data

        nombre = data.get("name")
        num = data.get("numero_whatsapp")
        direccion = data.get("direccion")
        date = data.get("scheduled_date")
        servicio = data.get("id_service")

        if not all([nombre, num, direccion, date]):
            return jsonify({"error": "Faltan campos"}), 400

        # Crear usuario
        nueva_cita = Appointments(
            name=nombre,
            num_whatsapp=num,
            direccion=direccion,
            scheduled_date=datetime.fromisoformat(date),  # Ensure correct date format
            id_service=servicio
        )

        db.session.add(nueva_cita)
        db.session.commit()

        return jsonify({"message": "Cita creada exitosamente"}), 201
    except Exception as e:
        print("Error:", str(e))  # Log the exception
        return jsonify({"error": f"Error al crear cita: {str(e)}"}), 500
    
# Endpoint para obtener todas las citas
@appointments_bp.route("/", methods=['GET'])
def get_appointments():
    try:
        citas = Appointments.query.all()
        citas_list = [cita.to_dict() for cita in citas]  # Assuming to_dict method exists in Appointments model
        return jsonify(citas_list), 200
    except Exception as e:
        print("Error:", str(e))  # Log the exception
        return jsonify({"error": f"Error al obtener citas: {str(e)}"}), 500 