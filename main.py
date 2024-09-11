import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import numpy as np
from scipy.optimize import linprog
import matplotlib.pyplot as plt
import networkx as nx
import sqlite3
import threading


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Deniz Lojistik Optimizasyonu")

        # ttk Stili Uygulama
        style = ttk.Style()
        style.theme_use('clam')  # 'clam', 'alt', 'default', 'classic' gibi temalar kullanılabilir
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TLabel", padding=6, background="#333", foreground="#fff")
        style.configure("TEntry", padding=6, background="#f0f0f0")

        self.ships = []
        self.num_ships = 0
        self.supply_ports = []
        self.demand_ports = []

        self.create_widgets()
        self.create_database()

    def create_widgets(self):
        self.add_ship_button = ttk.Button(self.root, text="Gemi Ekle", command=self.add_ship)
        self.add_ship_button.grid(row=0, column=0, padx=10, pady=10)

        self.add_supply_button = ttk.Button(self.root, text="Liman Arzı Ekle", command=self.add_supply_port)
        self.add_supply_button.grid(row=0, column=1, padx=10, pady=10)

        self.add_demand_button = ttk.Button(self.root, text="Liman Talebi Ekle", command=self.add_demand_port)
        self.add_demand_button.grid(row=0, column=2, padx=10, pady=10)

        self.optimize_button = ttk.Button(self.root, text="Optimize Et", command=self.optimize)
        self.optimize_button.grid(row=0, column=3, padx=10, pady=10)

        self.help_button = ttk.Button(self.root, text="Yardım", command=self.show_help)
        self.help_button.grid(row=0, column=4, padx=10, pady=10)

        self.allocation_text = tk.Text(self.root, height=20, width=80)
        self.allocation_text.grid(row=1, column=0, columnspan=5, padx=10, pady=10)

        self.create_tables()

    def create_tables(self):
        self.ship_table = ttk.Treeview(self.root, columns=('Capacity', 'Fuel Cost'), show='headings')
        self.ship_table.heading('Capacity', text='Gemi Kapasitesi')
        self.ship_table.heading('Fuel Cost', text='Gemi Yakıt Maliyeti')
        self.ship_table.grid(row=2, column=0, padx=10, pady=10, columnspan=5)

        self.supply_table = ttk.Treeview(self.root, columns=('Supply',), show='headings')
        self.supply_table.heading('Supply', text='Liman Arzı')
        self.supply_table.grid(row=3, column=0, padx=10, pady=10, columnspan=2)

        self.demand_table = ttk.Treeview(self.root, columns=('Demand',), show='headings')
        self.demand_table.heading('Demand', text='Liman Talebi')
        self.demand_table.grid(row=3, column=2, padx=10, pady=10, columnspan=2)

    def create_database(self):
        conn = sqlite3.connect('logistics.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS ships (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            capacity INTEGER NOT NULL,
                            fuel_cost INTEGER NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ports (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            type TEXT NOT NULL,
                            quantity INTEGER NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS transport_costs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ship_id INTEGER,
                            supply_port_id INTEGER,
                            demand_port_id INTEGER,
                            cost INTEGER,
                            FOREIGN KEY(ship_id) REFERENCES ships(id),
                            FOREIGN KEY(supply_port_id) REFERENCES ports(id),
                            FOREIGN KEY(demand_port_id) REFERENCES ports(id))''')
        conn.commit()
        conn.close()

    def add_ship(self):
        new_ship_window = tk.Toplevel(self.root)
        new_ship_window.title("Yeni Gemi Ekle")

        ttk.Label(new_ship_window, text="Gemi Kapasitesi").grid(row=0, column=0)
        cap_entry = ttk.Entry(new_ship_window)
        cap_entry.grid(row=0, column=1)

        ttk.Label(new_ship_window, text="Gemi Yakıt Maliyeti").grid(row=1, column=0)
        fuel_entry = ttk.Entry(new_ship_window)
        fuel_entry.grid(row=1, column=1)

        def save_ship():
            try:
                capacity = int(cap_entry.get())
                fuel_cost = int(fuel_entry.get())
                if capacity <= 0 or fuel_cost <= 0:
                    raise ValueError("Kapasite ve yakıt maliyeti pozitif olmalıdır.")
                self.ships.append({"capacity": capacity, "fuel_cost": fuel_cost, "sailing_time": 10})
                self.num_ships += 1
                self.ship_table.insert('', 'end', values=(capacity, fuel_cost))
                self.add_ship_to_db(capacity, fuel_cost)
                new_ship_window.destroy()
                print(self.ships)
            except ValueError:
                messagebox.showerror("Input Error", "Geçersiz giriş. Lütfen pozitif sayısal değerler girin.")

        ttk.Button(new_ship_window, text="Kaydet", command=save_ship).grid(row=2, column=0, columnspan=2, pady=10)

    def add_supply_port(self):
        new_supply_window = tk.Toplevel(self.root)
        new_supply_window.title("Yeni Liman Arzı Ekle")

        ttk.Label(new_supply_window, text="Liman Arzı").grid(row=0, column=0)
        supply_entry = ttk.Entry(new_supply_window)
        supply_entry.grid(row=0, column=1)

        def save_supply():
            try:
                supply = int(supply_entry.get())
                if supply <= 0:
                    raise ValueError("Liman arzı pozitif olmalıdır.")
                self.supply_ports.append(supply)
                self.supply_table.insert('', 'end', values=(supply,))
                self.add_port_to_db(f"Supply {len(self.supply_ports)}", "supply", supply)
                new_supply_window.destroy()
            except ValueError:
                messagebox.showerror("Input Error", "Geçersiz giriş. Lütfen pozitif sayısal değerler girin.")

        ttk.Button(new_supply_window, text="Kaydet", command=save_supply).grid(row=1, column=0, columnspan=2, pady=10)

    def add_demand_port(self):
        new_demand_window = tk.Toplevel(self.root)
        new_demand_window.title("Yeni Liman Talebi Ekle")

        ttk.Label(new_demand_window, text="Liman Talebi").grid(row=0, column=0)
        demand_entry = ttk.Entry(new_demand_window)
        demand_entry.grid(row=0, column=1)

        def save_demand():
            try:
                demand = int(demand_entry.get())
                if demand <= 0:
                    raise ValueError("Liman talebi pozitif olmalıdır.")
                self.demand_ports.append(demand)
                self.demand_table.insert('', 'end', values=(demand,))
                self.add_port_to_db(f"Demand {len(self.demand_ports)}", "demand", demand)
                new_demand_window.destroy()
            except ValueError:
                messagebox.showerror("Input Error", "Geçersiz giriş. Lütfen pozitif sayısal değerler girin.")

        ttk.Button(new_demand_window, text="Kaydet", command=save_demand).grid(row=1, column=0, columnspan=2, pady=10)

    def add_ship_to_db(self, capacity, fuel_cost):
        conn = sqlite3.connect('logistics.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ships (capacity, fuel_cost) VALUES (?, ?)", (capacity, fuel_cost))
        conn.commit()
        conn.close()

    def add_port_to_db(self, name, type, quantity):
        conn = sqlite3.connect('logistics.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ports (name, type, quantity) VALUES (?, ?, ?)", (name, type, quantity))
        conn.commit()
        conn.close()

    def load_ships_from_db(self):
        conn = sqlite3.connect('logistics.db')
        cursor = conn.cursor()
        cursor.execute("SELECT capacity, fuel_cost FROM ships")
        rows = cursor.fetchall()
        for row in rows:
            self.ships.append({"capacity": row[0], "fuel_cost": row[1], "sailing_time": 10})
            self.ship_table.insert('', 'end', values=(row[0], row[1]))
        conn.close()

    def load_ports_from_db(self):
        conn = sqlite3.connect('logistics.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, type, quantity FROM ports")
        rows = cursor.fetchall()
        for row in rows:
            if row[1] == "supply":
                self.supply_ports.append(row[2])
                self.supply_table.insert('', 'end', values=(row[2],))
            elif row[1] == "demand":
                self.demand_ports.append(row[2])
                self.demand_table.insert('', 'end', values=(row[2],))
        conn.close()

    def optimize(self):
        threading.Thread(target=self.run_optimization).start()

    def run_optimization(self):
        try:
            if not self.ships or not self.supply_ports or not self.demand_ports:
                raise ValueError("Gemi ve liman verileri eksik.")

            total_supply = sum(self.supply_ports)
            total_demand = sum(self.demand_ports)
            total_nodes = len(self.supply_ports) + len(self.demand_ports)
            if total_supply > total_demand:
                self.demand_ports.append(total_supply - total_demand)
                total_nodes += 1
            elif total_demand > total_supply:
                self.supply_ports.append(total_demand - total_supply)
                total_nodes += 1

            # Nakliye maliyetlerini girdi olarak alma
            transport_costs = np.zeros((self.num_ships, len(self.supply_ports), len(self.demand_ports)))
            for i in range(self.num_ships):
                for j in range(len(self.supply_ports)):
                    for k in range(len(self.demand_ports)):
                        self.root.after(0, lambda i=i, j=j, k=k: self.ask_transport_cost(transport_costs, i, j, k))

            # Toplam maliyet fonksiyonu (nakliye maliyeti + yakıt maliyeti)
            total_costs = np.zeros_like(transport_costs)
            for i, ship in enumerate(self.ships):
                total_costs[i] = transport_costs[i] + ship["fuel_cost"]

            # Maliyet matrisini düz bir liste olarak tanımlayın
            c = total_costs.flatten()

            # Arz ve talep kısıtlamalarını tanımlayın
            num_suppliers = len(self.supply_ports)
            num_customers = len(self.demand_ports)
            num_ships = len(self.ships)
            num_vars_per_ship = num_suppliers * num_customers

            # Eşitlik kısıtlamaları matrisi ve vektörü
            A_eq = np.zeros((num_suppliers + num_customers, num_vars_per_ship * num_ships))
            b_eq = self.supply_ports + self.demand_ports

            # Arz kısıtlamaları
            for i in range(num_suppliers):
                for j in range(num_customers):
                    for k in range(num_ships):
                        A_eq[i, k * num_vars_per_ship + i * num_customers + j] = 1

            # Talep kısıtlamaları
            for j in range(num_customers):
                for i in range(num_suppliers):
                    for k in range(num_ships):
                        A_eq[num_suppliers + j, k * num_vars_per_ship + i * num_customers + j] = 1

            # Kapasite kısıtlamalarını tanımlayın
            A_ub = np.zeros((num_ships * num_vars_per_ship, num_vars_per_ship * num_ships))
            b_ub = []
            for k, ship in enumerate(self.ships):
                for i in range(num_vars_per_ship):
                    A_ub[k * num_vars_per_ship + i, k * num_vars_per_ship + i] = 1
                    b_ub.append(ship["capacity"])

            # Değişken sınırlarını tanımlayın
            x_bounds = [(0, None)] * (num_vars_per_ship * num_ships)

            # Doğrusal programlama problemini çözün (simplex yöntemi kullanarak)
            result = linprog(c, A_eq=A_eq, b_eq=b_eq, A_ub=A_ub, b_ub=b_ub, bounds=x_bounds, method='simplex')

            # Çözümün başarılı olup olmadığını kontrol edin
            if result.success:
                # Sonuçları yazdır ve veritabanına kaydet
                self.root.after(0, lambda: self.display_results(result))
                self.root.after(0, lambda: self.save_optimization_to_db(result))
            else:
                self.root.after(0, lambda: messagebox.showerror("Optimization Error", f"Optimization failed: {result.message}"))
        except ValueError as ve:
            self.root.after(0, lambda: messagebox.showerror("Input Error", str(ve)))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Unexpected Error", str(e)))

    def ask_transport_cost(self, transport_costs, i, j, k):
        cost = simpledialog.askinteger("Nakliye Maliyeti",
                                       f"Gemi {i + 1}, Liman {j + 1} -> Liman {k + 1}")
        if cost is None or cost < 0:
            raise ValueError("Geçersiz nakliye maliyeti girildi.")
        transport_costs[i, j, k] = cost

    def display_results(self, result):
        self.allocation_text.delete(1.0, tk.END)
        self.allocation_text.insert(tk.END, "Optimal Allocation (flat):\n")
        self.allocation_text.insert(tk.END, f"{result.x}\n")
        self.allocation_text.insert(tk.END, f"Total Cost: {result.fun}\n")

        print('result: ', result)
        print('result.x: ', result.x)


        # Tahsisatı matris biçiminde göstermek için dönüştürme
        allocation = result.x.reshape((self.num_ships, len(self.supply_ports), len(self.demand_ports)))
        for k, ship in enumerate(self.ships):
            self.allocation_text.insert(tk.END, f"Allocation for Ship {k + 1}:\n")
            self.allocation_text.insert(tk.END, f"{allocation[k]}\n")


        print(self.num_ships)
        print(self.supply_ports)
        print(self.demand_ports)


        # Gemiler nereden nereye iş yaptı?
        self.allocation_text.insert(tk.END, "\nGerçekleşen Seferler:\n")
        sayac = 0
        for i in range(self.num_ships):
            for j in range(len(self.supply_ports)):
                for k in range(len(self.demand_ports)):
                    # print(f"Gemi {i + 1}, Liman {j + 1} -> Liman {k + 1}")
                    if result.x[sayac] != 0.0:
                        self.allocation_text.insert(tk.END, f"Gemi {i + 1}, Liman {j + 1} -> Liman {k + 1} -> Değer: {result.x[sayac]} -> Optimal Allocation Index: {sayac}\n")
                    # print(result.x[sayac])
                    sayac += 1



        # Grafiksel gösterim
        self.plot_results(allocation)

        print(allocation)

    def plot_results(self, allocation):
        fig, ax = plt.subplots()
        G = nx.DiGraph()

        for k in range(allocation.shape[0]):
            for i in range(allocation.shape[1]):
                for j in range(allocation.shape[2]):
                    total_allocation = allocation[k, i, j]
                    if total_allocation > 0:
                        G.add_edge(f"Supply {i+1}", f"Demand {j+1}", weight=total_allocation, label=f"Ship {k+1}")

        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_size=7000, node_color="skyblue", font_size=10, font_weight="bold", ax=ax)
        labels = nx.get_edge_attributes(G, 'weight')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_color='red', ax=ax)

        plt.title('Limanlar Arası Tahsisat')
        plt.show()

    def save_optimization_to_db(self, result):
        try:
            conn = sqlite3.connect('logistics.db')
            cursor = conn.cursor()
            allocation = result.x.reshape((self.num_ships, len(self.supply_ports), len(self.demand_ports)))
            for k, ship in enumerate(self.ships):
                for i in range(len(self.supply_ports)):
                    for j in range(len(self.demand_ports)):
                        if allocation[k, i, j] > 0:
                            cursor.execute("INSERT INTO transport_costs (ship_id, supply_port_id, demand_port_id, cost) VALUES (?, ?, ?, ?)",
                                           (k + 1, i + 1, j + 1, allocation[k, i, j]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Data Saved", "Optimizasyon sonuçları başarıyla kaydedildi.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def show_help(self):
        help_text = """
        Deniz Lojistik Optimizasyonu Uygulaması Yardım:
        1. 'Gemi Ekle' butonuna basarak gemi ekleyin.
        2. 'Liman Arzı Ekle' butonuna basarak arz limanı ekleyin.
        3. 'Liman Talebi Ekle' butonuna basarak talep limanı ekleyin.
        4. 'Optimize Et' butonuna basarak optimizasyonu gerçekleştirin.
        """
        messagebox.showinfo("Yardım", help_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()





