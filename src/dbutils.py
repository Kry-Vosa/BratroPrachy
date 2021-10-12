import sqlite3
from data_classes import *

APP_NAME = "BratroPrachy"
DB_VERSION = '2'

def get_version(cur):
    """return version number as a str if version was found or None if not"""
    
    #Check if the info table exists
    cur.execute("""
        SELECT count(*) FROM sqlite_master WHERE type='table' AND name='db_info';
    """)
    try_version = cur.fetchone()[0]
    
    #It doesn't, this might not be our db
    if not try_version:
        return None
        
    cur.execute("""
        SELECT key, value FROM db_info WHERE key IN ('version', 'app_name');
    """)
    
    db_info = dict(cur.fetchall())
    
    #Not correct data from db_info, something's fishy
    if db_info.get("app_name", None) != APP_NAME:
        return None
        
    return db_info.get("version", None)

def check_is_fresh(cur):
    """Returns true if the database is completely empty"""

    cur.execute("""
        SELECT count(*) FROM sqlite_master
    """)
    
    return cur.fetchone()[0] < 1

def create_db_newest(cur):
    cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                stamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                balance_change INTEGER NOT NULL
            );
        """)
        
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            payment_id INTEGER NOT NULL,
            item_name TEXT,
            item_cost INTEGER NOT NULL,
            count INTEGER INTEGER NOT NULL,
            cost_total INTEGER GENERATED ALWAYS AS (item_cost*count),
            
            FOREIGN KEY (payment_id) REFERENCES payments(payment_id) ON DELETE CASCADE
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            nickname TEXT,
            first_name TEXT,
            last_name TEXT
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS db_info (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    
    cur.execute("""
        INSERT INTO db_info (key, value) VALUES
            ('app_name', ?),
            ('version', ?);
    """, (APP_NAME, DB_VERSION))

def upgrade_db(cur, from_version):
    
    # makes simple upgrades easier to write
    def create_from_sql(expr, ret):
        def new_func(cur):
            if isinstance(expr, str):
                cur.execute(expr)
            else: 
                for exp in expr:
                    cur.execute(exp)
            return ret
        return new_func
    upgrades = {
        #key is version to upgrade from, function returns version it upgraded to. This will allow to add "jump" upgrade functions if upgardes would take too much time
        '1': create_from_sql(["ALTER TABLE customers ADD COLUMN first_name TEXT;", 'ALTER TABLE customers ADD COLUMN last_name TEXT;'], '2')
    }
    
    while from_version != DB_VERSION:
        from_version=upgrades[from_version](cur)
        cur.execute("UPDATE db_info SET value = ? WHERE key='version'", (from_version,))

def prepare_db():
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        
        version = get_version(cur)
        
        if not version:
            if check_is_fresh(cur):
                create_db_newest(cur)
            else:
                raise Exception("Neidentifikovatelná databáze! Možná špatný .db soubor?")
        elif int(version) > int(DB_VERSION):
            raise Exception(f"Nepoužitelná verze databáze! Možná špatný .db soubor?\nVerze v souboru: {version}\n Verze v programu: {DB_VERSION}")
        else:
            upgrade_db(cur, version)
    
        conn.commit()

def get_money(customer_id):
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT SUM(balance_change) FROM payments WHERE customer_id = ?;
        """, (customer_id,))
        ret = cur.fetchone()[0]
        if not ret:
            return 0
        return ret

def get_info(customer_id):
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT IFNULL(payments.customer_id, :customer_id), first_name, last_name, nickname, SUM(balance_change) AS balance FROM payments
              LEFT JOIN customers ON customers.customer_id = payments.customer_id
              WHERE payments.customer_id = :customer_id;
        """, {"customer_id":customer_id})
        ret = cur.fetchone()
        
        return CustomerInfo(*ret)
        
def get_export():
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT payments.customer_id, first_name, last_name, nickname, SUM(balance_change) AS balance FROM payments
              LEFT JOIN customers ON customers.customer_id = payments.customer_id
              GROUP BY payments.customer_id
              HAVING balance != 0 OR COALESCE(first_name, last_name, nickname) IS NOT NULL
              ORDER BY payments.customer_id ASC;
        """)
        return cur.fetchall();

def save_info(customer_id, first_name, last_name, nickname):
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO customers (customer_id, first_name, last_name, nickname) VALUES (:customer_id, :first_name, :last_name, :nickname)
            ON CONFLICT(customer_id) DO UPDATE SET first_name = :first_name, last_name = :last_name, nickname = :nickname;
        """, {"customer_id": customer_id, "first_name":first_name or None, "last_name": last_name or None, "nickname": nickname or None})
        conn.commit()

def save_order(customer_id, order):
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO payments (customer_id, description, balance_change) VALUES (?, "ORDER_PAYMENT", 0)
        """, (customer_id,))
        
        payment_id = cur.lastrowid
        cur.executemany("""
            INSERT INTO orders (payment_id, item_name, item_cost, count) VALUES (?, ?, ?, ?)
        """, [(payment_id, name, val, count) for (name, val), count in order.items()])
        
        cur.execute("""
            UPDATE payments SET balance_change = -1 * (SELECT SUM(cost_total) FROM orders WHERE payment_id = ?) WHERE payment_id = ?
        """, (payment_id, payment_id))
        
        conn.commit()

def add_funds(customer_id, amount):
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO payments (customer_id, description, balance_change) VALUES (?, "ADD_FUNDS", ?)
        """, (customer_id, amount))
        conn.commit()

def remove_funds(customer_id, amount):
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO payments (customer_id, description, balance_change) VALUES (?, "REMOVE_FUNDS", ?)
        """, (customer_id, -amount))
        conn.commit()

def get_payment_list(customer_id):
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT payment_id, description, stamp, balance_change, CASE WHEN EXISTS (SELECT * FROM orders WHERE orders.payment_id = payments.payment_id) THEN 1 ELSE 0 END as order_exists FROM payments
            WHERE customer_id = ?
            ORDER BY stamp ASC
        """, (customer_id,))
        
        payments = [list(x) for x in cur.fetchall()]
        
    for payment in payments:
        if payment[4]:
            payment[4] = get_order_list(payment[0])
        else:
            payment[4] = []
    
    return payments
    
def delete_payment(payment_id):
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM payments WHERE payment_id = ?
        """, (payment_id,))

def get_order_list(payment_id):
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT item_name, count, cost_total FROM orders WHERE payment_id = ?
            ORDER BY item_name DESC
        """, (payment_id,))
        return cur.fetchall()