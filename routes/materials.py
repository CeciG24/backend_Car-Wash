from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request, g
from werkzeug.exceptions import BadRequest, Conflict
from models import db
from models.material import Material, StockMovement, MaterialPurchase
from validation import payload, text, existing

materials_bp = Blueprint("materials", __name__, url_prefix="/materials")
UNITS = {"ml", "L", "g", "kg", "piezas"}
CATEGORIES = {"Químico", "Herramienta", "Consumible"}

@materials_bp.get('/purchases-summary')
def purchases_summary():
    # Mexico City currently uses UTC-6 throughout the year.
    local = datetime.now(timezone(timedelta(hours=-6)))
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    total = db.session.query(db.func.coalesce(db.func.sum(MaterialPurchase.total_cost), 0)).join(
        StockMovement, StockMovement.id == MaterialPurchase.movement_id).filter(
        StockMovement.created_at >= start.astimezone(timezone.utc).replace(tzinfo=None),
        StockMovement.created_at < end.astimezone(timezone.utc).replace(tzinfo=None)).scalar()
    return jsonify(Resumen=[{'total': float(total)}])

def amount(value, field, positive=False):
    try:
        if isinstance(value, bool):
            raise ValueError()
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or result > Decimal("999999999.999") or result != result.quantize(Decimal(".001")) or (positive and result == 0):
            raise ValueError()
        return result
    except (InvalidOperation, ValueError):
        raise BadRequest(f"{field}: usa un número válido, hasta 3 decimales")

def apply_data(item, data, creating=False):
    for field, size in (("name", 100), ("purpose", 10000)):
        if creating or field in data:
            setattr(item, field, text(data, field, size))
    if creating or "category" in data:
        if data.get("category") not in CATEGORIES:
            raise BadRequest("Categoría inválida")
        item.category = data["category"]
    if creating or "unit" in data:
        if data.get("unit") not in UNITS:
            raise BadRequest("Unidad inválida")
        if not creating and data["unit"] != item.unit and StockMovement.query.filter_by(material_id=item.id).first():
            raise Conflict("No cambies la unidad de un material con movimientos; crea otro registro")
        item.unit = data["unit"]
    if creating or "minimum" in data:
        item.minimum = amount(data.get("minimum", 0), "Existencia mínima")
    if "active" in data:
        if not isinstance(data["active"], bool):
            raise BadRequest("Activo debe ser verdadero o falso")
        item.active = data["active"]
    if creating or "notes" in data:
        item.notes = text(data, "notes", 10000, optional=True)
    if creating or "dilutions" in data:
        rows = data.get("dilutions", [])
        if not isinstance(rows, list) or len(rows) > 30:
            raise BadRequest("Diluciones inválidas")
        result = []
        for row in rows:
            if not isinstance(row, dict):
                raise BadRequest("Dilución inválida")
            result.append({"use": text(row, "use", 200),
                           "product": float(amount(row.get("product"), "Partes de producto", True)),
                           "water": float(amount(row.get("water"), "Partes de agua")),
                           "instructions": text(row, "instructions", 1000, optional=True)})
        item.dilutions = result
    if not creating and "quantity" in data:
        raise BadRequest("Registra una entrada o salida para modificar las existencias")

@materials_bp.route("", methods=["GET", "POST"])
def materials():
    if request.method == "GET":
        return jsonify(Materiales=[item.to_dict() for item in Material.query.order_by(Material.name).all()])
    data = payload()
    item = Material()
    apply_data(item, data, True)
    item.quantity = amount(data.get("quantity", 0), "Existencia inicial")
    db.session.add(item)
    db.session.flush()
    if item.quantity:
        db.session.add(StockMovement(material_id=item.id, user_id=g.user.id_usuario,
                                     kind="entrada", quantity=item.quantity, note="Existencia inicial"))
    db.session.commit()
    return jsonify(message="Material creado", material=item.to_dict()), 201

@materials_bp.route("/<int:identifier>", methods=["GET", "PUT", "DELETE"])
def material(identifier):
    item = existing(Material, identifier)
    if request.method == "GET":
        return jsonify(material=item.to_dict())
    if request.method == "DELETE":
        if StockMovement.query.filter_by(material_id=item.id).first():
            raise Conflict("Este material tiene historial. Desactívalo para conservar sus movimientos.")
        db.session.delete(item)
    else:
        apply_data(item, payload())
    db.session.commit()
    return jsonify(message="Material eliminado" if request.method == "DELETE" else "Material actualizado")

@materials_bp.route("/<int:identifier>/movements", methods=["GET", "POST"])
def movements(identifier):
    item = existing(Material, identifier)
    if request.method == "GET":
        rows = StockMovement.query.filter_by(material_id=item.id).order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).all()
        return jsonify(Movimientos=[row.to_dict() for row in rows])
    data = payload()
    if not item.active:
        raise Conflict("Reactiva el material antes de registrar movimientos")
    kind = data.get("kind")
    if kind not in ("entrada", "salida"):
        raise BadRequest("El movimiento debe ser entrada o salida")
    qty = amount(data.get("quantity"), "Cantidad", True)
    unit = data.get('unit', item.unit)
    if unit == 'l':
        unit = 'L'
    if unit != item.unit:
        if {unit, item.unit} != {'ml', 'L'}:
            raise BadRequest('Solo se puede convertir entre ml y litros; las piezas se registran por separado')
        qty = amount(qty * (Decimal('1000') if unit == 'L' else Decimal('.001')), 'Cantidad convertida', True)
    if item.unit == 'piezas' and qty != qty.to_integral_value():
        raise BadRequest('Las piezas deben ser cantidades enteras')
    note = text(data, "note", 500)
    cost = None
    if data.get("total_cost") is not None:
        cost = amount(data["total_cost"], "Costo total")
        if kind != "entrada" or cost != cost.quantize(Decimal(".01")):
            raise BadRequest("Las compras requieren una entrada y un costo con máximo 2 decimales")
    delta = qty if kind == "entrada" else -qty
    # Atomic conditional update prevents two concurrent withdrawals overspending stock.
    changed = db.session.execute(db.update(Material).where(
        Material.id == item.id, Material.active.is_(True),
        Material.quantity + delta >= 0,
        Material.quantity + delta <= Decimal("999999999.999")
    ).values(quantity=Material.quantity + delta)).rowcount
    if changed != 1:
        raise Conflict("Existencias insuficientes o cantidad fuera de rango")
    movement = StockMovement(material_id=item.id, user_id=g.user.id_usuario,
                             kind=kind, quantity=qty, note=note)
    if cost is not None:
        movement.purchase = MaterialPurchase(total_cost=cost)
    db.session.add(movement)
    db.session.commit()
    return jsonify(message="Movimiento registrado", material=item.to_dict()), 201

