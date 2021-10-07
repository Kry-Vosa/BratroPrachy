import sqlite3

def prepare_db():
    with sqlite3.connect("prachy.db") as conn:
        cur = conn.cursor()
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
                nickname TEXT
            );
        """)
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