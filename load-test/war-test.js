import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom Metrics untuk memantau hasil War Tiket
const ticketsReserved = new Counter('tickets_reserved_202');
const ticketsSoldOut  = new Counter('tickets_sold_out_400');
const reserveDuration = new Trend('reserve_response_time_ms');
const successRate     = new Rate('reserve_success_rate');

// Beritahu k6 bahwa status 200, 202, dan 400 (Sold Out) adalah respon HTTP yang diharapkan
http.setResponseCallback(http.expectedStatuses(200, 201, 202, 400));

// ── Skenario Beban Bertahap (1 s/d 500 Virtual Users) ─────────────
export const options = {
  stages: [
    { duration: '10s', target: 50 },   // Tahap 1: Ramp-up dari 1 ke 50 VUs (Pemanasan)
    { duration: '20s', target: 200 },  // Tahap 2: Naik ke 200 VUs (Mulai ramai)
    { duration: '30s', target: 500 },  // Tahap 3: Puncak War Tiket ke 500 VUs!
    { duration: '20s', target: 500 },  // Tahap 4: Tahan di 500 VUs bersamaan
    { duration: '10s', target: 0 },    // Tahap 5: Ramp-down kembali ke 0
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],    // Kegagalan teknis (5xx) harus di bawah 5%
    http_req_duration: ['p(95)<3000'], // 95% request harus selesai di bawah 3 detik di laptop lokal
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8080/api/v1';

// Setup: Login 1 kali untuk mendapatkan JWT Token customer
export function setup() {
  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ username: 'johndoe', password: 'user123' }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(loginRes, {
    'Login seed user berhasil': (r) => r.status === 200,
  });

  const token = loginRes.json('token');
  return { token };
}

// Virtual User Execution Loop
export default function (data) {
  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${data.token}`,
  };

  const payload = JSON.stringify({
    category_id: 1, // Kategori CAT 1
    quantity: 1,
  });

  const startTime = Date.now();
  const res = http.post(`${BASE_URL}/orders/reserve`, payload, { headers });
  reserveDuration.add(Date.now() - startTime);

  // Analisa Respon Bisnis
  if (res.status === 202) {
    // Berhasil masuk antrean tiket (tiket masih ada)
    ticketsReserved.add(1);
    successRate.add(true);
  } else if (res.status === 400) {
    // Sold out terdeteksi secara atomic oleh Redis
    ticketsSoldOut.add(1);
    successRate.add(true);
  } else {
    // Error tidak diharapkan (500, 502 Bad Gateway Nginx, dll.)
    successRate.add(false);
  }

  check(res, {
    'Status 202 (Accepted) atau 400 (Sold Out)': (r) => r.status === 202 || r.status === 400,
  });

  // Jeda acak antar aksi klik pengguna nyata (100ms - 500ms)
  sleep(Math.random() * 0.4 + 0.1);
}
