# 🎫 TicketWar — Distributed High-Concurrency Ticket War System

> Sistem pemesanan tiket konser terdistribusi dengan arsitektur *non-blocking fast-ingestion* yang dirancang khusus untuk menangani lonjakan trafik tinggi (*flash sale / war tiket*) tanpa kemacetan database (*connection exhaustion*) dan tanpa penjualan kursi ganda (*zero race-condition & anti-overselling*).

---

## 📑 Daftar Isi

- [Arsitektur Sistem](#-arsitektur-sistem)
- [Tech Stack](#-tech-stack)
- [Struktur Direktori](#-struktur-direktori)
- [Prasyarat](#-prasyarat)
- [Panduan Instalasi & Menjalankan](#-panduan-instalasi--menjalankan)
- [Akun Demo Bawaan](#-akun-demo-bawaan-seed-data)
- [Panduan Pengujian Beban (Load Testing 1 - 500 VUs)](#-panduan-pengujian-beban-load-testing)
- [Cara Mengubah Skenario Uji Beban](#-cara-mengubah-skenario-uji-beban)
- [Cara Mereset Data Transaksi & Kuota](#-cara-mereset-data-transaksi--kuota)
- [Panduan Modifikasi Kode](#-panduan-modifikasi-kode)
- [Troubleshooting](#-troubleshooting)

---

## 🏛️ Arsitektur Sistem

Saat ribuan pengguna menekan tombol **"AMBIL TIKET SEKARANG"** secara serentak, request **TIDAK** langsung menembak database PostgreSQL. Sistem menggunakan pola **Fast Ingestion Buffer**:

```
[ Browser / Vue 3 ] 
        │ (HTTP / WebSocket)
        ▼
[ Nginx Gateway / Load Balancer :8080 ]
        │
        ├───────────────┬────────────────────────┐
        ▼               ▼                        ▼
 [ Static / SPA ]  [ Flask API :8000 ]    [ Vite HMR ]
                        │
                        ├─► 1. Atomic DECRBY quota:{cat_id} di Redis
                        │      ├─ Kuota < 0  ──► Return 400 (Sold Out) Langsung!
                        │      └─ Kuota >= 0 ──► 2. Push ke Redis 'order_queue'
                        │                           │
                        └────── Return 202 ◄────────┘ (Non-blocking < 20ms)
                                     │
                                     ▼
                           [ Worker Daemon (Python) ]
                                     │
                                     ├─► 3. Ambil order via BLPOP
                                     ├─► 4. Pasang Redis Distributed Lock kursi
                                     ├─► 5. Transaksi ACID ke PostgreSQL:
                                     │       - Insert Orders (paid)
                                     │       - Generate Tickets & UUID Code
                                     │       - Update DB available_quota
                                     │       - Insert Audit Log
                                     ├─► 6. Lepas Distributed Lock (Lua CAS)
                                     └─► 7. Cache status order: "completed"
```

---

## 💻 Tech Stack

| Komponen | Teknologi | Keterangan |
|---|---|---|
| **Frontend** | Vue 3 (`<script setup>`), Vite, Pinia, Tailwind CSS | SPA reaktif, countdown timer, waiting room polling |
| **Reverse Proxy** | Nginx 1.25 Alpine | Port host `8080` -> internal route ke frontend & API |
| **Ingestion API** | Python 3.12, Flask, PyJWT, psycopg2 | Non-blocking validator & queue producer |
| **In-Memory & Lock** | Redis 7 Alpine | Atomic decrement, FIFO `order_queue`, Distributed Lock |
| **Worker Daemon** | Python 3.12 Worker Pool | Asynchronous order processor & ACID committer |
| **Database Persisten**| PostgreSQL 16 Alpine | 6 relasi tabel dengan indeks performa |

---

## 📁 Struktur Direktori

```text
ticket-konser/
├── .env                        # Konfigurasi database, Redis, & JWT Secret
├── docker-compose.yml          # Konfigurasi 6 container Docker & network
├── README.md                   # Dokumentasi lengkap proyek
├── reset.ps1                   # Skrip reset cepat kuota & transaksi (PowerShell)
├── reset.bat                   # Skrip reset cepat kuota (Double-click Windows)
├── docs/
│   └── PRD.md                  # Spesifikasi kebutuhan produk
├── nginx/
│   └── default.conf            # Konfigurasi reverse proxy & SPA fallback
├── load-test/
│   ├── war-test.js             # Skrip uji beban k6 (1 s/d 500 VUs)
│   └── locustfile.py           # Skrip uji beban alternatif berbasis Locust
├── frontend/                   # Vue 3 Single Page Application
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── api/                # Axios instance + JWT Interceptor
│       ├── stores/             # Pinia Auth Store
│       ├── router/             # Vue Router + Navigation Guard
│       ├── components/         # NavBar, WaitingModal
│       └── views/              # Login, Register, ConcertList, WarRoom, OrderDetail
├── api/                        # Ingestion Backend API (Flask)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py                  # Entrypoint server
│   └── app/
│       ├── __init__.py         # App factory & CORS
│       ├── config.py           # Environment variables loader
│       ├── extensions.py       # PostgreSQL Pool & Redis client singleton
│       ├── auth.py             # JWT encode/decode & @jwt_required decorator
│       └── routes/             # Blueprint: auth, concerts, orders
├── worker/                     # Asynchronous Background Worker
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py               # BLPOP listener, Distributed Lock, & ACID transaction
└── postgres/
    └── init.sql                # DDL skema 6 tabel, indexes, & seed data
```

---

## ⚙️ Prasyarat

Sebelum memulai, pastikan perangkat Anda memiliki:
* **Docker Desktop** (dengan status *Engine running*).
* **Git** (opsional, untuk clone repositori).

---

## 🚀 Panduan Instalasi & Menjalankan

### 1. Clone Repositori
```bash
git clone https://github.com/USERNAME/ticket-konser.git
cd ticket-konser
```

### 2. Nyalakan Seluruh Sistem dengan Docker Compose
```powershell
docker compose up --build -d
```
*(Docker akan mengunduh image dan menyalakan 6 service di latar belakang)*.

### 3. Cek Status Kontainer
```powershell
docker compose ps
```
Pastikan seluruh kontainer berikut berjalan:
* `ticketwar_nginx`
* `ticketwar_frontend`
* `ticketwar_api`
* `ticketwar_worker`
* `ticketwar_redis` (healthy)
* `ticketwar_db` (healthy)

### 4. Akses Aplikasi di Browser

| Halaman | URL | Keterangan |
|---|---|---|
| **Frontend Web** | [http://localhost:8080](http://localhost:8080) | Katalog konser, login, & war room |
| **API Health Check** | [http://localhost:8080/api/health](http://localhost:8080/api/health) | Verifikasi status API |
| **Katalog Konser & Kuota** | [http://localhost:8080/api/v1/concerts](http://localhost:8080/api/v1/concerts) | Endpoint JSON konser |

---

## 👤 Akun Demo Bawaan (Seed Data)

Database sudah dilengkapi data awal untuk pengujian langsung:

| Role | Username | Password | Hak Akses |
|---|---|---|---|
| **Customer** | `johndoe` | `user123` | Mengikuti War Tiket & Melihat E-Ticket |
| **Event Organizer** | `eo_coldplay` | `eo123` | Monitoring kuota & event |
| **Administrator** | `admin` | `admin123` | Akses audit & status semua invoice |

---

## 🧪 Panduan Pengujian Beban (Load Testing)

Sistem telah diuji sanggup melayani **25.000+ request** dengan lonjakan serentak hingga **500 Virtual Users** tanpa crash (*0% server down*).

### Menjalankan Uji Beban 1 s/d 500 Virtual Users (k6 via Docker)

Jalankan perintah ini di PowerShell tanpa perlu menginstal apa pun di komputer host:

```powershell
docker run --rm -v ${PWD}/load-test:/scripts --network=ticket-konser_ticketwar_net -e TARGET_URL=http://nginx/api/v1 grafana/k6 run /scripts/war-test.js
```

### Membaca Hasil Metrik k6:
* **`tickets_reserved_202`**: Jumlah pesanan yang berhasil mengamankan kuota (tepat sesuai kuota tiket).
* **`tickets_sold_out_400`**: Jumlah permintaan yang ditolak secara aman oleh Redis setelah tiket habis.
* **`http_req_failed`**: Menunjukkan kegagalan teknis (error 500 / 502). Nilai yang diharapkan adalah **`0.00%`**.
* **`reserve_response_time_ms`**: Rata-rata waktu respons transaksi (biasanya < 500ms).

---

## 🛠️ Cara Mengubah Skenario Uji Beban

Buka file **[`load-test/war-test.js`](load-test/war-test.js)**:

### 1. Mengubah Jumlah Virtual Users & Durasi
Cari bagian `stages`:
```javascript
export const options = {
  stages: [
    { duration: '10s', target: 50 },   // Naik ke 50 user dalam 10 detik
    { duration: '20s', target: 200 },  // Naik ke 200 user
    { duration: '30s', target: 500 },  // Puncak: 500 user serentak
    { duration: '20s', target: 500 },  // Tahan di 500 user
    { duration: '10s', target: 0 },    // Turun kembali ke 0
  ],
  // ...
};
```
* Untuk menaikkan ke **1000 user**, cukup ganti angka `target: 500` menjadi `target: 1000`.
* Untuk uji ledakan instan (*spike test*), ubah durasi menjadi pendek, misal `{ duration: '5s', target: 500 }`.

### 2. Mengubah Kategori Tiket yang Diuji
Di fungsi default:
```javascript
const payload = JSON.stringify({
  category_id: 1, // Ganti dengan ID kategori lain (misal: 2 untuk VIP)
  quantity: 1,    // Jumlah tiket per klik
});
```

---

## 🔄 Cara Mereset Data Transaksi & Kuota

Setelah selesai uji beban, kuota tiket akan menjadi 0. Anda bisa meresetnya kembali ke kondisi siap uji dalam 1 detik:

### Opsi A: Menggunakan Skrip Cepat (Kontainer Tetap Nyala)

Buka PowerShell dan jalankan:
```powershell
powershell -ExecutionPolicy Bypass -File .\reset.ps1 -Cat1Quota 500
```
*(Atau double-click file **`reset.bat`**)*.

Anda juga bisa mengatur kuota berapapun:
```powershell
powershell -ExecutionPolicy Bypass -File .\reset.ps1 -Cat1Quota 1000
```

### Opsi B: Reset Total Pabrik (Menghapus Harddisk Volume Database)
```powershell
docker compose down -v
docker compose up -d
```

---

## 🧩 Panduan Modifikasi Kode

### 1. Menambah Konser atau Kategori Tiket Baru
Edit file **[`postgres/init.sql`](postgres/init.sql)** pada bagian `SEED DATA`:
```sql
INSERT INTO concerts (organizer_id, title, artist, venue, concert_date, status) VALUES
    (2, 'Konser Baru', 'Nama Artis', 'Stadion Madya', '2026-12-01 20:00:00+07', 'published');

INSERT INTO ticket_categories (concert_id, category_name, price, total_quota, available_quota) VALUES
    (2, 'Festival A', 850000.00, 100, 100);
```

### 2. Mengatur Durasi Distributed Lock
Edit file **[`worker/worker.py`](worker/worker.py)**:
```python
LOCK_TTL_MS = 10_000   # 10 detik (durasi lock kursi di Redis)
```

### 3. Mengatur Endpoint / Port
* Port Nginx host diatur di **[`docker-compose.yml`](docker-compose.yml)**: `8080:80`.
* JWT Expiration dan kredensial database diatur di **[`.env`](.env)**.

---

## ❓ Troubleshooting

#### 1. Script `.ps1` diblokir Windows ("running scripts is disabled")
Jalankan perintah ini di PowerShell untuk mengizinkan eksekusi sesi saat ini:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

#### 2. Error "network ticketwar_net not found" saat load test
Docker Compose secara default menambahkan prefix nama folder proyek ke nama network. Pastikan menggunakan nama:
```powershell
--network=ticket-konser_ticketwar_net
```
*(Atau cek nama network persisnya dengan `docker network ls`)*.

#### 3. Ingin Melihat Log Antrean Pemrosesan Tiket
```powershell
# Memantau Worker mengambil antrean dan locking kursi secara live:
docker compose logs -f worker

# Memantau Ingestion API:
docker compose logs -f api
```

---

## 📄 Lisensi
Proyek ini dibuat untuk keperluan demonstrasi sistem terdistribusi skala tinggi. Bebas digunakan dan dimodifikasi (*MIT License*).
