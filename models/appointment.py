from datetime import datetime
from . import db
import enum

class statusEnum(enum.Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    CANCELED = "Canceled"

class Appointments(db.Model):
    __tablename__ = 'appointments'

    id_appointment = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name=db.Column(db.String(100), nullable=False)
    num_whatsapp=db.Column(db.String(100), nullable=False)
    direccion=db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_date =db.Column(db.DateTime, nullable=False)
    status=db.Column(db.Enum(statusEnum), nullable=False, default=statusEnum.PENDING)

    id_service = db.Column(db.Integer, db.ForeignKey("services.id_service"), nullable=True)
    service = db.relationship("Services", back_populates="appointments")
    pricing = db.relationship("AppointmentPrice", uselist=False, cascade="all, delete-orphan", lazy="joined")

    def to_dict(self):
        return {
            "id_appointment": self.id_appointment,
            "name": self.name,
            "numero_whatsapp": self.num_whatsapp,
            "direccion": self.direccion,
            "scheduled_date": self.scheduled_date.isoformat() + "Z",
            "fecha_creacion": self.fecha_creacion.isoformat() + "Z",
            "status": self.status.value,
            "id_service": self.id_service,
            "servicio": self.service.name if self.service else None,
            "amount": float(self.pricing.amount) if self.pricing else (self.service.price if self.service else None),
            "amount_estimated": self.pricing is None,
        }

    def __repr__(self):
        return f'<Cita {self.id_appointment}>'

class AppointmentPrice(db.Model):
    __tablename__ = 'appointment_prices'
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id_appointment'), primary_key=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
