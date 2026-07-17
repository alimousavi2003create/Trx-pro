"""TRX PRO - Database Layer"""
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import config

def get_db():
    conn = psycopg2.connect(config.DATABASE_URL)
    conn.autocommit = False
    return conn

@contextmanager
def get_db_cursor():
    conn = get_db()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def init_db():
    with get_db_cursor() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS nfts (
                id SERIAL PRIMARY KEY,
                owner_id TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                name TEXT NOT NULL,
                image_data TEXT NOT NULL,
                price NUMERIC,
                currency TEXT,
                is_listed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            ALTER TABLE nfts ADD COLUMN IF NOT EXISTS mint_fee_amount NUMERIC
        """)
        c.execute("""
            ALTER TABLE nfts ADD COLUMN IF NOT EXISTS mint_fee_currency TEXT
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY, username TEXT, first_name TEXT,
                last_name TEXT, photo_url TEXT, wallet_trx TEXT, wallet_ton TEXT,
                balance_trx REAL DEFAULT 0, balance_ton REAL DEFAULT 0,
                mining_power REAL DEFAULT 1.0, energy INTEGER DEFAULT 100,
                energy_max INTEGER DEFAULT 100, energy_last_refill TIMESTAMP DEFAULT NOW(),
                level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0, xp_next INTEGER DEFAULT 150,
                referral_code TEXT UNIQUE, parent_id TEXT REFERENCES users(user_id),
                left_child TEXT REFERENCES users(user_id), right_child TEXT REFERENCES users(user_id),
                tree_depth INTEGER DEFAULT 0, left_volume REAL DEFAULT 0,
                right_volume REAL DEFAULT 0, cycle_count INTEGER DEFAULT 0,
                last_bonus_at TIMESTAMP, tap_count_today INTEGER DEFAULT 0,
                tap_count_total INTEGER DEFAULT 0, last_tap_at TIMESTAMP,
                tap_pattern_score REAL DEFAULT 0, is_flagged BOOLEAN DEFAULT FALSE,
                captcha_required BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(), last_active_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_usdt REAL DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tap_count_reset_at TIMESTAMP DEFAULT NOW()")
        c.execute("UPDATE users SET tap_count_today = 0, tap_count_reset_at = NOW() WHERE tap_count_today >= %s", (config.TAP_DAILY_LIMIT,))
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tap_count_reset_at TIMESTAMP DEFAULT NOW()")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_automine_at TIMESTAMP DEFAULT NOW()")
        c.execute("""
            CREATE TABLE IF NOT EXISTS shop_items (
                id SERIAL PRIMARY KEY, item_key TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL, description TEXT, icon_3d_url TEXT, icon_2d_url TEXT,
                price_trx REAL, price_ton REAL, effect_type TEXT NOT NULL,
                effect_value REAL NOT NULL, effect_duration INTEGER DEFAULT 0,
                rarity TEXT DEFAULT 'Common', max_quantity INTEGER DEFAULT 1,
                required_level INTEGER DEFAULT 1, is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                item_key TEXT NOT NULL REFERENCES shop_items(item_key), quantity INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE, purchased_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP, created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS crash_rounds (
                round_id TEXT PRIMARY KEY, seed_hash TEXT NOT NULL,
                seed_reveal TEXT, crash_point REAL, total_bets_trx REAL DEFAULT 0,
                total_bets_ton REAL DEFAULT 0, total_players INTEGER DEFAULT 0,
                status TEXT DEFAULT 'waiting', start_time TIMESTAMP, end_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS crash_bets (
                id SERIAL PRIMARY KEY, round_id TEXT NOT NULL REFERENCES crash_rounds(round_id),
                user_id TEXT NOT NULL REFERENCES users(user_id), currency TEXT NOT NULL,
                amount REAL NOT NULL, cashout_multiplier REAL, profit REAL DEFAULT 0,
                fee REAL DEFAULT 0, status TEXT DEFAULT 'pending', cashed_out_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
                type TEXT NOT NULL, currency TEXT NOT NULL, amount REAL NOT NULL,
                fee REAL DEFAULT 0, balance_before REAL, balance_after REAL,
                metadata JSONB DEFAULT '{}', created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS referral_commissions (
                id SERIAL PRIMARY KEY, referrer_id TEXT NOT NULL REFERENCES users(user_id),
                referred_id TEXT NOT NULL REFERENCES users(user_id), level INTEGER NOT NULL,
                transaction_id INTEGER REFERENCES transactions(id), amount REAL NOT NULL,
                currency TEXT NOT NULL, is_paid BOOLEAN DEFAULT FALSE, paid_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS bot_logs (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
                event_type TEXT NOT NULL, details JSONB DEFAULT '{}',
                severity INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS processed_deposits (
                tx_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                currency TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS pool_state (
                currency TEXT PRIMARY KEY,
                total_collected REAL DEFAULT 0,
                total_paid REAL DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
                currency TEXT NOT NULL, amount REAL NOT NULL, destination_address TEXT NOT NULL,
                status TEXT DEFAULT 'pending', admin_note TEXT,
                created_at TIMESTAMP DEFAULT NOW(), processed_at TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY, active_users INTEGER DEFAULT 0,
                total_taps INTEGER DEFAULT 0, total_mined_trx REAL DEFAULT 0,
                total_bets_trx REAL DEFAULT 0, total_bets_ton REAL DEFAULT 0,
                project_fees_trx REAL DEFAULT 0, project_fees_ton REAL DEFAULT 0,
                new_users INTEGER DEFAULT 0, withdrawals_trx REAL DEFAULT 0
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_parent ON users(parent_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_flagged ON users(is_flagged) WHERE is_flagged = TRUE")
        c.execute("CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory(user_id, is_active)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_crash_bets_round ON crash_bets(round_id, status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_crash_bets_user ON crash_bets(user_id, created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type, currency)")
    print("Database initialized!")
