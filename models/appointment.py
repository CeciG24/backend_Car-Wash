from datetime import datetime
from . import db

class Appointments(db.Model):
    __tablename__ = 'Appointments'
    
    id_appointment = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name=db.Column(db.String(100), nullable=False)
    num_whatsapp=db.Column(db.String(100), nullable=False)
    direccion=db.Column(db.String(100), nullable=False)

    id_service = db.Column(db.Integer, db.ForeignKey("Services.id_service"), nullable=True)

    # Relación opcional si existe la tabla 'preferencias'
    service = db.relationship('Service', back_populates='Appontments', lazy=True, uselist=False)

    def __repr__(self):
        return f'<Cita {self.id_appointment}>'