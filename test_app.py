import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure main is importable
sys.path.insert(0, os.path.dirname(__file__))
from main import app, get_db

class TestSecretSantaPermanent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_static_and_root(self):
        """Test root serves index.html and static files exist."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Christmas Chris", res.text)

    def test_02_dynamic_signup_with_special_characters(self):
        """Test signup with passwords containing special characters like Anu@2346, Test@123, my#pass$."""
        users_to_test = [
            ("Anu_User", "Anu@2346"),
            ("Chris_Host", "Test@123!"),
            ("Rudolph_Deer", "my#pass$2026%^&*"),
            ("Santa_Claus", "HoHoHo@Secret#99")
        ]
        for username, password in users_to_test:
            res = self.client.post("/api/auth/signup", json={"username": username, "password": password})
            self.assertIn(res.status_code, [200, 400]) # 400 if already exists, else 200
            if res.status_code == 200:
                data = res.json()
                self.assertIn("token", data)
                self.assertEqual(data["user"]["username"], username)

    def test_03_login_with_special_characters(self):
        """Test login with special character passwords."""
        res = self.client.post("/api/auth/login", json={"username": "Anu_User", "password": "Anu@2346"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("token", data)
        self.token_anu = data["token"]

        # Wrong password should fail
        res_fail = self.client.post("/api/auth/login", json={"username": "Anu_User", "password": "WrongPassword@123"})
        self.assertEqual(res_fail.status_code, 400)

    def test_04_create_and_join_group_workflow(self):
        """Test full group workflow: create group, join via code, update wishlist, shuffle."""
        # 1. Login user 1 (Chris_Host)
        res1 = self.client.post("/api/auth/login", json={"username": "Chris_Host", "password": "Test@123!"})
        token_chris = res1.json()["token"]
        headers_chris = {"Authorization": f"Bearer {token_chris}"}

        # 2. Login user 2 (Anu_User)
        res2 = self.client.post("/api/auth/login", json={"username": "Anu_User", "password": "Anu@2346"})
        token_anu = res2.json()["token"]
        headers_anu = {"Authorization": f"Bearer {token_anu}"}

        # 3. Login user 3 (Rudolph_Deer)
        res3 = self.client.post("/api/auth/login", json={"username": "Rudolph_Deer", "password": "my#pass$2026%^&*"})
        token_rudolph = res3.json()["token"]
        headers_rudolph = {"Authorization": f"Bearer {token_rudolph}"}

        # Chris creates a group
        create_res = self.client.post("/api/groups/create", json={"name": "North Pole Elves 2026"}, headers=headers_chris)
        self.assertEqual(create_res.status_code, 200)
        group_data = create_res.json()["group"]
        group_id = group_data["id"]
        group_code = group_data["code"]
        self.assertTrue(len(group_code) >= 6)

        # Anu joins using group_code
        join_res_anu = self.client.post("/api/groups/join", json={"code": group_code}, headers=headers_anu)
        self.assertEqual(join_res_anu.status_code, 200)

        # Rudolph joins using group_code
        join_res_rudolph = self.client.post("/api/groups/join", json={"code": group_code}, headers=headers_rudolph)
        self.assertEqual(join_res_rudolph.status_code, 200)

        # Update wishlists
        self.client.put(f"/api/groups/{group_id}/wishlist", json={"wishlist": "1. Wool scarf\n2. Gingerbread cookies"}, headers=headers_chris)
        self.client.put(f"/api/groups/{group_id}/wishlist", json={"wishlist": "1. Ceramic Santa mug\n2. Scented candles"}, headers=headers_anu)
        self.client.put(f"/api/groups/{group_id}/wishlist", json={"wishlist": "1. Carrots\n2. Shiny jingle bells"}, headers=headers_rudolph)

        # Trigger Secret Santa shuffle
        shuffle_res = self.client.post(f"/api/groups/{group_id}/shuffle", headers=headers_chris)
        self.assertEqual(shuffle_res.status_code, 200)
        self.assertTrue(shuffle_res.json()["is_shuffled"])

        # Check each user's assignment
        details_chris = self.client.get(f"/api/groups/{group_id}", headers=headers_chris).json()
        details_anu = self.client.get(f"/api/groups/{group_id}", headers=headers_anu).json()
        details_rudolph = self.client.get(f"/api/groups/{group_id}", headers=headers_rudolph).json()

        rec_chris = details_chris["assignment"]["recipient_username"]
        rec_anu = details_anu["assignment"]["recipient_username"]
        rec_rudolph = details_rudolph["assignment"]["recipient_username"]

        # Ensure NO self-assignment (Derangement rule)
        self.assertNotEqual(rec_chris, "Chris_Host")
        self.assertNotEqual(rec_anu, "Anu_User")
        self.assertNotEqual(rec_rudolph, "Rudolph_Deer")

        # Ensure all 3 are assigned distinct recipients
        assigned_recipients = {rec_chris, rec_anu, rec_rudolph}
        self.assertEqual(assigned_recipients, {"Chris_Host", "Anu_User", "Rudolph_Deer"})

        # Ensure recipient's wishlist is visible to their Secret Santa
        self.assertTrue(len(details_chris["assignment"]["recipient_wishlist"]) > 0)

        print("\nAll Secret Santa integration tests passed successfully!")
        print(f"Assignment pairing: Chris -> {rec_chris}, Anu -> {rec_anu}, Rudolph -> {rec_rudolph}")

if __name__ == "__main__":
    unittest.main()
