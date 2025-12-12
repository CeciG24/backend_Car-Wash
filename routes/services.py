from flask import Blueprint, jsonify, request
from models import db
from models.services import Services
from models.serviceDescription import ServiceDescription
from models.portfolioService import PortfolioService

services_bp = Blueprint('services', __name__, url_prefix='/services')

#CRUD Servicios

# Obtener todos los servicios
@services_bp.route('', methods=['GET'])
def get_services():
    try:
        services = Services.query.all()
        return jsonify({
            "Servicios": [{
                "id_servicio": s.id_service,
                "nombre": s.name,
                "precio": s.price,
            } for s in services]
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener servicios: {str(e)}"}), 500

# Obtener descripcion de un servicio por ID
@services_bp.route('/descriptions/<int:id_service>', methods=['GET'])
def get_service_description_by_id(id_service):
    try:
        description = ServiceDescription.query.filter_by(service_id=id_service).all()
        return jsonify({
            "Descripcion": {
                "id_servicio": description.id_service,
                "descripcion": description.description
            } 
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener descripcion: {str(e)}"}), 500

#Crear un nuevo servicio
@services_bp.route('', methods=['POST'])
def create_service():
    try:
        data = request.get_json()
        new_service = Services(
            name=data['name'],
            price=data['price'],
            tipo=data['tipo'],
            vehiculo=data['vehiculo'],
        )
        db.session.add(new_service)
        db.session.commit()
        return jsonify({"message": "Servicio creado exitosamente"}), 201
    except Exception as e:
        return jsonify({"error": f"Error al crear servicio: {str(e)}"}), 500
    
#Actualizar un servicio por ID
@services_bp.route('/<int:id_service>', methods=['PUT'])
def update_service(id_service):
    try:
        data = request.get_json()
        service = Services.query.get(id_service)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404

        service.name = data.get('name', service.name)
        service.price = data.get('price', service.price)
        service.tipo = data.get('tipo', service.tipo)
        service.vehiculo = data.get('vehiculo', service.vehiculo)

        db.session.commit()
        return jsonify({"message": "Servicio actualizado exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar servicio: {str(e)}"}), 500
    
#Eliminar un servicio por ID
@services_bp.route('/<int:id_service>', methods=['DELETE'])
def delete_service(id_service):
    try:
        service = Services.query.get(id_service)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404

        db.session.delete(service)
        db.session.commit()
        return jsonify({"message": "Servicio eliminado exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar servicio: {str(e)}"}), 500
    