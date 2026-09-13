import unittest
import test_api as base
from models import db
from models.appointment import Appointments

class IncomePurchaseTests(unittest.TestCase):
    setUp = base.ApiTests.setUp
    tearDown = base.ApiTests.tearDown
    booking = base.ApiTests.booking

    def test_price_survives_service_price_changes(self):
        response = self.client.post('/appointments', json=self.booking())
        identifier = response.json['id_appointment']
        self.client.put(f'/services/{self.service_id}', headers=self.headers, json={'price': 500})
        self.client.put(f'/appointments/{identifier}', headers=self.headers,
                        json={'status': 'Completed', 'id_service': self.service_id})
        row = self.client.get(f'/appointments/{identifier}', headers=self.headers).json
        self.assertEqual(row['amount'], 200)
        self.assertFalse(row['amount_estimated'])
        item = db.session.get(Appointments, identifier)
        item.pricing = None
        db.session.commit()
        row = self.client.get(f'/appointments/{identifier}', headers=self.headers).json
        self.assertTrue(row['amount_estimated'])
        self.assertEqual(row['amount'], 500)

    def test_purchase_cost_and_validation_rollback(self):
        response = self.client.post('/materials', headers=self.headers, json={
            'name': 'APC prueba', 'purpose': 'Prueba', 'category': 'Químico', 'unit': 'L', 'quantity': 0})
        identifier = response.json['material']['id']
        path = f'/materials/{identifier}/movements'
        response = self.client.post(path, headers=self.headers,
            json={'kind': 'entrada', 'quantity': 1, 'note': 'Compra litro APC', 'total_cost': 100})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['material']['quantity'], 1)
        history = self.client.get(path, headers=self.headers).json['Movimientos']
        self.assertEqual(history[0]['total_cost'], 100)
        self.assertEqual(self.client.get('/materials/purchases-summary', headers=self.headers).json['Resumen'][0]['total'], 100)
        self.assertEqual(self.client.get('/materials/purchases-summary').status_code, 401)
        response = self.client.post(path, headers=self.headers,
            json={'kind': 'entrada', 'quantity': 500, 'unit': 'ml', 'note': 'Medio litro'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['material']['quantity'], 1.5)
        for cost in (-1, True, 'NaN', 1.234):
            response = self.client.post(path, headers=self.headers,
                json={'kind': 'entrada', 'quantity': 1, 'note': 'Inválido', 'total_cost': cost})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(path, headers=self.headers,
            json={'kind': 'salida', 'quantity': 1, 'note': 'Inválido', 'total_cost': 20}).status_code, 400)
        self.assertEqual(self.client.get(f'/materials/{identifier}', headers=self.headers).json['material']['quantity'], 1.5)
