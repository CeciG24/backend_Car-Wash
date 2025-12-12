from datetime import datetime
from . import db

class Appointments(db.Model):
    __tablename__ = 'appointments'
    
    id_appointment = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name=db.Column(db.String(100), nullable=False)
    num_whatsapp=db.Column(db.String(100), nullable=False)
    direccion=db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_date =db.Column(db.DateTime, nullable=False)

    id_service = db.Column(db.Integer, db.ForeignKey("services.id_service"), nullable=True)
    service = db.relationship("Services", back_populates="appointments")

    def __repr__(self):
        return f'<Cita {self.id_appointment}>'