import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Barrier
from unittest.mock import patch
import bcrypt
from app import create_app
from models import db
from models.user import User
from models.appointment import Appointments
from models.services import Services, TipoEnum
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

    def test_slot_conflict_and_release_in_admin_edits(self):
        start = (datetime.now(timezone.utc) + timedelta(days=3)).replace(second=0, microsecond=0)
        booking = {**self.booking(), "scheduled_date": start.isoformat()}
        first = self.client.post("/appointments", json=booking).json["id_appointment"]
        first_url = f"/appointments/{first}"
        same_minute = (start + timedelta(seconds=30)).astimezone(timezone(timedelta(hours=-6)))
        conflict = self.client.post("/appointments", json={**booking, "scheduled_date": same_minute.isoformat()})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json["code"], "appointment_slot_taken")

        next_slot = (start + timedelta(hours=1)).isoformat()
        second = self.client.post("/appointments", json={**booking, "scheduled_date": next_slot}).json["id_appointment"]
        conflict = self.client.put(first_url, headers=self.headers,
                                   json={"scheduled_date": next_slot, "id_service": self.service_id})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(self.client.put(first_url, headers=self.headers, json={"status": "Canceled"}).status_code, 200)
        replacement = self.client.post("/appointments", json=booking)
        self.assertEqual(replacement.status_code, 201)
        self.assertEqual(self.client.put(first_url, headers=self.headers, json={"status": "Pending"}).status_code, 409)

        second_url = f"/appointments/{second}"
        self.assertEqual(self.client.delete(second_url, headers=self.headers).status_code, 200)
        reopened = self.client.put(first_url, headers=self.headers,
                                   json={"status": "Pending", "scheduled_date": next_slot, "id_service": self.service_id})
        self.assertEqual(reopened.status_code, 200)

    def test_booking_sends_receipt_and_records_vehicle_for_shared_service(self):
        service = self.client.post("/services", headers=self.headers,
                                   json={"name": "Lavado general", "price": 200, "tipo": "BASICO"}).json
        with mail.record_messages() as outbox:
            response = self.client.post("/appointments", json={
                **self.booking(), "id_service": service["id_service"],
                "vehiculo": "Moto", "email": "cliente@example.test",
            })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json["confirmation_email_sent"])
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0].recipients, ["cliente@example.test"])
        identifier = response.json["id_appointment"]
        self.assertIn(f"Folio: {identifier}", outbox[0].body)
        self.assertIn("Vehículo: Moto", outbox[0].body)
        row = self.client.get(f"/appointments/{identifier}", headers=self.headers).json
        self.assertEqual(row["vehiculo"], "Moto")
        self.assertEqual(row["status"], "Pending")

    def test_invalid_vehicle_or_email_does_not_create_a_booking(self):
        for update in ({"vehiculo": "Moto"}, {"email": "cliente@example.test, otro@example.test"}):
            response = self.client.post("/appointments", json={**self.booking(), **update})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Appointments.query.count(), 0)

    def test_booking_remains_saved_if_receipt_cannot_be_sent(self):
        with patch.object(mail, "send", side_effect=OSError):
            response = self.client.post("/appointments", json={
                **self.booking(), "vehiculo": "SUV Grande", "email": "cliente@example.test",
            })
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json["confirmation_email_sent"])
        self.assertIsNotNone(db.session.get(Appointments, response.json["id_appointment"]))

    def test_service_validation_and_recovery(self):
        for update in ({"price": -1}, {"price": 1.5}, {"tipo": "bad"}, {"vehiculo": "bad"}, {"name": ""}):
            response = self.client.put(f"/services/{self.service_id}", json=update, headers=self.headers)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(f"/services/{self.service_id}").json["Servicio"]["precio"], 200)
        self.assertEqual(self.client.get("/services/999").status_code, 404)

    def test_service_duration_and_category_with_optional_package(self):
        response = self.client.post("/services", headers=self.headers, json={
            "name": "Pulido", "price": 600, "categoria": "Pulido y corrección", "duracion_minutos": 90,
        })
        self.assertEqual(response.status_code, 201)
        item = response.json["service"]
        self.assertEqual(item["categoria"], "Pulido y corrección")
        self.assertEqual(item["duracion_minutos"], 90)
        self.assertIsNone(item["tipo"])

        path = f"/services/{self.service_id}"
        response = self.client.put(path, headers=self.headers, json={"duracion_minutos": 45})
        self.assertEqual(response.status_code, 200)
        item = self.client.get(path).json["Servicio"]
        self.assertEqual((item["tipo"], item["duracion_minutos"]), ("Premium", 45))

        for changes in ({"duracion_minutos": 0}, {"duracion_minutos": -1},
                        {"duracion_minutos": 1.5}, {"categoria": "sin registrar"}):
            self.assertEqual(self.client.put(path, headers=self.headers, json=changes).status_code, 400)
        response = self.client.put(path, headers=self.headers, json={"tipo": "", "duracion_minutos": None})
        self.assertEqual(response.status_code, 200)
        item = self.client.get(path).json["Servicio"]
        self.assertIsNone(item["tipo"])
        self.assertIsNone(item["duracion_minutos"])

    def test_booking_saves_multiple_extras_and_their_prices(self):
        self.client.put(f"/services/{self.service_id}", headers=self.headers, json={"tipo": "Extra"})
        extras = [
            self.client.post("/services", headers=self.headers, json={
                "name": name, "price": price, "es_extra": True, "vehiculo": vehicle,
            }).json["id_service"]
            for name, price, vehicle in (("Pulido de faros", 75, "SUV Grande"), ("Encerado", 50, None))
        ]
        with mail.record_messages() as outbox:
            response = self.client.post("/appointments", json={
                **self.booking(), "vehiculo": "SUV Grande", "ids_extras": extras,
                "email": "cliente@example.test",
            })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Extras: Pulido de faros, Encerado", outbox[0].body)
        path = f"/appointments/{response.json['id_appointment']}"
        self.client.put(f"/services/{extras[0]}", headers=self.headers, json={"price": 100})
        self.assertEqual(self.client.put(path, headers=self.headers, json={"status": "Completed"}).status_code, 200)
        row = self.client.get(path, headers=self.headers).json
        self.assertEqual(row["id_service"], self.service_id)
        self.assertEqual([item["id_servicio"] for item in row["extras"]], extras)
        self.assertEqual([item["precio"] for item in row["extras"]], [75, 50])
        self.assertEqual(row["amount"], 325)
        monthly = self.client.get("/charts/monthly-revenue", headers=self.headers).json
        self.assertEqual(sum(monthly.values()), 325)
        self.assertEqual(self.client.delete(f"/services/{extras[0]}", headers=self.headers).status_code, 409)
        self.assertEqual(self.client.delete(path, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.delete(f"/services/{extras[0]}", headers=self.headers).status_code, 200)

    def test_invalid_extras_leave_the_calendar_free(self):
        extra = self.client.post("/services", headers=self.headers, json={
            "name": "Faros", "price": 75, "es_extra": True, "vehiculo": "Auto",
        }).json["id_service"]
        booking = self.booking()
        for changes in ({"ids_extras": [self.service_id]}, {"ids_extras": [extra]},
                        {"ids_extras": [extra, extra]}, {"ids_extras": str(extra)},
                        {"id_service": extra}):
            self.assertEqual(self.client.post("/appointments", json={**booking, **changes}).status_code, 400)
        self.assertEqual(Appointments.query.count(), 0)
        self.assertEqual(self.client.post("/appointments", json=booking).status_code, 201)

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

class ConcurrentBookingTests(unittest.TestCase):
    def test_only_one_request_claims_the_last_slot(self):
        # A file-backed database lets both requests use separate connections.
        with NamedTemporaryFile(dir=Path(__file__).resolve().parents[1], suffix=".sqlite3", delete=False) as temp:
            database = Path(temp.name)
        self.addCleanup(database.unlink)
        app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + database.as_posix(),
                          "MAIL_SUPPRESS_SEND": True})
        with app.app_context():
            self.addCleanup(db.engine.dispose)
            service = Services(name="Lavado", price=200, tipo=TipoEnum.BASICO)
            db.session.add(service)
            db.session.commit()
            service_id = service.id_service
        start = Barrier(2)
        date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

        def book(number):
            with app.test_client() as client:
                start.wait(timeout=5)
                return client.post("/appointments", json={
                    "name": f"Cliente {number}", "numero_whatsapp": "2221234567",
                    "direccion": "Calle 1", "scheduled_date": date,
                    "id_service": service_id, "email": f"cliente{number}@example.test",
                })

        with patch("routes.appointments.send_confirmation", return_value=True) as send_confirmation:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(book, (1, 2)))
            send_confirmation.assert_called_once()
        self.assertCountEqual([result.status_code for result in results], [201, 409])
        with app.app_context():
            self.assertEqual(Appointments.query.count(), 1)


if __name__ == "__main__":
    unittest.main()

