from . import db
class ServiceDescription(db.Model):
    __tablename__ = 'service_descriptions'
    
    id_description = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id_service'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)  # Para ordenar los puntos
    
    service = db.relationship("Services", back_populates="descriptions")

    def __repr__(self):
        return f'<Service {self.id_description}>'