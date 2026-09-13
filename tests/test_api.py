import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import bcrypt
from app import create_app
from models import db
from models.user import User
from models.appointment import Appointments
from extensions import mail

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "isolated-test-secret-not-for-production",
            "ADMIN_EMAILS": {"owner@example.test"}, "MAIL_SUPPRESS_SEND": True,
            "MAIL_DEFAULT_SENDER": "test@example.test", "CONTACT_EMAIL": "owner@example.test"
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.session.add(User(nombre="Owner", email="owner@example.test",
                            contraseña_hash=bcrypt.hashpw(b"password123", bcrypt.gensalt(rounds=4)).decode()))
        db.session.commit()
        self.client = self.app.test_client()
        response = self.client.post("/login", json={"email": "owner@example.test", "contraseña": "password123"})
        self.assertEqual(response.status_code, 200)
        self.headers = {"Authorization": "Bearer " + response.json["token"]}
        response = self.client.post("/services", json={"name": "Lavado", "price": 200, "tipo": "PREMIUM", "vehiculo": "SUV Grande"}, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        self.service_id = response.json["id_service"]

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def booking(self):
        return {"name": "Cliente", "numero_whatsapp": "2221234567", "direccion": "Calle 1",
                "scheduled_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                "id_service": self.service_id}

    def test_service_crud_and_descriptions(self):
        for path in ("/services", "/services/"):
            self.assertEqual(self.client.get(path).status_code, 200)
        result = self.client.get(f"/services/{self.service_id}").json["Servicio"]
        self.assertEqual(result["vehiculo"], "SUV Grande")
        for order, desc in ((2, "Segundo"), (1, "Primero")):
            response = self.client.post("/services/descriptions", headers=self.headers,
                                        json={"service_id": self.service_id, "description": desc, "order": order})
            self.assertEqual(response.status_code, 201)
        response = self.client.get(f"/services/descriptions/{self.service_id}")
        self.assertEqual(response.json["Descripcion"]["descripcion"], "Primero\nSegundo")
        response = self.client.put(f"/services/{self.service_id}", headers=self.headers,
                                   json={"tipo": "Basico", "vehiculo": "AUTO", "price": 300})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.delete(f"/services/{self.service_id}", headers=self.headers).status_code, 200)

    def test_private_endpoints(self):
        for method, path in (("get", "/appointments"), ("get", "/charts/appointments-status"),
                             ("post", "/services"), ("put", "/services/1"),
                             ("delete", "/reviews/1"), ("post", "/portfolio"), ("post", "/register")):
            self.assertEqual(getattr(self.client, method)(path, json={}).status_code, 401)
        self.assertEqual(self.client.get("/user/me", headers=self.headers).json["rol"], "admin")
        self.assertEqual(self.client.get("/appointments", headers={"Authorization": "Bearer forged"}).status_code, 401)

    def test_expired_and_removed_admin(self):
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=1):
            token = self.client.post("/login", json={"email": "owner@example.test", "contraseña": "password123"}).json["token"]
        self.assertEqual(self.client.get("/appointments", headers={"Authorization": "Bearer " + token}).status_code, 401)
        self.app.config["ADMIN_EMAILS"] = set()
        self.assertEqual(self.client.get("/appointments", headers=self.headers).status_code, 403)

    def test_appointments_crud_and_charts(self):
        response = self.client.post("/appointments", json=self.booking())
        self.assertEqual(response.status_code, 201)
        identifier = response.json["id_appointment"]
        rows = self.client.get("/appointments/", headers=self.headers).json
        self.assertEqual(rows[0]["status"], "Pending")
        self.assertTrue(rows[0]["scheduled_date"].endswith("Z"))
        self.assertEqual(self.client.get("/charts/pending-appointments", headers=self.headers).status_code, 200)
        response = self.client.put(f"/appointments/{identifier}", headers=self.headers,
                                   json={"name": "Actualizado", "status": "COMPLETED"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(f"/appointments/{identifier}", headers=self.headers).json["name"], "Actualizado")
        self.assertEqual(self.client.delete(f"/services/{self.service_id}", headers=self.headers).status_code, 409)
        self.assertEqual(self.client.delete(f"/appointments/{identifier}", headers=self.headers).status_code, 200)

    def test_invalid_bookings_leave_no_rows(self):
        for update in ({"scheduled_date": "2020-01-01T00:00:00Z"}, {"scheduled_date": "bad"},
                       {"name": " "}, {"id_service": None}, {"id_service": 999}):
            result = self.client.post("/appointments", json={**self.booking(), **update})
            self.assertIn(result.status_code, (400, 404))
        self.assertEqual(Appointments.query.count(), 0)

    def test_service_validation_and_recovery(self):
        for update in ({"price": -1}, {"price": 1.5}, {"tipo": "bad"}, {"vehiculo": "bad"}, {"name": ""}):
            response = self.client.put(f"/services/{self.service_id}", json=update, headers=self.headers)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(f"/services/{self.service_id}").json["Servicio"]["precio"], 200)
        self.assertEqual(self.client.get("/services/999").status_code, 404)

    def test_portfolio_crud(self):
        response = self.client.post("/portfolio/", headers=self.headers, json={
            "car_model": "Jetta", "service_id": self.service_id,
            "video_url": "https://www.tiktok.com/@example/video/123456789", "description": "Resultado",
            "date": "2026-01-02T12:00:00-06:00"})
        self.assertEqual(response.status_code, 201)
        identifier = response.json["id"]
        item = self.client.get("/portfolio").json["Servicios"][0]
        self.assertEqual(item["id_servicio"], identifier)
        self.assertEqual(item["servicio"], "Lavado")
        self.assertEqual(item["fecha"], "2026-01-02T18:00:00Z")
        self.assertEqual(self.client.put(f"/portfolio/{identifier}", headers=self.headers, json={"video_url": "javascript:alert(1)"}).status_code, 400)
        self.assertEqual(self.client.put(f"/portfolio/{identifier}", headers=self.headers, json={"car_model": "Golf"}).status_code, 200)
        self.assertEqual(self.client.delete(f"/portfolio/{identifier}", headers=self.headers).status_code, 200)

    def test_reviews(self):
        self.assertEqual(self.client.post("/reviews", json={"nombre_cliente": "A", "comentario": "Bien", "calificacion": 6}).status_code, 400)
        self.assertEqual(self.client.post("/reviews/", json={"nombre_cliente": "A", "comentario": "Bien", "calificacion": 5}).status_code, 201)
        identifier = self.client.get("/reviews").json["Reseñas"][0]["id"]
        self.assertEqual(self.client.put(f"/reviews/{identifier}", headers=self.headers, json={"calificacion": 4}).status_code, 200)
        self.assertEqual(self.client.delete(f"/reviews/{identifier}", headers=self.headers).status_code, 200)

    def test_contact_mail_and_missing_configuration(self):
        with mail.record_messages() as outbox:
            response = self.client.post("/contacts", json={"nombre": "Cliente", "numero": "222", "detalles": "Consulta"})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(len(outbox), 1)
        self.app.config["CONTACT_EMAIL"] = None
        self.assertEqual(self.client.post("/contacts", json={"nombre": "A", "numero": "1", "detalles": "Hola"}).status_code, 503)

    def test_bad_json_and_auth(self):
        self.assertEqual(self.client.post("/reviews", json=[]).status_code, 400)
        self.assertEqual(self.client.post("/reviews", data="{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/login", json={"email": "owner@example.test", "contraseña": "wrong"}).status_code, 401)
        self.assertEqual(self.client.post("/register", headers=self.headers, json={"nombre": "Owner", "email": "owner@example.test", "contraseña": "password123"}).status_code, 409)

if __name__ == "__main__":
    unittest.main()

