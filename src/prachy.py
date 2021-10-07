import tkinter as tk
import tkinter.messagebox as tkmessagebox
import tkinter.scrolledtext as tkscrolledtext
import tkinter.font as tkFont
import sqlite3, json, sys, dbutils
from config import schema
from cerberus import Validator

def only4Num(inStr, acttyp):
    if acttyp == '1': #insert
        if not inStr.isdigit() or len(inStr) > 4:
            return False
    return True


class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=22, family='Arial')
        self.title("Endurova kalkulačka peněz")
        self.wm_geometry("800x600")
        self.state('zoomed')
        
        self.config = {}
        try:
            with open("./config.json", encoding="utf-8") as infil:
                self.config = json.load(infil)
        except Exception as ex:
            print(ex)
            tkmessagebox.showerror(title="Chyba v nastavení", message="Při načítání config.json se objevila nějaká chyba\nZkontrolujte, že je všechno tak, jak má být.")
            sys.exit()
        
        # validate config
        val = Validator(schema)
        if not val.validate(self.config):
            tkmessagebox.showerror(title="Chyba v nastavení", message="Při načítání config.json se objevily chyby:\n" + str(val.errors)[:1024])
            sys.exit()
        
        self.config = val.normalized(self.config)
        
        print(self.config)
        
        dbutils.prepare_db()
        
        
        self.frames = {
            "MainPage": MainPage(self),
            "Order": Order(self),
            "EditProfile": EditProfile(self),
        }
        
        for frame in self.frames.values():
            frame.place(x=0, y=0, relwidth=1, relheight=1)
        
        self.open_frame("MainPage")
    

    
    def open_frame(self, name, *args, returned_from=False, **kwargs):
        frame = self.frames[name];
        if returned_from:
            ret = frame.returned_back(returned_from, *args, **kwargs)
        else:
            ret = frame.setup(*args, **kwargs)
        if ret is not False:
            frame.tkraise()


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
        
        info_area = self.info_area = CutomerTopPanel(self)
        info_area.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
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
        if self.return_to:
            self.app.open_frame(self.return_to, returned_from = "EditProfile")
        else:
            self.app.open_frame("MainPage")
        
    def add_funds_button_callback(self):
        value_add = self.input_funds.get()
        if not value_add:
            self.bell()
            return
        value_add = int(value_add)
        
        self.input_funds.delete(0, "end")
        dbutils.add_funds(self.customer_num, value_add)
        self.info_area.set_money(dbutils.get_money(self.customer_num))
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
        dbutils.remove_funds(self.customer_num, value)
        self.info_area.set_money(dbutils.get_money(self.customer_num))
        self.load_old_orders()

    
    def setup(self, customer_num, return_to=None):
        self.return_to = return_to
        self.customer_num = customer_num
        self.info_area.set_customer(customer_num)
        self.info_area.set_money(dbutils.get_money(customer_num))
        self.load_old_orders()
        
        self.focus_set()
    
    def clear(self):
        self.info_area.clear()
        self.customer_num = 0
        self.input_funds.delete(0, "end")
        
        self.order_history['state'] = 'normal'
        self.order_history.delete("1.0", "end")
        self.order_history['state'] = 'disabled'
        
    def delete_order(self, order_id):
        cancel = tkmessagebox.askyesno(title="Zrušení z historie", message="Opravdu chcete tento pohyb na účtu zrušit?")
        if not cancel:
            return
        
        dbutils.delete_payment(order_id)
        self.money_label["text"] = dbutils.get_money(self.customer_num)
        self.load_old_orders()
        
    def load_old_orders(self):
        self.order_history['state'] = 'normal'
        self.order_history.delete("1.0", "end")
        
        payments = dbutils.get_payment_list(self.customer_num)
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
                       command = lambda pay_id=pay_id: self.delete_order(pay_id))
                       
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
    def __init__(self, root):
        self.app = root;
        tk.Frame.__init__(self, root)
        
        button_font = tkFont.Font(family='Arial', size=24, weight="bold")
        
        info_area = self.info_area = CutomerTopPanel(self)
        info_area.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        button_area = AutoGrid(self)
        button_area.grid(row=1, column=0, sticky='nsew')
        
        for i, settings in enumerate(self.app.config["buttons"]):
            button=self.create_price_button(button_area, settings["color"], settings["value"], settings.get("text", None))
            button.grid()

        prep_area = self.prep_area = tk.Text(self, width=28, borderwidth=0, highlightthickness=0, state="disabled", font=tkFont.Font(family='Courier', size=22));
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
    
        money = dbutils.get_money(self.customer_num)
        total = sum((x*y for (_, x),y in self.orders.items()))
        
        mbox_text = "Zákazník si objednal za více, než kolik má nabito.\n Chcete pokračovat v platbě? (Zákazníkovi se tím vytvoří dluh)"
        if total > money and not tkmessagebox.askyesno(title="Poračovat na dluh", message=mbox_text):
            return
        
        dbutils.save_order(self.customer_num, self.orders)
        self.clear()
        self.app.open_frame("MainPage")
    
    def profile_button_callback(self):
        self.app.open_frame("EditProfile", self.customer_num, return_to="Order")
    
    def clear(self):
        self.info_area.clear();
        self.customer_num = -1
        self.orders = {}
        self.money = 0
        #self.old_order_id = -1
        #self.old_orders = ""
        self.redraw_orders()
    
    def returned_back(self, from_page):
        self.info_area.set_money(dbutils.get_money(self.customer_num))
        self.focus_set()
    
    def setup(self, num, old_order=False):
        self.customer_num = num
        self.money = dbutils.get_money(self.customer_num)
        self.info_area.set_customer(self.customer_num)
        self.info_area.set_money(self.money)
        
        #This is yet unused
        #self.old_orders = ""
        
        self.redraw_orders()
        
        self.focus_set()
    
    def remove_item(self, key):
        count = self.orders.get(key, 0) - 1
        if(count < 1):
            self.orders.pop(key)
        else:
            self.orders[key] = count
        self.redraw_orders()
        
        
    def redraw_orders(self):
        self.prep_area['state'] = 'normal'
        self.prep_area.delete("1.0", "end")
        
        total = sum((x*y for (_,x),y in self.orders.items()))
        
        self.prep_area.insert("end","Věci v objednávce:\n")
        
        for (name, val), num in sorted(self.orders.items()):
            key = (name, val)
            name = name.replace("\n", " ")
            if len(name) > 17:
                name = name[:10]+"..."
            text = f'{name:<17}{val:>4}{num:>3}x '
            self.prep_area.insert("end", text)
            button = tk.Button(self.prep_area, text="x", cursor="left_ptr",
                       bd=0, bg=self.prep_area["bg"], fg="#a60000", highlightthickness=0,
                       command = lambda key=key: self.remove_item(key))
            self.prep_area.window_create("end", window = button)
            self.prep_area.insert("end", "\n")
                       
            
        self.prep_area.insert("end", "-------------------\nCelkem: "+str(total)+"\nZůstatek: "+str(self.money-total))
        
        self.prep_area['state'] = 'disabled'
        self.prep_area.see('end')
    
    
    def price_button_callback(self, name, value):
        key = (name, value)
        self.orders[key] = self.orders.get(key, 0) + 1
        self.redraw_orders()

    def create_price_button(self, root, color, price, text=None):
        spacing = int(self.app.config["button.spacing"] / 2)
        butt_size = self.app.config["button.size"] 
        all_size = butt_size + spacing * 2;
        if text is None:
            font_size = 37
            text = str(price)
        else:
            font_size = 20
        
        button_frame = tk.Frame(root, height=all_size, width=all_size)
        price_button=tk.Button(button_frame)
        price_button.place(x=spacing, y=spacing, width=butt_size, height=butt_size)
        price_button["anchor"] = "center"
        price_button["bg"] = color
        price_button["font"] = tkFont.Font(family='Arial',size=font_size, weight="bold")
        price_button["fg"] = "#000000"
        price_button["justify"] = "center"
        price_button["text"] = text
        price_button["relief"] = "raised"
        price_button["command"] = lambda: self.price_button_callback(text, price)
        return button_frame

class CutomerTopPanel(tk.Frame):
    def __init__(self, root):
        tk.Frame.__init__(self, root)
        
        button_font = tkFont.Font(family='Arial', size=22, weight="bold")
        
        info_label = tk.Label(self, text="Zákazník:", font=button_font)
        info_label.pack(side="left")
        customer_label = self.customer_label = tk.Label(self, text="-", font=button_font)
        customer_label.pack(side="left")


        czk_label = tk.Label(self, text="Kč", font=button_font)
        czk_label.pack(side="right")
        money_label = self.money_label = tk.Label(self, text="-", font=button_font)
        money_label.pack(side="right")
        kredit_label = tk.Label(self, text="Kredit:", font=button_font)
        kredit_label.pack(side="right")
        
    def set_customer(self, text):
        self.customer_label["text"] = text;
    
    def set_money(self, text):
        self.money_label["text"] = text;
        
    def clear(self):
        self.customer_label["text"] = "-";
        self.money_label["text"] = "-";

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
