-- ============================================
-- TicketWar – Database Initialization Script
-- ============================================
-- Auto-executed on first `docker-compose up` via
-- /docker-entrypoint-initdb.d/init.sql
--
-- Contents:
--   1. DDL  – 6 tables
--   2. IDX  – Performance indexes
--   3. SEED – Initial data (users, concert, categories)
-- ============================================

BEGIN;

-- ============================================
-- 1. DDL – TABLE DEFINITIONS
-- ============================================

-- 1.1 Users
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL       PRIMARY KEY,
    username      VARCHAR(50)  UNIQUE NOT NULL,
    email         VARCHAR(120) UNIQUE NOT NULL,
    password_hash TEXT         NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'customer'
                  CHECK (role IN ('customer', 'eo', 'admin')),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- 1.2 Concerts
CREATE TABLE IF NOT EXISTS concerts (
    id            SERIAL       PRIMARY KEY,
    organizer_id  INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title         VARCHAR(200) NOT NULL,
    artist        VARCHAR(200) NOT NULL,
    venue         VARCHAR(200) NOT NULL,
    concert_date  TIMESTAMPTZ  NOT NULL,
    status        VARCHAR(20)  NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'published', 'cancelled', 'completed'))
);

-- 1.3 Ticket Categories
CREATE TABLE IF NOT EXISTS ticket_categories (
    id              SERIAL         PRIMARY KEY,
    concert_id      INTEGER        NOT NULL REFERENCES concerts(id) ON DELETE CASCADE,
    category_name   VARCHAR(100)   NOT NULL,
    price           NUMERIC(12,2)  NOT NULL,
    total_quota     INTEGER        NOT NULL,
    available_quota INTEGER        NOT NULL
);

-- 1.4 Orders
CREATE TABLE IF NOT EXISTS orders (
    id              SERIAL         PRIMARY KEY,
    invoice_number  VARCHAR(50)    UNIQUE NOT NULL,
    user_id         INTEGER        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id     INTEGER        NOT NULL REFERENCES ticket_categories(id) ON DELETE CASCADE,
    quantity        INTEGER        NOT NULL,
    total_amount    NUMERIC(14,2)  NOT NULL,
    payment_status  VARCHAR(20)    NOT NULL DEFAULT 'pending'
                    CHECK (payment_status IN ('pending', 'paid', 'failed')),
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- 1.5 Tickets
CREATE TABLE IF NOT EXISTS tickets (
    id          SERIAL       PRIMARY KEY,
    order_id    INTEGER      NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    seat_number VARCHAR(20)  NOT NULL,
    ticket_code VARCHAR(50)  UNIQUE NOT NULL,
    is_used     BOOLEAN      NOT NULL DEFAULT FALSE,
    is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
    issued_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- 1.6 Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id          SERIAL       PRIMARY KEY,
    user_id     INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(100) NOT NULL,
    table_name  VARCHAR(100),
    record_id   INTEGER,
    ip_address  VARCHAR(45),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ============================================
-- 2. IDX – INDEXES
-- ============================================

-- Fast lookup by invoice number (order status polling)
CREATE INDEX IF NOT EXISTS idx_orders_invoice_number
    ON orders (invoice_number);

-- Fast lookup for user's order history
CREATE INDEX IF NOT EXISTS idx_orders_user_id
    ON orders (user_id);

-- Fast lookup / validation of ticket codes (e-ticket scan)
CREATE INDEX IF NOT EXISTS idx_tickets_ticket_code
    ON tickets (ticket_code);

-- ============================================
-- 3. SEED – INITIAL DATA
-- ============================================

-- 3.1 Users
-- Passwords hashed with bcrypt (cost 12):
--   admin123 → $2b$12$fHKjpGJuqJefYiYrv5Qs2uoYucnrIqBaFYKAx4NoYgwdpi/EG4zVq
--   eo123    → $2b$12$D9qATXt9QhAny6DMsvRZ3O2WOpKgydv2QD0mBwYUO8/KGvMsXYy3i
--   user123  → $2b$12$8ssOkbmH3cnuKOBUI/.RzOd2OPY/Ugs6591j9Wqtb1SBV89uVitLK

INSERT INTO users (username, email, password_hash, role) VALUES
    ('admin',
     'admin@ticketwar.id',
     '$2b$12$fHKjpGJuqJefYiYrv5Qs2uoYucnrIqBaFYKAx4NoYgwdpi/EG4zVq',
     'admin'),
    ('eo_coldplay',
     'eo@ticketwar.id',
     '$2b$12$D9qATXt9QhAny6DMsvRZ3O2WOpKgydv2QD0mBwYUO8/KGvMsXYy3i',
     'eo'),
    ('johndoe',
     'johndoe@email.com',
     '$2b$12$8ssOkbmH3cnuKOBUI/.RzOd2OPY/Ugs6591j9Wqtb1SBV89uVitLK',
     'customer')
ON CONFLICT DO NOTHING;

-- 3.2 Concert (organizer = eo_coldplay, id = 2)
INSERT INTO concerts (organizer_id, title, artist, venue, concert_date, status) VALUES
    (2,
     'Coldplay Music of the Spheres',
     'Coldplay',
     'Gelora Bung Karno Stadium, Jakarta',
     '2026-11-15 19:00:00+07',
     'published')
ON CONFLICT DO NOTHING;

-- 3.3 Ticket Categories
INSERT INTO ticket_categories (concert_id, category_name, price, total_quota, available_quota) VALUES
    (1, 'CAT 1',  1500000.00, 50, 50),
    (1, 'VIP',    3500000.00, 20, 20)
ON CONFLICT DO NOTHING;

COMMIT;
