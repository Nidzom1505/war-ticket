# TicketWar: PRD Aplikasi & Vibe Coding Playbook (Antigravity Edition)

Dokumen ini memuat dua bagian:
1. **Bagian I: PRD Khusus Pengembangan Aplikasi (Core Features Only)**
2. **Bagian II: Panduan Interaktif Prompt per Langkah di Antigravity**

---

# BAGIAN I: PRD PENGEMBANGAN APLIKASI TICKETWAR

## 1. Ringkasan & Arsitektur Aplikasi
Sistem pemesanan tiket konser dengan arsitektur non-blocking terdistribusi yang dirancang untuk mencegah kemacetan database (*connection exhaustion*) dan penjualan kursi ganda (*race condition*).

* **Frontend (FE)**: Vue 3 (Composition API `<script setup>`), Vite, Pinia, Tailwind CSS.
* **Gateway / Ingress**: Nginx (Port host `8080` -> internal port `80`).
* **Ingestion API (BE)**: Python (Flask), PyJWT, Redis Client, Psycopg2.
* **In-Memory Buffer & Lock**: Redis 7 Alpine (`order_queue`, atomic decrement, distributed seat lock).
* **Worker Daemon**: Python Worker Pool (asynchronous order processor ke DB).
* **Database Persisten**: PostgreSQL 16 Alpine.

---

## 2. Struktur Direktori Proyek
```text
ticketwar/
├── docs/
│   └── PRD.md
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── api/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── routes.py
│   │   └── db.py
│   ├── requirements.txt
│   └── Dockerfile
├── worker/
│   ├── worker.py
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── default.conf
├── postgres/
│   └── init.sql
├── docker-compose.yml
└── .env
```

---

## 3. Skema Basis Data Relasional (PostgreSQL 16)
1. **`users`**: `id` (PK), `username`, `email`, `password_hash`, `role` (`customer`, `eo`, `admin`), `is_active`, `created_at`.
2. **`concerts`**: `id` (PK), `organizer_id` (FK `users.id`), `title`, `artist`, `venue`, `concert_date`, `status`.
3. **`ticket_categories`**: `id` (PK), `concert_id` (FK `concerts.id`), `category_name`, `price`, `total_quota`, `available_quota`.
4. **`orders`**: `id` (PK), `invoice_number` (Unique), `user_id` (FK `users.id`), `category_id` (FK `ticket_categories.id`), `quantity`, `total_amount`, `payment_status` (`pending`, `paid`, `failed`), `created_at`.
5. **`tickets`**: `id` (PK), `order_id` (FK `orders.id`), `seat_number`, `ticket_code` (Unique), `is_used`, `is_deleted` (default `false`), `issued_at`.
6. **`audit_logs`**: `id` (PK), `user_id` (FK `users.id`), `action`, `table_name`, `record_id`, `ip_address`, `created_at`.

---

## 4. Alur Kerja Fitur Inti
1. **Autentikasi (JWT + Bcrypt)**: Customer, EO, Admin registrasi/login dan mendapatkan token JWT.
2. **Katalog & Sinkronisasi Kuota**: API membaca daftar konser. Kuota tiket awal disinkronkan ke Redis (`quota:{category_id}`).
3. **War Tiket (Fast Ingestion)**:
   * Frontend menembak `POST /api/v1/orders/reserve`.
   * API memotong kuota tiket secara atomic di Redis via `DECRBY`.
   * Jika kuota habis ($< 0$), API langsung merespons `400 Sold Out`.
   * Jika berhasil, API mendorong payload ke antrean Redis `order_queue` dan seketika mengembalikan `202 Accepted` bersama `invoice_number`.
4. **Pemrosesan Asinkron (Worker)**:
   * Worker memantau antrean `order_queue`.
   * Mengunci nomor kursi dengan Redis Distributed Lock (`SET lock:seat:... NX PX 10000`).
   * Menjalankan transaksi ACID di PostgreSQL (insert order, generate baris tiket, catat audit log).
   * Menandai status order menjadi `paid` / `completed`.
5. **Antarmuka Pengguna (Vue 3)**:
   * Menampilkan timer hitung mundur.
   * Saat tombol *War* ditekan, UI beralih ke *Waiting Room / Queue Tracker*.
   * Polling berkala (setiap 1.5 detik) ke `GET /api/v1/orders/status/:invoiceNumber` hingga status transaksi selesai dan tiket muncul.

---
