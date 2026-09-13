from datetime import datetime, timezone
from . import db

class Material(db.Model):
    __tablename__ = "materials"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False)
    unit = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    minimum = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    dilutions = db.Column(db.JSON, nullable=False, default=list)
    notes = db.Column(db.Text, nullable=False, default="")
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "purpose": self.purpose,
                "category": self.category, "unit": self.unit,
                "quantity": float(self.quantity), "minimum": float(self.minimum),
                "dilutions": self.dilutions, "notes": self.notes, "active": self.active,
                "low_stock": self.quantity <= self.minimum}

class StockMovement(db.Model):
    __tablename__ = "stock_movements"
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id_usuario"), nullable=False)
    kind = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    note = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    user = db.relationship("User")
    purchase = db.relationship("MaterialPurchase", uselist=False, cascade="all, delete-orphan", lazy="joined")

    def to_dict(self):
        return {"id": self.id, "kind": self.kind, "quantity": float(self.quantity),
                "note": self.note, "created_at": self.created_at.isoformat() + "Z",
                "user": self.user.nombre,
                "total_cost": float(self.purchase.total_cost) if self.purchase else None}

class MaterialPurchase(db.Model):
    __tablename__ = "material_purchases"
    movement_id = db.Column(db.Integer, db.ForeignKey("stock_movements.id"), primary_key=True)
    total_cost = db.Column(db.Numeric(12, 2), nullable=False)

