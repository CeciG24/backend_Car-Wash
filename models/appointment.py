from datetime import datetime
from . import db
from .services import VehiculoEnum
import enum

class statusEnum(enum.Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    CANCELED = "Canceled"


# A shared database row serializes changes to the appointment calendar.
db.Table("appointment_write_lock", db.Column("id", db.Integer, primary_key=True))


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
    vehicle_selection = db.relationship("AppointmentVehicle", uselist=False, cascade="all, delete-orphan", lazy="joined")
    extras = db.relationship("AppointmentExtra", cascade="all, delete-orphan", lazy="selectin",
                             order_by="AppointmentExtra.service_id")

    @property
    def vehicle(self):
        if self.vehicle_selection:
            return self.vehicle_selection.vehicle
        return self.service.vehiculo if self.service else None

    @property
    def amount(self):
        base = float(self.pricing.amount) if self.pricing else (self.service.price if self.service else None)
        return base + sum(extra.amount for extra in self.extras) if base is not None else None

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
            "vehiculo": self.vehicle.value if self.vehicle else None,
            "extras": [{"id_servicio": extra.service_id, "nombre": extra.service.name, "precio": extra.amount}
                       for extra in self.extras],
            "amount": self.amount,
            "amount_estimated": self.pricing is None,
        }

    def __repr__(self):
        return f'<Cita {self.id_appointment}>'

class AppointmentPrice(db.Model):
    __tablename__ = 'appointment_prices'
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id_appointment'), primary_key=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)


class AppointmentVehicle(db.Model):
    __tablename__ = 'appointment_vehicles'
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id_appointment'), primary_key=True)
    vehicle = db.Column(db.Enum(VehiculoEnum, name="vehiculo_enum"), nullable=False)


class AppointmentExtra(db.Model):
    __tablename__ = 'appointment_extras'
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id_appointment', ondelete='CASCADE'), primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id_service'), primary_key=True, index=True)
    amount = db.Column(db.Integer, nullable=False)
    service = db.relationship("Services", lazy="joined")
