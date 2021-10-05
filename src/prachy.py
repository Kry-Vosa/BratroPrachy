import tkinter as tk
import tkinter.messagebox as tkmessagebox
import tkinter.scrolledtext as tkscrolledtext
import tkinter.font as tkFont
import sqlite3, json, sys

def only4Num(inStr, acttyp):
    if acttyp == '1': #insert
        if not inStr.isdigit() or len(inStr) > 4:
            return False
    return True

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
        """, [(payment_id, val, val, count) for val, count in order.items()])
        
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
        

class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=22, family='Arial')
        self.title("Endurova kalkulačka peněz")
        self.wm_geometry("800x600")
        self.state('zoomed')
        
        self.prepare_db()
        
        
        
        
        self.frames = {
            "MainPage": MainPage(self),
            "Order": Order(self, buttons=self.load_price_buttons()),
            "EditProfile": EditProfile(self),
        }
        
        for frame in self.frames.values():
            frame.place(x=0, y=0, relwidth=1, relheight=1)
        
        self.open_frame("MainPage")
        
    def open_frame(self, name, returned_from=False, *args, **kwargs):
        frame = self.frames[name];
        if returned_from:
            ret = frame.returned_back(returned_from, *args, **kwargs)
        else:
            ret = frame.setup(*args, **kwargs)
        if ret is not False:
            frame.tkraise()
    
    def load_price_buttons(self):
        try:
            with open("./config.json") as infil:
                return json.load(infil)["buttons"]
        except Exception as ex:
            print(ex)
            tkmessagebox.showerror(title="Chyba v nastavení", message="Při načítání config.json se objevila nějaká chyba\nZkontrolujte, že je všechno tak, jak má být.")
            sys.exit()
            
            
    @staticmethod        
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
            

class MainPage(tk.Frame):
    def __init__(self, root):
        self.app = root;
        tk.Frame.__init__(self, root)
        
        button_font = tkFont.Font(family='Arial', size=22, weight="bold")
        
        menu_frame = tk.Frame(self, bg="red")
        menu_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        """payment_button = tk.Button(menu_frame, text="Opravit poslední\nobjednávku", bg="#a3ffb3")
        payment_button.pack(side="left", fill="y", expand=True)
        
        payment_button = tk.Button(menu_frame, text="Zazálohovat", bg="#a3ffb3")
        payment_button.pack(side="left", fill="y", expand=True)"""
        
        tk.Label(self, text="Číslo:", font=button_font)\
          .grid(row=2, column=0, sticky="es")
        
        input_number = self.input_number = tk.Entry(self, font=button_font, width=5, validate="key")
        input_number['validatecommand'] = (input_number.register(only4Num),'%P','%d')
        input_number.bind("<Return>", lambda _: self.open_order())
        input_number.grid(row=2, column=1, sticky="ws")
        
        buttons_frame = tk.Frame(self)
        buttons_frame.grid(row=3, columnspan=2, sticky="n", pady=10,)
        
        payment_button = tk.Button(buttons_frame, text="Objednávka", bg="#a3ffb3", command=self.open_order)
        payment_button.pack(side="left", padx=5)
        
        add_money_button = tk.Button(buttons_frame, text="Upravit profil/nabít kredit", bg="#fffb80", command=self.add_money)
        add_money_button.pack(side="left", padx=5)
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
    
    def open_order(self):
        if not self.input_number.get():
            return
        val = int(self.input_number.get())
        self.clear()
        self.app.open_frame("Order", val)
    
    def add_money(self):
        if not self.input_number.get():
            return
        val = int(self.input_number.get())
        self.clear()
        self.app.open_frame("EditProfile", val)
    
    def clear(self):
        self.input_number.delete(0, "end")
    
    def setup(self):
        self.input_number.focus_set()
        pass
        
class EditProfile(tk.Frame):
    def __init__(self, root):
        self.app = root;
        tk.Frame.__init__(self, root)
        
        button_font = tkFont.Font(family='Arial', size=22, weight="bold")
        
        info_area = tk.Frame(self)
        info_area.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        info_label = tk.Label(info_area, text="Zákazník:", font=button_font)
        info_label.pack(side="left")
        customer_label = self.customer_label = tk.Label(info_area, text="-", font=button_font)
        customer_label.pack(side="left")

        czk_label = tk.Label(info_area, text="Kč", font=button_font)
        czk_label.pack(side="right")
        money_label = self.money_label = tk.Label(info_area, text="-", font=button_font)
        money_label.pack(side="right")
        
        
        order_history = self.order_history = tkscrolledtext.ScrolledText(self, width=30, borderwidth=0, highlightthickness=0, state="disabled", font=tkFont.Font(family='Courier', size=22))
        order_history.grid(row=1, column=1, sticky="nsew")

        main_area = tk.Frame(self)
        main_area.grid(row=1, column=0, sticky="nsew", padx=5, pady=15)
        
        add_funds_frame = tk.Frame(main_area)
        tk.Label(add_funds_frame, text="Nabití kreditu:", font=button_font)\
          .pack(side="left", )
        input_funds = self.input_funds = tk.Entry(add_funds_frame, font=button_font, width=5, validate="key")
        input_funds['validatecommand'] = (input_funds.register(only4Num),'%P','%d')
        input_funds.bind("<Return>", lambda _: self.add_funds_button_callback())
        input_funds.pack(side="left")
        add_funds_button = tk.Button(add_funds_frame, text="Nabít", bg="#a3ffb3", command=self.add_funds_button_callback)
        add_funds_button.pack(side="left")
        
        add_funds_frame.pack(fill="x", expand=True)
        
        
        remove_funds_frame = tk.Frame(main_area)
        tk.Label(remove_funds_frame, text="Vybití kreditu:", font=button_font)\
          .pack(side="left")
        input_remove_funds = self.input_remove_funds = tk.Entry(remove_funds_frame, font=button_font, width=5, validate="key")
        input_remove_funds['validatecommand'] = (input_funds.register(only4Num),'%P','%d')
        input_remove_funds.bind("<Return>", lambda _: self.remove_funds_button_callback())
        input_remove_funds.pack(side="left")
        remove_funds_button = tk.Button(remove_funds_frame, text="Vybít", bg="#fffb80", command=self.remove_funds_button_callback)
        remove_funds_button.pack(side="left")
        
        remove_funds_frame.pack(fill="x", expand=True)
        
        finish_area = tk.Frame(self)
        finish_area.grid(row=2, column=0, columnspan=2, sticky="nsew")
        back_button=tk.Button(finish_area, text="Zpět", bg="#ff9696", font=button_font, command=self.exit_button_callback)
        back_button.pack(side="left", fill="y", padx=5, pady=5)
        self.bind('<Escape>', lambda _: self.exit_button_callback())
        
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        
        self.clear()
    
    def exit_button_callback(self):
        self.clear()
        self.app.open_frame(self.return_to, returned_from = "EditProfile")
        
    def add_funds_button_callback(self):
        value_add = self.input_funds.get()
        if not value_add:
            self.bell()
            return
        value_add = int(value_add)
        
        cancel = tkmessagebox.askyesno(title="Nabít kredit", message="Opravdu chcete nabít účet hodnotou "+str(value_add)+ "?")
        if not cancel:
            return
        
        self.input_funds.delete(0, "end")
        add_funds(self.customer_num, value_add)
        self.money_label["text"] = get_money(self.customer_num)
        self.load_old_orders()
        
    def remove_funds_button_callback(self):
        value = self.input_remove_funds.get()
        if not value:
            self.bell()
            return
        value = int(value)
        
        cancel = tkmessagebox.askyesno(title="Vybít kredit", message="Opravdu chcete z účtu vybít hodnotou "+str(value)+ "?")
        if not cancel:
            return
        
        self.input_remove_funds.delete(0, "end")
        remove_funds(self.customer_num, value)
        self.money_label["text"] = get_money(self.customer_num)
        self.load_old_orders()

    
    def setup(self, customer_num, return_to="MainPage"):
        self.return_to = return_to
        self.customer_num = customer_num
        self.customer_label["text"] = customer_num
        self.money_label["text"] = get_money(customer_num)
        self.load_old_orders()
        
        self.focus_set()
    
    def clear(self):
        self.customer_label["text"] = "-";
        self.money_label["text"] = "-"
        self.customer_num = 0
        self.input_funds.delete(0, "end")
        
        self.order_history['state'] = 'normal'
        self.order_history.delete("1.0", "end")
        self.order_history['state'] = 'disabled'
        
    def delete_order(self, order_id):
        cancel = tkmessagebox.askyesno(title="Zrušení z historie", message="Opravdu chcete tento pohyb na účtu zrušit?")
        if not cancel:
            return
        
        
        
    def load_old_orders(self):
        self.order_history['state'] = 'normal'
        self.order_history.delete("1.0", "end")
        
        payments = get_payment_list(self.customer_num)
        total = 0
        
        for payment in payments:
            pay_id, typ, stamp, pay_total, orders = payment
            
            if typ == "ORDER_PAYMENT":
                typ = "Objednávka"
            elif typ == "ADD_FUNDS":
                typ = "Nabití kreditu"
            elif typ == "REMOVE_FUNDS":
                typ = "Vybití kreditu"
                
            button = tk.Button(self.order_history, text="X", cursor="left_ptr",
                       bd=0, bg=self.order_history["bg"], fg="#a60000", highlightthickness=0,
                       command = lambda: self.delete_order(pay_id))
                       
            self.order_history.insert("end", stamp)
            self.order_history.window_create("end", window = button)
            text_out = "\n" +typ + "\n" + "------------\n"
            total += pay_total
            if orders:
                text_out += "\n".join(("%s\t\t%sx" % (order[0], order[1])  for order in orders))
                text_out += "\n------------\n"
            
            text_out += "Zůstatek %d (%+d)\n" % (total, pay_total)
            
            self.order_history.insert("end", text_out + "\n\n")
        
        self.order_history['state'] = 'disabled'
        self.order_history.see('end')

class Order(tk.Frame):
    def __init__(self, root, buttons):
        self.app = root;
        tk.Frame.__init__(self, root)
        
        button_font = tkFont.Font(family='Arial', size=22, weight="bold")
        
        info_area = tk.Frame(self)
        info_area.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="we")
        info_label = tk.Label(info_area, text="Zákazník:", font=button_font)
        info_label.pack(side="left")
        customer_label = self.customer_label = tk.Label(info_area, text="-", font=button_font)
        customer_label.pack(side="left")

        czk_label = tk.Label(info_area, text="Kč", font=button_font)
        czk_label.pack(side="right")
        money_label = self.money_label = tk.Label(info_area, text="-", font=button_font)
        money_label.pack(side="right")
        
        
        button_area = AutoGrid(self)
        button_area.grid(row=1, column=0, sticky='nsew')
        
        for i, (price, color) in enumerate(buttons):
            button=self.create_price_button(button_area, color, price)
            button.grid()

        prep_area = self.prep_area = tk.Text(self, width=25, borderwidth=0, highlightthickness=0, state="disabled", font=tkFont.Font(family='Courier', size=22));
        prep_area.grid(row=1, column=1, sticky='sn')
        
        finish_area = tk.Frame(self)
        finish_area.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="we")
        done_button=tk.Button(finish_area, text="Zaplatit", bg="#a3ffb3", font=button_font, command=self.done_button_callback)
        done_button.pack(side="right", fill="y")
        
        cancel_button=tk.Button(finish_area, text="Zrušit", bg="#ff9696", font=button_font, command=self.cancel_button_callback)
        cancel_button.pack(side="left", fill="y")
        self.bind('<Escape>', lambda _: self.cancel_button_callback())
        
        profile_button = tk.Button(finish_area, text="Profil", bg="#fffb80", command=self.profile_button_callback)
        profile_button.pack()
        
        
        
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        
        self.clear()
        
    def cancel_button_callback(self):
        if self.orders:
            cancel = tkmessagebox.askyesno(title="Zrušit objednávku", message="Opravdu chcete zrušit tuto objednávku?")
        else:
            cancel = True
            
        if cancel:
            self.clear()
            self.app.open_frame("MainPage")
        
    def done_button_callback(self):
        if not self.orders:
            self.bell()
            return
    
        money = get_money(self.customer_num)
        total = sum((x*y for x,y in self.orders.items()))
        
        mbox_text = "Zákazník si objednal za více, než kolik má nabito.\nChcete pokračovat v platbě? (Zákazníkovi se tím vytvoří dluh)"
        if total > money and not tkmessagebox.askyesno(title="Poračovat na dluh", message=mbox_text):
            return
        
        save_order(self.customer_num, self.orders)
        self.clear()
        self.app.open_frame("MainPage")
    
    def profile_button_callback(self):
        self.app.open_frame("EditProfile", self.customer_num, return_to="Order")
    
    def clear(self):
        self.customer_label["text"] = "-";
        self.money_label["text"] = "-"
        self.customer_num = -1
        self.orders = {}
        self.old_order_id = -1
        self.old_orders = ""
        self.redraw_orders()
    
    def returned_back(self, from_page):
        self.money_label["text"] = get_money(self.customer_num)
        self.focus_set()
    
    def setup(self, num, old_order=False):
        self.customer_num = num
        self.customer_label["text"] = self.customer_num
        self.money_label["text"] = get_money(self.customer_num)
        
        self.old_orders = ""
        
        self.focus_set()
    
    def redraw_orders(self):
        total = sum((x*y for x,y in self.orders.items()))
        text = '\n'.join(("%s\t\t%sx" % (val, num) for val, num in sorted(self.orders.items())))
        self.prep_area['state'] = 'normal'
        self.prep_area.delete("1.0", "end")
        self.prep_area.insert("1.0", self.old_orders + "Věci v objednávce:\n"+text+"\n-------------------\nCelkem: "+str(total))
        self.prep_area['state'] = 'disabled'
    
    
    def price_button_callback(self, value):
        self.orders[value] = self.orders.get(value, 0) + 1
        self.redraw_orders()

    def create_price_button(self, root, color, price):
        butt_size = 200
        button_frame = tk.Frame(root, height=butt_size, width=butt_size)
        price_button=tk.Button(button_frame)
        price_button.place(x=8, y=8, width=butt_size-16, height=butt_size-16)
        price_button["anchor"] = "center"
        price_button["bg"] = color
        price_button["font"] = tkFont.Font(family='Arial',size=37, weight="bold")
        price_button["fg"] = "#000000"
        price_button["justify"] = "center"
        price_button["text"] = str(price)
        price_button["relief"] = "raised"
        price_button["command"] = lambda: self.price_button_callback(price)
        return button_frame
     
class AutoGrid(tk.Frame):
    def __init__(self, root=None, **kwargs):
        tk.Frame.__init__(self, root, **kwargs)
        self.columns = None
        self.bind('<Configure>', self.regrid)

    def regrid(self, event=None):
        width = self.winfo_width()
        slaves = self.grid_slaves()
        max_width = max(slave.winfo_width() for slave in slaves)
        cols = width // max_width
        if cols == self.columns or cols < 1: # if the column number has not changed, abort
            return
        for slave in slaves:
            slave.grid_forget()
        for i, slave in enumerate(reversed(slaves)):
            slave.grid(row=i//cols, column=i%cols)
        self.columns = cols
     

def run_app():
    app = App()
    app.mainloop()
    
if __name__ == "__main__":
    run_app()