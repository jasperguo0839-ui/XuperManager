import tkinter as tk
from tkinter import ttk, messagebox

from datetime import time

from utils.logger import setup_logger
from data.repository import DataRepository
from services.report_service import ReportService
from services.checkout_service import CheckoutService
from services.pricing_service import (
    PricingService,
    CategoryDiscountRule,
    TimeDiscountRule,
    MembershipDiscountRule,
    BulkQuantityRule,
)
from services.membership_service import compute_tier, find_customer
from models.cart import Cart

def parse_hh(hh_time_str: str) -> time:
    # "17:00" -> time(17,0)
    hour, minute = hh_time_str.split(":")
    return time(int(hour), int(minute))

class SupermarketApp:
    def __init__(self, root: tk.Tk):
        # core services / data 
        self.root = root
        self.root.title("Supermarket Management System")
        self.root.geometry("900x600")

        self.logger = setup_logger()
        self.repo = DataRepository()
        self.report_service = ReportService(self.repo)

        # PricingService with all discount strategies (same as main.py logic)
        self.pricing = PricingService()
        self.pricing.add_rule(CategoryDiscountRule({
            "Dairy": 0.10,
            "Bakery": 0.05
        }))
        self.pricing.add_rule(TimeDiscountRule(
            start_time=time(17, 0),
            end_time=time(18, 0),
            rate=0.05
        ))
        self.pricing.add_rule(MembershipDiscountRule({
            "REGULAR": 0.00,
            "SILVER":  0.02,
            "GOLD":    0.05,
            "VIP":     0.08
        }))
        self.pricing.add_rule(BulkQuantityRule(
            threshold=3,
            rate=0.05
        ))

        self.checkout_service = CheckoutService(self.repo, self.pricing)

        # One shared cart in memory
        self.cart = Cart()

        # notebook layout 
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # Each tab frame
        self.products_frame = ttk.Frame(self.notebook)
        self.inventory_frame = ttk.Frame(self.notebook)
        self.customers_frame = ttk.Frame(self.notebook) 
        self.cart_frame = ttk.Frame(self.notebook)
        self.report_frame = ttk.Frame(self.notebook)
        self.lowstock_frame = ttk.Frame(self.notebook)
        self.promotions_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.products_frame, text="Products")
        self.notebook.add(self.inventory_frame, text="Inventory")
        self.notebook.add(self.customers_frame, text="Customers")
        self.notebook.add(self.cart_frame, text="Cart & Checkout")
        self.notebook.add(self.report_frame, text="Reports")
        self.notebook.add(self.lowstock_frame, text="Low Stock")
        self.notebook.add(self.promotions_frame, text="Promotions")

        # Build each tab UI
        self.build_products_tab()
        self.build_inventory_tab()
        self.build_customers_tab() 
        self.build_cart_tab()
        self.build_report_tab()
        self.build_lowstock_tab()
        self.build_promotions_tab()  

        # initial fills
        self.refresh_products_table()
        self.refresh_inventory_table()
        self.refresh_customers_table() 
        self.refresh_lowstock_list()
        self.refresh_report()
        self.refresh_promotions_fields()

    # Utility funcs
    def _load_pricing_from_promotions(self):
        """
        Read current promotions from repo (promotions.json),
        rebuild PricingService with those parameters,
        update checkout_service.
        """
        promo = self.repo.get_promotions()

        cat_discounts = promo["category_discounts"]
        hh_cfg = promo["happy_hour"]
        bulk_cfg = promo["bulk"]

        # Rebuild pricing
        pricing = PricingService()
        # Category discounts (e.g. {"Dairy":0.10})
        pricing.add_rule(CategoryDiscountRule(cat_discounts))

        # Time discount (happy hour)
        start_t = parse_hh(hh_cfg["start"])
        end_t = parse_hh(hh_cfg["end"])
        pricing.add_rule(TimeDiscountRule(
            start_time=start_t,
            end_time=end_t,
            rate=hh_cfg["rate"]
        ))

        # Membership rule stays fixed (you probably don't want manager to edit this)
        pricing.add_rule(MembershipDiscountRule({
            "REGULAR": 0.00,
            "SILVER":  0.02,
            "GOLD":    0.05,
            "VIP":     0.08
        }))

        # Bulk discount
        pricing.add_rule(BulkQuantityRule(
            threshold=bulk_cfg["threshold"],
            rate=bulk_cfg["rate"]
        ))

        # Swap in the new pricing + checkout service
        self.pricing = pricing
        self.checkout_service = CheckoutService(self.repo, self.pricing)

        # Good for logging and debugging
        self.logger.info(f"GUI: promotions loaded. Category={cat_discounts}, "
                         f"HH={hh_cfg}, Bulk={bulk_cfg}")
        
    def load_products_inventory(self):
        products = self.repo.get_products()
        inventory = self.repo.get_inventory()
        return products, inventory

    def load_products_map_inventory(self):
        products = self.repo.get_products()
        inventory = self.repo.get_inventory()
        products_map = {p["sku"]: p for p in products}
        return products, products_map, inventory

    # TAB 1: PRODUCTS 

    def build_products_tab(self):
        top_frame = ttk.LabelFrame(self.products_frame, text="Product List")
        top_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("sku", "name", "cat", "price", "active")
        self.products_tree = ttk.Treeview(
            top_frame,
            columns=columns,
            show="headings",
            height=12
        )
        self.products_tree.heading("sku", text="SKU")
        self.products_tree.heading("name", text="Name")
        self.products_tree.heading("cat", text="Category")
        self.products_tree.heading("price", text="Price")
        self.products_tree.heading("active", text="Active")
        self.products_tree.column("sku", width=120)
        self.products_tree.column("name", width=200)
        self.products_tree.column("cat", width=120)
        self.products_tree.column("price", width=80, anchor="e")
        self.products_tree.column("active", width=80, anchor="center")
        self.products_tree.pack(fill="both", expand=True, padx=5, pady=5)

        refresh_btn = ttk.Button(
            top_frame,
            text="Refresh",
            command=self.refresh_products_table
        )
        refresh_btn.pack(pady=(0,5))

        # Add product section
        add_frame = ttk.LabelFrame(self.products_frame, text="Add New Product")
        add_frame.pack(fill="x", padx=10, pady=(0,10))

        ttk.Label(add_frame, text="SKU:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(add_frame, text="Name:").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        ttk.Label(add_frame, text="Category:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(add_frame, text="Price:").grid(row=1, column=2, sticky="e", padx=5, pady=5)

        self.add_sku_entry = ttk.Entry(add_frame, width=20)
        self.add_name_entry = ttk.Entry(add_frame, width=20)
        self.add_cat_entry = ttk.Entry(add_frame, width=20)
        self.add_price_entry = ttk.Entry(add_frame, width=10)

        self.add_sku_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.add_name_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.add_cat_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.add_price_entry.grid(row=1, column=3, sticky="w", padx=5, pady=5)

        add_btn = ttk.Button(
            add_frame,
            text="Add Product",
            command=self.gui_add_product
        )
        add_btn.grid(row=0, column=4, rowspan=2, sticky="w", padx=10, pady=5)

    def refresh_products_table(self):
        for row in self.products_tree.get_children():
            self.products_tree.delete(row)

        products, _ = self.load_products_inventory()
        for p in products:
            self.products_tree.insert(
                "",
                "end",
                values=(
                    p["sku"],
                    p["name"],
                    p.get("category", ""),
                    f"${p['price']:.2f}",
                    "Yes" if p.get("active", True) else "No"
                )
            )
        self.logger.info("GUI: refreshed products table")

    def gui_add_product(self):
        sku = self.add_sku_entry.get().strip()
        name = self.add_name_entry.get().strip()
        cat = self.add_cat_entry.get().strip()
        price_str = self.add_price_entry.get().strip()

        if not sku or not name or not cat or not price_str:
            messagebox.showerror("Error", "All fields are required.")
            return

        try:
            price = float(price_str)
        except ValueError:
            messagebox.showerror("Error", "Price must be a number.")
            return

        products = self.repo.get_products()
        # check for duplicate SKU
        for p in products:
            if p["sku"] == sku:
                messagebox.showerror("Error", f"SKU {sku} already exists.")
                return

        new_product = {
            "sku": sku,
            "name": name,
            "category": cat,
            "price": price,
            "active": True
        }
        products.append(new_product)
        self.repo.save_products(products)

        self.logger.info(
            f"GUI: added new product {sku} ({name}), "
            f"price={price}, category={cat}"
        )

        # clear fields
        self.add_sku_entry.delete(0, tk.END)
        self.add_name_entry.delete(0, tk.END)
        self.add_cat_entry.delete(0, tk.END)
        self.add_price_entry.delete(0, tk.END)

        # refresh UI table
        self.refresh_products_table()
        messagebox.showinfo("Success", "Product added.")

    # TAB 2: INVENTORY (stock table & update)

    def build_inventory_tab(self):
        # Create the top section of the tab for displaying current inventory
        inv_top = ttk.LabelFrame(self.inventory_frame, text="Inventory")
        inv_top.pack(fill="both", expand=True, padx=10, pady=10)

        # Define table columns: SKU, Product Name, and Stock Quantity
        columns = ("sku", "name", "stock")

        # Create the Treeview (table widget) to show inventory items
        self.inventory_tree = ttk.Treeview(
            inv_top,
            columns=columns,
            show="headings",   # show only column headings (no default tree column)
            height=12          # number of visible rows
        )

        # Set column headers (title for each column)
        self.inventory_tree.heading("sku", text="SKU")
        self.inventory_tree.heading("name", text="Name")
        self.inventory_tree.heading("stock", text="Stock")

        # Define column widths and alignment
        self.inventory_tree.column("sku", width=120)
        self.inventory_tree.column("name", width=200)
        self.inventory_tree.column("stock", width=80, anchor="center")

        # Pack the table widget into the window (make it fill the space)
        self.inventory_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Create a "Refresh" button to reload inventory data from storage
        refresh_btn = ttk.Button(
            inv_top,
            text="Refresh",
            command=self.refresh_inventory_table  # when clicked, refresh table
        )
        refresh_btn.pack(pady=(0,5))

        # Create the bottom section for updating stock quantities
        inv_bottom = ttk.LabelFrame(self.inventory_frame, text="Update Stock (+/-)")
        inv_bottom.pack(fill="x", padx=10, pady=(0,10))

        # Label for SKU input field
        ttk.Label(inv_bottom, text="SKU:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        # Label for quantity change input field
        ttk.Label(inv_bottom, text="Change (+/-):").grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # Text entry where the user types the SKU to update
        self.inv_sku_entry = ttk.Entry(inv_bottom, width=20)
        # Text entry for quantity change (can be positive or negative)
        self.inv_delta_entry = ttk.Entry(inv_bottom, width=10)

        # Position the entry boxes inside the grid layout
        self.inv_sku_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.inv_delta_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        # Create "Apply" button to apply the stock change
        update_btn = ttk.Button(
            inv_bottom,
            text="Apply",
            command=self.gui_update_inventory  # when clicked, update inventory
        )
        update_btn.grid(row=0, column=4, sticky="w", padx=10, pady=5)

    def refresh_inventory_table(self):
        for row in self.inventory_tree.get_children():
            self.inventory_tree.delete(row)

        products, inventory = self.load_products_inventory()
        for p in products:
            sku = p["sku"]
            stock = inventory.get(sku, 0)
            self.inventory_tree.insert(
                "",
                "end",
                values=(sku, p["name"], stock)
            )

        self.logger.info("GUI: refreshed inventory table")

    def gui_update_inventory(self):
        sku = self.inv_sku_entry.get().strip()
        delta_str = self.inv_delta_entry.get().strip()

        if not sku or not delta_str:
            messagebox.showerror("Error", "Please provide SKU and change amount.")
            return

        try:
            delta = int(delta_str)
        except ValueError:
            messagebox.showerror("Error", "Change must be an integer.")
            return

        inventory = self.repo.get_inventory()
        current_qty = inventory.get(sku, 0)
        new_qty = current_qty + delta

        if new_qty < 0:
            messagebox.showerror(
                "Error",
                f"Stock cannot go below zero (current {current_qty}, delta {delta})."
            )
            self.logger.warning(
                f"GUI: inventory update rejected for {sku}, "
                f"delta={delta}, would go negative."
            )
            return

        inventory[sku] = new_qty
        self.repo.save_inventory(inventory)

        self.logger.info(
            f"GUI: inventory updated {sku}, delta={delta}, new_stock={new_qty}"
        )

        # Clear input fields
        self.inv_sku_entry.delete(0, tk.END)
        self.inv_delta_entry.delete(0, tk.END)

        # Refresh table
        self.refresh_inventory_table()
        messagebox.showinfo("Success", "Inventory updated.")
    
    # TAB 3: CUSTOMERS (view + add new customer)

    def build_customers_tab(self):
        outer = ttk.LabelFrame(self.customers_frame, text="Customers")
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        # top: table of existing customers
        table_frame = ttk.Frame(outer)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("customer_id", "name", "spend", "tier")
        self.customers_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10
        )
        self.customers_tree.heading("customer_id", text="Customer ID")
        self.customers_tree.heading("name", text="Name")
        self.customers_tree.heading("spend", text="Lifetime Spend")
        self.customers_tree.heading("tier", text="Tier")

        self.customers_tree.column("customer_id", width=150)
        self.customers_tree.column("name", width=200)
        self.customers_tree.column("spend", width=120, anchor="e")
        self.customers_tree.column("tier", width=100, anchor="center")

        self.customers_tree.pack(fill="both", expand=True)

        refresh_btn = ttk.Button(
            outer,
            text="Refresh Customers",
            command=self.refresh_customers_table
        )
        refresh_btn.pack(pady=(0,10))

        # bottom: add new customer
        add_frame = ttk.LabelFrame(outer, text="Add New Customer")
        add_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(add_frame, text="Customer ID:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(add_frame, text="Name:").grid(row=0, column=2, sticky="e", padx=5, pady=5)

        self.new_customer_id_entry = ttk.Entry(add_frame, width=20)
        self.new_customer_name_entry = ttk.Entry(add_frame, width=20)

        self.new_customer_id_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.new_customer_name_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        add_btn = ttk.Button(
            add_frame,
            text="Register Customer",
            command=self.gui_add_customer
        )
        add_btn.grid(row=0, column=4, sticky="w", padx=10, pady=5)

    def refresh_customers_table(self):
        # Clear table first
        for row in self.customers_tree.get_children():
            self.customers_tree.delete(row)

        customers = self.repo.get_customers()

        # In case customers.json is empty or missing
        if not customers:
            self.logger.info("GUI: refreshed customers table (no customers yet)")
            return

        for c in customers:
            cust_id = c.get("customer_id", "")
            name = c.get("name", "")
            spend = c.get("lifetime_spend", 0.0)
            tier = c.get("tier", "REGULAR")
            self.customers_tree.insert(
                "",
                "end",
                values=(cust_id, name, f"${spend:.2f}", tier)
            )

        self.logger.info("GUI: refreshed customers table")

    def gui_add_customer(self):
        """
        Explicit 'register customer' action.
        This is what you asked for.
        """
        cust_id = self.new_customer_id_entry.get().strip()
        name = self.new_customer_name_entry.get().strip()

        if not cust_id or not name:
            messagebox.showerror("Error", "Please enter both Customer ID and Name.")
            return

        customers = self.repo.get_customers()

        # Check if this ID already exists
        for c in customers:
            if c["customer_id"] == cust_id:
                messagebox.showerror("Error", "That Customer ID already exists.")
                return

        # New customer starts with no spend and base tier REGULAR
        new_customer = {
            "customer_id": cust_id,
            "name": name,
            "lifetime_spend": 0.0,
            "tier": "REGULAR"
        }
        customers.append(new_customer)
        self.repo.save_customers(customers)

        self.logger.info(
            f"GUI: registered new customer {cust_id} ({name})"
        )

        # Clear entry fields
        self.new_customer_id_entry.delete(0, tk.END)
        self.new_customer_name_entry.delete(0, tk.END)

        # Refresh table to show new customer
        self.refresh_customers_table()
        messagebox.showinfo("Success", "Customer registered.")

    # TAB 4: CART & CHECKOUT

    def build_cart_tab(self):
        # top: cart table
        cart_top = ttk.LabelFrame(self.cart_frame, text="Current Cart")
        cart_top.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("sku", "qty")
        self.cart_tree = ttk.Treeview(
            cart_top,
            columns=columns,
            show="headings",
            height=8
        )
        self.cart_tree.heading("sku", text="SKU")
        self.cart_tree.heading("qty", text="Qty")
        self.cart_tree.column("sku", width=150)
        self.cart_tree.column("qty", width=80, anchor="center")
        self.cart_tree.pack(fill="both", expand=True, padx=5, pady=5)

        cart_refresh_btn = ttk.Button(
            cart_top,
            text="Refresh Cart View",
            command=self.refresh_cart_table
        )
        cart_refresh_btn.pack(pady=(0,5))

        # middle: add to cart
        cart_mid = ttk.LabelFrame(self.cart_frame, text="Add Item to Cart")
        cart_mid.pack(fill="x", padx=10, pady=(0,10))

        ttk.Label(cart_mid, text="SKU:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(cart_mid, text="Quantity:").grid(row=0, column=2, sticky="e", padx=5, pady=5)

        self.cart_sku_entry = ttk.Entry(cart_mid, width=20)
        self.cart_qty_entry = ttk.Entry(cart_mid, width=10)

        self.cart_sku_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.cart_qty_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        add_to_cart_btn = ttk.Button(
            cart_mid,
            text="Add to Cart",
            command=self.gui_add_to_cart
        )
        add_to_cart_btn.grid(row=0, column=4, sticky="w", padx=10, pady=5)

        # bottom: checkout (membership aware)
        cart_bottom = ttk.LabelFrame(self.cart_frame, text="Checkout")
        cart_bottom.pack(fill="x", padx=10, pady=(0,10))

        ttk.Label(cart_bottom, text="Customer ID:").grid(row=0, column=0, sticky="e", padx=5, pady=5)

        self.customer_id_entry = ttk.Entry(cart_bottom, width=20)
        self.customer_id_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        checkout_btn = ttk.Button(
            cart_bottom,
            text="Checkout Now",
            command=self.gui_checkout
        )
        checkout_btn.grid(row=0, column=2, sticky="w", padx=15, pady=5)

    def refresh_cart_table(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)

        for item in self.cart.items:
            self.cart_tree.insert(
                "",
                "end",
                values=(item.sku, item.qty)
            )

        self.logger.info("GUI: refreshed cart table")

    def gui_add_to_cart(self):
        sku = self.cart_sku_entry.get().strip()
        qty_str = self.cart_qty_entry.get().strip()

        if not sku or not qty_str:
            messagebox.showerror("Error", "Please provide SKU and quantity.")
            return

        try:
            qty = int(qty_str)
        except ValueError:
            messagebox.showerror("Error", "Quantity must be an integer.")
            return
        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be positive.")
            return

        # Add to cart (no stock check here; we'll do it on checkout)
        self.cart.add(sku, qty)
        self.logger.info(f"GUI: cart add {sku} x {qty}")

        # Clear inputs
        self.cart_sku_entry.delete(0, tk.END)
        self.cart_qty_entry.delete(0, tk.END)

        self.refresh_cart_table()
        messagebox.showinfo("Success", "Item added to cart.")

    def gui_checkout(self):
        """
        - Look up / create customer
        - Determine tier from lifetime_spend
        - Run checkout via CheckoutService (which applies pricing rules)
        - Update spend and tier in customers.json
        - Clear cart
        - Show summary
        """
        customer_id = self.customer_id_entry.get().strip()
        if not customer_id:
            messagebox.showerror("Error", "Please enter Customer ID.")
            return

        products, products_map, inventory = self.load_products_map_inventory()

        if not self.cart.items:
            messagebox.showerror("Error", "Cart is empty.")
            return

        # Load customers and resolve membership tier
        customers = self.repo.get_customers()
        customer = find_customer(customers, customer_id)

        if customer is None:
            name = self.simple_prompt("New Customer", "Enter customer name:")
            if name is None or name.strip() == "":
                messagebox.showerror("Error", "Checkout cancelled (no name).")
                return
            customer = {
                "customer_id": customer_id,
                "name": name.strip(),
                "lifetime_spend": 0.0,
                "tier": "REGULAR"
            }
            customers.append(customer)
            self.logger.info(f"GUI: created new customer {customer_id} ({name})")

        # Determine tier from spend
        current_spend = customer.get("lifetime_spend", 0.0)
        current_tier = compute_tier(current_spend)
        customer["tier"] = current_tier

        # Do checkout
        try:
            order = self.checkout_service.checkout(
                self.cart,
                products_map,
                inventory,
                membership_tier=current_tier
            )
        except Exception as e:
            # checkout failed e.g. insufficient stock
            self.logger.exception(f"GUI: checkout failed: {e}")
            messagebox.showerror("Checkout Failed", str(e))
            return

        # Update spend and recompute tier
        new_spend = round(current_spend + order.total, 2)
        customer["lifetime_spend"] = new_spend
        new_tier = compute_tier(new_spend)
        customer["tier"] = new_tier

        # Save customer list and inventory updates
        self.repo.save_customers(customers)
        # inventory already saved by checkout_service via repo.save_inventory()

        self.logger.info(
            f"GUI: checkout success order_id={order.order_id}, total={order.total}, "
            f"customer={customer_id}, old_tier={current_tier}, new_tier={new_tier}, "
            f"spend_now={new_spend}"
        )

        # UI feedback: show receipt-style summary
        receipt_lines = [
            f"Order ID: {order.order_id}",
            f"Customer: {customer['name']} ({customer_id})",
            f"Previous Tier: {current_tier}",
            f"New Tier: {new_tier}",
            f"Total: ${order.total:.2f}",
            "",
            "Items:"
        ]
        for it in order.items:
            receipt_lines.append(
                f"- {it.sku} x {it.qty} @ ${it.unit_price:.2f} = ${it.subtotal:.2f}"
            )

        messagebox.showinfo("Checkout Complete", "\n".join(receipt_lines))

        # clear cart UI and entry
        self.refresh_cart_table()
        self.customer_id_entry.delete(0, tk.END)

    def simple_prompt(self, title: str, prompt: str) -> str | None:
        """
        Tiny blocking prompt implemented via a popup.
        Returns the entered string or None if cancelled.
        """
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry("300x120")
        ttk.Label(popup, text=prompt).pack(pady=10)

        text_var = tk.StringVar()
        entry = ttk.Entry(popup, textvariable=text_var)
        entry.pack(pady=5)
        entry.focus()

        result = {"value": None}

        def submit():
            result["value"] = text_var.get()
            popup.destroy()

        def cancel():
            result["value"] = None
            popup.destroy()

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="OK", command=submit).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side="left", padx=5)

        popup.grab_set()
        popup.wait_window()
        return result["value"]

    # TAB 5: REPORTS (revenue + top sellers)

    def build_report_tab(self):
        frame = ttk.LabelFrame(self.report_frame, text="Sales Summary")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.revenue_label = ttk.Label(frame, text="Total Revenue: $0.00", font=("Arial", 12, "bold"))
        self.revenue_label.pack(pady=10)

        self.topseller_label = ttk.Label(frame, text="Top 5 Products:\n(none)")
        self.topseller_label.pack(pady=10)

        refresh_btn = ttk.Button(
            frame,
            text="Refresh Report",
            command=self.refresh_report
        )
        refresh_btn.pack(pady=10)

    def refresh_report(self):
        summary = self.report_service.sales_summary()
        revenue = summary["revenue"]
        top5 = summary["top5"]

        self.logger.info(
            f"GUI: refreshed sales summary: revenue={revenue}, top5={top5}"
        )

        self.revenue_label.config(
            text=f"Total Revenue: ${revenue:.2f}"
        )

        if not top5:
            self.topseller_label.config(
                text="Top 5 Products:\n(no sales yet)"
            )
        else:
            lines = ["Top 5 Products:"]
            for rank, (sku, sold_qty) in enumerate(top5, start=1):
                lines.append(f"{rank}. {sku} - Sold {sold_qty}")
            self.topseller_label.config(text="\n".join(lines))

    # TAB 6: LOW STOCK

    def build_lowstock_tab(self):
        frame = ttk.LabelFrame(self.lowstock_frame, text="Low Stock Items")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.lowstock_listbox = tk.Listbox(frame, height=15)
        self.lowstock_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        refresh_btn = ttk.Button(
            frame,
            text="Refresh Low Stock",
            command=self.refresh_lowstock_list
        )
        refresh_btn.pack(pady=10)

    def refresh_lowstock_list(self):
        self.lowstock_listbox.delete(0, tk.END)

        inventory = self.repo.get_inventory()
        low_items = self.report_service.low_stock(inventory, threshold=5)

        self.logger.info(
            f"GUI: low stock check -> {low_items}"
        )

        if not low_items:
            self.lowstock_listbox.insert(tk.END, "All stock levels are healthy.")
        else:
            for sku, qty in low_items:
                self.lowstock_listbox.insert(
                    tk.END,
                    f"{sku}: {qty} left"
                )

    # TAB 7: PROMOTIONS (edit discount strategy)

    def build_promotions_tab(self):
        frame = ttk.LabelFrame(self.promotions_frame, text="Promotion Settings")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Section 1: Category Discount
        cat_frame = ttk.LabelFrame(frame, text="Category Discount")
        cat_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(cat_frame, text="Category:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(cat_frame, text="Discount Rate (0.10 for 10% off):").grid(row=0, column=2, sticky="e", padx=5, pady=5)

        self.promo_cat_name_entry = ttk.Entry(cat_frame, width=20)
        self.promo_cat_rate_entry = ttk.Entry(cat_frame, width=10)

        self.promo_cat_name_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.promo_cat_rate_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        add_cat_btn = ttk.Button(
            cat_frame,
            text="Set/Update Category Discount",
            command=self.gui_update_category_discount
        )
        add_cat_btn.grid(row=0, column=4, sticky="w", padx=10, pady=5)

        # Section 2: Happy Hour
        hh_frame = ttk.LabelFrame(frame, text="Happy Hour Discount")
        hh_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(hh_frame, text="Start (HH:MM):").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(hh_frame, text="End (HH:MM):").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        ttk.Label(hh_frame, text="Rate (0.05 = 5% off):").grid(row=1, column=0, sticky="e", padx=5, pady=5)

        self.hh_start_entry = ttk.Entry(hh_frame, width=10)
        self.hh_end_entry = ttk.Entry(hh_frame, width=10)
        self.hh_rate_entry = ttk.Entry(hh_frame, width=10)

        self.hh_start_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.hh_end_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.hh_rate_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Section 3: Bulk Discount
        bulk_frame = ttk.LabelFrame(frame, text="Bulk Purchase Discount")
        bulk_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(bulk_frame, text="Threshold (buy >= this many):").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(bulk_frame, text="Rate (0.05 = 5% off):").grid(row=0, column=2, sticky="e", padx=5, pady=5)

        self.bulk_threshold_entry = ttk.Entry(bulk_frame, width=10)
        self.bulk_rate_entry = ttk.Entry(bulk_frame, width=10)

        self.bulk_threshold_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.bulk_rate_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        # Apply Button
        apply_btn = ttk.Button(
            frame,
            text="Apply All Promotion Changes",
            command=self.gui_apply_promotions
        )
        apply_btn.pack(pady=15)

        # helper label / note
        self.promo_status_label = ttk.Label(frame, text="", foreground="gray")
        self.promo_status_label.pack()

    def refresh_promotions_fields(self):
        """
        Load promotions.json and populate GUI fields so the manager
        sees current settings.
        """
        promo = self.repo.get_promotions()

        # Category discount fields: we don't preload one single category,
        # because category_discounts is a dict of possibly many.
        # We'll just blank the input each time.
        self.promo_cat_name_entry.delete(0, tk.END)
        self.promo_cat_rate_entry.delete(0, tk.END)

        # Happy hour
        hh = promo["happy_hour"]
        self.hh_start_entry.delete(0, tk.END)
        self.hh_end_entry.delete(0, tk.END)
        self.hh_rate_entry.delete(0, tk.END)

        self.hh_start_entry.insert(0, hh["start"])
        self.hh_end_entry.insert(0, hh["end"])
        self.hh_rate_entry.insert(0, str(hh["rate"]))

        # Bulk
        bulk = promo["bulk"]
        self.bulk_threshold_entry.delete(0, tk.END)
        self.bulk_rate_entry.delete(0, tk.END)
        self.bulk_threshold_entry.insert(0, str(bulk["threshold"]))
        self.bulk_rate_entry.insert(0, str(bulk["rate"]))

        self.promo_status_label.config(text="Loaded current promotion settings.")
        self.logger.info("GUI: promotions fields refreshed")

    def gui_update_category_discount(self):
        # Update (or create) a category discount entry.
        # Doesn't immediately apply to PricingService; just updates promotions.json in memory.
        # The final Apply button will persist + reload engine.
        cat_name = self.promo_cat_name_entry.get().strip()
        rate_str = self.promo_cat_rate_entry.get().strip()

        if not cat_name or not rate_str:
            messagebox.showerror("Error", "Please fill category and rate.")
            return

        try:
            rate_val = float(rate_str)
        except ValueError:
            messagebox.showerror("Error", "Rate must be a number like 0.10.")
            return

        promo = self.repo.get_promotions()
        cat_discounts = promo.get("category_discounts", {})
        cat_discounts[cat_name] = rate_val
        promo["category_discounts"] = cat_discounts

        # save back to repo (but we haven't reloaded engine yet)
        self.repo.save_promotions(promo)

        self.logger.info(f"GUI: updated category discount {cat_name} -> {rate_val}")
        self.promo_status_label.config(text=f"Category '{cat_name}' set to {rate_val*100:.1f}% off")

        # clean just the fields for category input
        self.promo_cat_name_entry.delete(0, tk.END)
        self.promo_cat_rate_entry.delete(0, tk.END)

    def gui_apply_promotions(self):
        """
        Take all GUI fields (happy hour + bulk),
        write them into promotions.json,
        reload pricing service live.
        """
        promo = self.repo.get_promotions()

        # Update happy hour block
        start_val = self.hh_start_entry.get().strip()
        end_val = self.hh_end_entry.get().strip()
        rate_val = self.hh_rate_entry.get().strip()
        try:
            hh_rate = float(rate_val)
        except ValueError:
            messagebox.showerror("Error", "Happy Hour rate must be a number, e.g. 0.05")
            return
        promo["happy_hour"] = {
            "start": start_val,
            "end": end_val,
            "rate": hh_rate
        }

        # Update bulk block
        bulk_thresh_str = self.bulk_threshold_entry.get().strip()
        bulk_rate_str = self.bulk_rate_entry.get().strip()
        try:
            bulk_thresh = int(bulk_thresh_str)
            bulk_rate = float(bulk_rate_str)
        except ValueError:
            messagebox.showerror("Error", "Bulk threshold must be int, bulk rate must be float.")
            return
        promo["bulk"] = {
            "threshold": bulk_thresh,
            "rate": bulk_rate
        }

        # Save promotions.json
        self.repo.save_promotions(promo)

        # Reload pricing engine using new promotions
        self._load_pricing_from_promotions()

        self.logger.info("GUI: promotions applied and pricing reloaded")
        self.promo_status_label.config(text="Promotions applied.")
        messagebox.showinfo("Success", "New promotions are now active for checkout.")


def main():
    root = tk.Tk()
    app = SupermarketApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()