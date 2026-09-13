import unittest
import test_api as base
from models.material import Material, StockMovement

class MaterialTests(unittest.TestCase):
    setUp = base.ApiTests.setUp
    tearDown = base.ApiTests.tearDown
    def material(self, **updates):
        response = self.client.post("/materials", headers=self.headers, json={
            "name": "Producto de prueba", "purpose": "Uso de prueba", "category": "Químico",
            "unit": "ml", "quantity": 1000, "minimum": 200,
            "dilutions": [{"use": "Prueba", "product": 1, "water": 9, "instructions": "Dato de prueba"}],
            **updates})
        self.assertEqual(response.status_code, 201)
        return response.json["material"]["id"]

    def test_inventory_authorization(self):
        self.assertEqual(self.client.get("/materials").status_code, 401)
        self.assertEqual(self.client.post("/materials", json={}).status_code, 401)

    def test_stock_movements_and_insufficient_stock(self):
        identifier = self.material()
        response = self.client.post(f"/materials/{identifier}/movements", headers=self.headers,
                                    json={"kind": "salida", "quantity": 850, "note": "Consumo"})
        self.assertEqual(response.status_code, 201)
        item = self.client.get(f"/materials/{identifier}", headers=self.headers).json["material"]
        self.assertEqual(item["quantity"], 150)
        self.assertTrue(item["low_stock"])
        response = self.client.post(f"/materials/{identifier}/movements", headers=self.headers,
                                    json={"kind": "salida", "quantity": 200, "note": "Exceso"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(f"/materials/{identifier}/movements", headers=self.headers).json["Movimientos"].__len__(), 2)
        self.assertEqual(self.client.get(f"/materials/{identifier}", headers=self.headers).json["material"]["quantity"], 150)
        self.assertEqual(self.client.delete(f"/materials/{identifier}", headers=self.headers).status_code, 409)
        self.assertEqual(self.client.put(f"/materials/{identifier}", headers=self.headers, json={"unit": "L"}).status_code, 409)

    def test_material_update_archive_delete(self):
        identifier = self.material(quantity=0)
        self.assertEqual(self.client.put(f"/materials/{identifier}", headers=self.headers,
                                        json={"purpose": "Otro uso", "active": False}).status_code, 200)
        self.assertEqual(self.client.post(f"/materials/{identifier}/movements", headers=self.headers,
                                         json={"kind": "entrada", "quantity": 10, "note": "Compra"}).status_code, 409)
        self.assertEqual(self.client.put(f"/materials/{identifier}", headers=self.headers, json={"quantity": 200}).status_code, 400)
        self.assertEqual(self.client.delete(f"/materials/{identifier}", headers=self.headers).status_code, 200)
        self.assertEqual(Material.query.count(), 0)
        self.assertEqual(StockMovement.query.count(), 0)

    def test_invalid_amount_and_dilution(self):
        for update in ({"quantity": -1}, {"quantity": "NaN"}, {"quantity": .0001}, {"minimum": True},
                       {"dilutions": [{"use": "A", "product": 0, "water": 1}]},
                       {"dilutions": [{"use": "A", "product": 1, "water": -1}]},
                       {"unit": "litros"}):
            response = self.client.post("/materials", headers=self.headers, json={
                "name": "Test", "purpose": "Test", "category": "Químico", "unit": "ml",
                "quantity": 0, "minimum": 0, **update})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Material.query.count(), 0)


