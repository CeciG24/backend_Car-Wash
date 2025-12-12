from . import db
from datetime import datetime

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_cliente = db.Column(db.String(100), nullable=False)
    comentario = db.Column(db.Text, nullable=False)
    calificacion = db.Column(db.Integer, default=5)  # 1 a 5 estrellas
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def to_json(self):
        return {
            "id": self.id,
            "nombre_cliente": self.nombre_cliente,
            "comentario": self.comentario,
            "calificacion": self.calificacion,
            "fecha": self.fecha.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def __repr__(self):
        return f"<Review {self.id} - {self.nombre_cliente}>"