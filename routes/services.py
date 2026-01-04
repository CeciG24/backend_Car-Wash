from flask import Blueprint, jsonify, request
from models import db
from models.services import Services, VehiculoEnum, TipoEnum
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

# Crear un nuevo servicio
@services_bp.route('', methods=['POST'])
def create_service():
    try:
        data = request.get_json()
        
        # Validación básica
        if not data:
            return jsonify({"error": "No se proporcionaron datos"}), 400
        
        # Validar campos requeridos
        required_fields = ['name', 'price', 'tipo']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Faltan campos requeridos: {', '.join(missing_fields)}"}), 400
        
        # Validar que el tipo sea válido
        try:
            tipo_value = TipoEnum[data['tipo'].upper()]
        except KeyError:
            valid_tipos = [e.name for e in TipoEnum]
            return jsonify({"error": f"Tipo inválido. Valores permitidos: {', '.join(valid_tipos)}"}), 400
        
        # Validar vehiculo si se proporciona
        vehiculo_value = None
        if 'vehiculo' in data and data['vehiculo']:
            try:
                vehiculo_value = VehiculoEnum[data['vehiculo'].upper().replace(' ', '_')]
            except KeyError:
                valid_vehiculos = [e.name for e in VehiculoEnum]
                return jsonify({"error": f"Vehículo inválido. Valores permitidos: {', '.join(valid_vehiculos)}"}), 400
        
        # Validar que el precio sea un número positivo
        try:
            price = int(data['price'])
            if price < 0:
                return jsonify({"error": "El precio debe ser un número positivo"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "El precio debe ser un número válido"}), 400
        
        new_service = Services(
            name=data['name'],
            price=price,
            tipo=tipo_value,
            vehiculo=vehiculo_value
        )
        
        db.session.add(new_service)
        db.session.commit()
        
        return jsonify({
            "message": "Servicio creado exitosamente",
            "id_service": new_service.id_service,
            "service": {
                "id": new_service.id_service,
                "name": new_service.name,
                "price": new_service.price,
                "tipo": new_service.tipo.value,
                "vehiculo": new_service.vehiculo.value if new_service.vehiculo else None
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
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
    
#Obtener servicio por id
@services_bp.route('/<int:id_service>', methods=['GET'])
def get_service_by_id(id_service):
    try:
        service = Services.query.get(id_service)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404

        return jsonify({
            "Servicio": {
                "id_servicio": service.id_service,
                "nombre": service.name,
                "precio": service.price,
                "tipo": service.tipo,
                "vehiculo": service.vehiculo
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener servicio: {str(e)}"}), 500
    
# Crear descripcion de un servicio
@services_bp.route('/descriptions', methods=['POST'])
def create_service_description():
    try:
        data = request.get_json()
        
        # Validación básica
        if not data:
            return jsonify({"error": "No se proporcionaron datos"}), 400
        
        if 'service_id' not in data or 'description' not in data:
            return jsonify({"error": "Faltan campos requeridos: service_id y description"}), 400
        
        # Verificar que el servicio existe
        service = Services.query.get(data['service_id'])
        if not service:
            return jsonify({"error": "El servicio especificado no existe"}), 404
        
        new_description = ServiceDescription(
            service_id=data['service_id'],
            description=data['description'],
            order=data.get('order', 0)  # Usar get() para el campo opcional
        )
        
        db.session.add(new_description)
        db.session.commit()
        
        return jsonify({
            "message": "Descripcion de servicio creada exitosamente",
            "id_description": new_description.id_description
        }), 201
        
    except Exception as e:
        db.session.rollback()  # Importante: revertir cambios en caso de error
        return jsonify({"error": f"Error al crear descripcion: {str(e)}"}), 500
    