"""
TicketWar – Locust Load Testing Script
Gradual Ramp-Up from 1 to 500 Users with Web UI.

Run with:
    pip install locust
    locust -f load-test/locustfile.py --host=http://localhost:8080
Then open: http://localhost:8089 in your browser.
"""

from locust import HttpUser, task, between, events


class TicketWarCustomer(HttpUser):
    wait_time = between(0.1, 0.5)  # Delay klik pengguna (100ms - 500ms)
    token = None

    def on_start(self):
        """Dijalankan saat Virtual User pertama kali spawn (Login)."""
        res = self.client.post(
            "/api/v1/auth/login",
            json={"username": "johndoe", "password": "user123"},
            name="[Auth] Login",
        )
        if res.status_code == 200:
            self.token = res.json().get("token")

    @task
    def war_ticket(self):
        """Simulasi klik tombol 'AMBIL TIKET SEKARANG'."""
        if not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"category_id": 1, "quantity": 1}

        with self.client.post(
            "/api/v1/orders/reserve",
            json=payload,
            headers=headers,
            catch_response=True,
            name="[War] Reserve Ticket",
        ) as response:
            # 202 Accepted (berhasil dapat tiket) & 400 Bad Request (Sold out) adalah respon valid
            if response.status_code == 202:
                response.success()
            elif response.status_code == 400:
                response.success()  # Sold out bukan error server
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
