# classicmodels_app_openrouter.py
# Complete ClassicModels GUI Application with OpenRouter AI

import customtkinter as ctk
from tkinter import ttk, messagebox, scrolledtext
import mysql.connector
from mysql.connector import Error
import re
import requests
import json
from datetime import datetime
import threading

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ============================================================
# ✅ YOUR OPENROUTER API KEY
# ============================================================

OPENROUTER_API_KEY = "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"

# ============================================================
# ✅ CHOOSE YOUR AI MODEL
# ============================================================

AI_MODEL = "openai/gpt-3.5-turbo"

# ============================================================
# DATABASE MANAGER
# ============================================================

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.schema = {}
        self.connect()
        self.get_schema()
    
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                database='classicmodels',
                user='root',
                password='',
                charset='utf8mb4'
            )
            if self.connection.is_connected():
                print("✅ Connected to ClassicModels database")
        except Error as e:
            print(f"❌ Connection Error: {e}")
            messagebox.showerror(
                "Connection Error",
                "Could not connect to MySQL.\n\n"
                "Please check:\n"
                "1. XAMPP/WAMP is running\n"
                "2. MySQL service is started\n"
                "3. Database 'classicmodels' exists in phpMyAdmin\n"
                "4. Username: root, Password: (empty)"
            )
    
    def get_schema(self):
        try:
            query = """
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'classicmodels'
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """
            results = self.execute_query(query)
            
            self.schema = {}
            if results:
                for row in results:
                    table = row['TABLE_NAME']
                    if table not in self.schema:
                        self.schema[table] = []
                    self.schema[table].append({
                        'column': row['COLUMN_NAME'],
                        'type': row['DATA_TYPE']
                    })
            print(f"✅ Schema loaded: {len(self.schema)} tables")
            return self.schema
        except Exception as e:
            print(f"❌ Error loading schema: {e}")
            self.schema = {}
            return self.schema
    
    def get_schema_text(self):
        if not self.schema:
            return "No schema available"
        
        text = "Database Schema:\n"
        for table, columns in self.schema.items():
            text += f"\nTable: {table}\n"
            for col in columns:
                text += f"  - {col['column']} ({col['type']})\n"
        return text
    
    def execute_query(self, query, params=None):
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                self.connection.commit()
                return cursor.rowcount
        except Error as e:
            print(f"Query error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def get_customers(self):
        query = """
            SELECT customerNumber, customerName, contactLastName, contactFirstName, 
                   city, country, creditLimit 
            FROM customers 
            ORDER BY customerName
            LIMIT 50
        """
        return self.execute_query(query)
    
    def get_customer_details(self, customer_number):
        query = """
            SELECT c.*, e.firstName as salesRepFirstName, e.lastName as salesRepLastName
            FROM customers c
            LEFT JOIN employees e ON c.salesRepEmployeeNumber = e.employeeNumber
            WHERE c.customerNumber = %s
        """
        result = self.execute_query(query, (customer_number,))
        return result[0] if result else None
    
    def get_product_categories(self):
        query = "SELECT productLine FROM productlines ORDER BY productLine"
        return self.execute_query(query)
    
    def get_products_by_category(self, category):
        query = """
            SELECT productCode, productName, buyPrice, MSRP, quantityInStock
            FROM products
            WHERE productLine = %s
            ORDER BY productName
            LIMIT 30
        """
        return self.execute_query(query, (category,))
    
    def get_sales_summary(self):
        query = """
            SELECT p.productLine, 
                   COUNT(DISTINCT od.orderNumber) as orderCount,
                   SUM(od.quantityOrdered) as totalQuantity,
                   SUM(od.quantityOrdered * od.priceEach) as totalSales
            FROM products p
            JOIN orderdetails od ON p.productCode = od.productCode
            GROUP BY p.productLine
            ORDER BY totalSales DESC
        """
        return self.execute_query(query)
    
    def get_employee_hierarchy(self):
        query = """
            SELECT e.employeeNumber, e.firstName, e.lastName, e.jobTitle,
                   e.reportsTo, m.firstName as managerFirstName, 
                   m.lastName as managerLastName
            FROM employees e
            LEFT JOIN employees m ON e.reportsTo = m.employeeNumber
            ORDER BY e.jobTitle, e.lastName
        """
        return self.execute_query(query)
    
    def get_order_details(self, order_number):
        query = """
            SELECT od.productCode, p.productName, od.quantityOrdered, 
                   od.priceEach, (od.quantityOrdered * od.priceEach) as lineTotal
            FROM orderdetails od
            JOIN products p ON od.productCode = p.productCode
            WHERE od.orderNumber = %s
        """
        return self.execute_query(query, (order_number,))
    
    def get_recent_orders(self, limit=20):
        query = """
            SELECT o.orderNumber, o.orderDate, o.status, c.customerName,
                   COUNT(od.productCode) as itemCount,
                   SUM(od.quantityOrdered * od.priceEach) as total
            FROM orders o
            JOIN customers c ON o.customerNumber = c.customerNumber
            JOIN orderdetails od ON o.orderNumber = od.orderNumber
            GROUP BY o.orderNumber
            ORDER BY o.orderDate DESC
            LIMIT %s
        """
        return self.execute_query(query, (limit,))
    
    def search_products(self, search_term):
        query = """
            SELECT productCode, productName, productLine, 
                   buyPrice, MSRP, quantityInStock
            FROM products
            WHERE productName LIKE %s 
               OR productDescription LIKE %s
            LIMIT 30
        """
        search_pattern = f"%{search_term}%"
        return self.execute_query(query, (search_pattern, search_pattern))
    
    def search_customers_db(self, search_term):
        query = """
            SELECT customerNumber, customerName, contactFirstName, contactLastName,
                   city, country, creditLimit
            FROM customers
            WHERE customerName LIKE %s OR contactFirstName LIKE %s OR contactLastName LIKE %s
            LIMIT 50
        """
        search_pattern = f"%{search_term}%"
        return self.execute_query(query, (search_pattern, search_pattern, search_pattern))
    
    def get_qa_answers(self, question_type):
        qa_data = {
            "top_customers": """
                SELECT c.customerName, 
                       SUM(od.quantityOrdered * od.priceEach) as totalSpent,
                       COUNT(DISTINCT o.orderNumber) as orderCount
                FROM customers c
                JOIN orders o ON c.customerNumber = o.customerNumber
                JOIN orderdetails od ON o.orderNumber = od.orderNumber
                GROUP BY c.customerNumber
                ORDER BY totalSpent DESC
                LIMIT 10
            """,
            "best_selling_products": """
                SELECT p.productName, 
                       SUM(od.quantityOrdered) as totalSold,
                       SUM(od.quantityOrdered * od.priceEach) as revenue,
                       p.productLine as category
                FROM products p
                JOIN orderdetails od ON p.productCode = od.productCode
                GROUP BY p.productCode
                ORDER BY totalSold DESC
                LIMIT 10
            """,
            "sales_by_country": """
                SELECT c.country, 
                       COUNT(DISTINCT o.orderNumber) as orderCount,
                       SUM(od.quantityOrdered * od.priceEach) as totalSales,
                       COUNT(DISTINCT c.customerNumber) as customerCount
                FROM customers c
                JOIN orders o ON c.customerNumber = o.customerNumber
                JOIN orderdetails od ON o.orderNumber = od.orderNumber
                GROUP BY c.country
                ORDER BY totalSales DESC
            """,
            "employee_performance": """
                SELECT e.firstName, e.lastName, 
                       COUNT(DISTINCT o.orderNumber) as ordersHandled,
                       SUM(od.quantityOrdered * od.priceEach) as totalSales,
                       COUNT(DISTINCT c.customerNumber) as customersServed
                FROM employees e
                JOIN customers c ON e.employeeNumber = c.salesRepEmployeeNumber
                JOIN orders o ON c.customerNumber = o.customerNumber
                JOIN orderdetails od ON o.orderNumber = od.orderNumber
                GROUP BY e.employeeNumber
                ORDER BY totalSales DESC
            """,
            "monthly_sales": """
                SELECT DATE_FORMAT(orderDate, '%%Y-%%m') as month,
                       COUNT(DISTINCT orderNumber) as orderCount,
                       SUM(od.quantityOrdered * od.priceEach) as totalSales,
                       AVG(od.quantityOrdered * od.priceEach) as avgOrderValue
                FROM orders o
                JOIN orderdetails od ON o.orderNumber = od.orderNumber
                GROUP BY month
                ORDER BY month DESC
                LIMIT 12
            """,
            "product_categories_summary": """
                SELECT pl.productLine as category,
                       COUNT(p.productCode) as productCount,
                       AVG(p.buyPrice) as avgBuyPrice,
                       AVG(p.MSRP) as avgMSRP,
                       AVG(p.MSRP - p.buyPrice) as avgProfitMargin,
                       SUM(p.quantityInStock) as totalStock
                FROM productlines pl
                LEFT JOIN products p ON pl.productLine = p.productLine
                GROUP BY pl.productLine
                ORDER BY productCount DESC
            """,
            "order_status_summary": """
                SELECT status, 
                       COUNT(*) as orderCount,
                       SUM(od.quantityOrdered * od.priceEach) as totalValue,
                       AVG(od.quantityOrdered * od.priceEach) as avgOrderValue
                FROM orders o
                JOIN orderdetails od ON o.orderNumber = od.orderNumber
                GROUP BY status
                ORDER BY orderCount DESC
            """
        }
        return self.execute_query(qa_data.get(question_type, qa_data["top_customers"]))
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Database connection closed")


# ============================================================
# OPENROUTER AI HELPER
# ============================================================

class OpenRouterAI:
    def __init__(self, api_key, model="openai/gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.schema_text = ""
        self.initialized = False
        self.last_error = ""
        self.init_ai()
    
    def init_ai(self):
        if not self.api_key or self.api_key == "YOUR_OPENROUTER_API_KEY_HERE":
            self.last_error = "API key not set."
            self.initialized = False
            return
        
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "ClassicModels AI Assistant"
                },
                data=json.dumps({
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Say hello"}],
                    "max_tokens": 10
                }),
                timeout=30
            )
            
            if response.status_code == 200:
                self.initialized = True
                print(f"✅ AI initialized with model: {self.model}")
            else:
                self.last_error = f"Model failed. Status: {response.status_code}"
                self.initialized = False
                
        except Exception as e:
            self.last_error = f"Error: {str(e)}"
            self.initialized = False
    
    def set_schema(self, schema_text):
        self.schema_text = schema_text
    
    def generate_sql(self, question, db):
        if not self.initialized:
            return None, f"AI not initialized. {self.last_error}"
        
        try:
            prompt = f"""
You are a SQL expert. Convert the following natural language question into a MySQL SQL query.

Database Schema:
{self.schema_text}

Rules:
1. Only output the SQL query, no explanations
2. Use proper MySQL syntax
3. Use table and column names exactly as in the schema
4. For LIMIT queries, use sensible limits (default 10)
5. If the question asks for "top" or "best", use ORDER BY DESC and LIMIT
6. Return ONLY the SQL query

Question: {question}

SQL Query:
"""
            
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "ClassicModels AI Assistant"
                },
                data=json.dumps({
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.1
                }),
                timeout=60
            )
            
            if response.status_code != 200:
                return None, f"API Error: {response.status_code}"
            
            result = response.json()
            sql_query = result['choices'][0]['message']['content'].strip()
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            if not sql_query.upper().startswith('SELECT'):
                return None, "Not a SELECT statement"
            
            results = db.execute_query(sql_query)
            if results is None:
                return None, "Query execution failed"
            
            return sql_query, "Query generated successfully!"
            
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def generate_insight(self, question, results, sql_query):
        if not self.initialized or not results:
            return None
        
        try:
            result_summary = f"Results ({len(results)} rows):\n"
            if len(results) > 0:
                columns = list(results[0].keys())
                result_summary += f"Columns: {', '.join(columns)}\n"
                for i, row in enumerate(results[:5]):
                    result_summary += f"Row {i+1}: {row}\n"
                if len(results) > 5:
                    result_summary += f"... and {len(results) - 5} more rows\n"
            
            prompt = f"""
Based on the following database query results, provide a brief insight or summary (2-3 sentences):
Question: {question}
SQL Query: {sql_query}
{result_summary}

Insight:
"""
            
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "ClassicModels AI Assistant"
                },
                data=json.dumps({
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.5
                }),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                return None
            
        except Exception as e:
            return None


# ============================================================
# MAIN APPLICATION - WITH TABBED RESULTS
# ============================================================

class ClassicModelsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("ClassicModels Database Manager with AI")
        self.geometry("1500x850")
        self.minsize(1200, 700)
        
        self.db = DatabaseManager()
        self.ai = OpenRouterAI(OPENROUTER_API_KEY, AI_MODEL)
        if self.ai.initialized:
            self.ai.set_schema(self.db.get_schema_text())
        
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.create_sidebar()
        self.create_main_content()
        self.load_dashboard()
    
    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.main_container, width=230, corner_radius=10)
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))
        self.sidebar.pack_propagate(False)
        
        ctk.CTkLabel(
            self.sidebar, 
            text="🤖 ClassicModels", 
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(20, 30))
        
        nav_buttons = [
            ("🏠 Dashboard", self.load_dashboard),
            ("👥 Customers", self.load_customers),
            ("📦 Products", self.load_products),
            ("📝 Orders", self.load_orders),
            ("📈 Sales Summary", self.load_sales_summary),
            ("👔 Employees", self.load_employees),
            ("🔍 Search", self.load_search),
            ("❓ Predefined Q&A", self.load_qa),
            ("🤖 AI Ask Question", self.load_ai_qa)
        ]
        
        for text, command in nav_buttons:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                height=40,
                corner_radius=8,
                font=ctk.CTkFont(size=13)
            )
            btn.pack(pady=4, padx=10, fill="x")
        
        status_frame = ctk.CTkFrame(self.sidebar)
        status_frame.pack(side="bottom", fill="x", pady=10, padx=10)
        
        conn_status = "✅ Connected" if (self.db.connection and self.db.connection.is_connected()) else "❌ Disconnected"
        ctk.CTkLabel(status_frame, text=conn_status, font=ctk.CTkFont(size=12)).pack(pady=5)
        
        if self.ai.initialized:
            ai_status = f"🤖 AI: Ready ({self.ai.model})"
            ai_color = "lightgreen"
        else:
            ai_status = "🤖 AI: Not Available"
            ai_color = "red"
        
        ctk.CTkLabel(status_frame, text=ai_status, font=ctk.CTkFont(size=12), text_color=ai_color).pack(pady=5)
        
        ctk.CTkButton(
            status_frame,
            text="Exit",
            command=self.quit_app,
            fg_color="red",
            hover_color="darkred",
            height=35
        ).pack(pady=(0, 10), padx=10, fill="x")
    
    def create_main_content(self):
        self.content_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        self.content_frame.pack(side="right", fill="both", expand=True)
        
        self.header_label = ctk.CTkLabel(
            self.content_frame,
            text="Dashboard",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.header_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.content_area = ctk.CTkFrame(self.content_frame)
        self.content_area.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()
    
    def quit_app(self):
        self.db.close()
        self.quit()
    
    def load_dashboard(self):
        self.clear_content()
        self.header_label.configure(text="🏠 Dashboard")
        
        try:
            customers = self.db.get_customers()
            recent_orders = self.db.get_recent_orders(5)
            sales_summary = self.db.get_sales_summary()
            
            stats_frame = ctk.CTkFrame(self.content_area)
            stats_frame.pack(fill="x", pady=10)
            
            stats = [
                ("Total Customers", len(customers) if customers else 0, "👥"),
                ("Recent Orders", len(recent_orders) if recent_orders else 0, "📝"),
                ("Product Lines", len(sales_summary) if sales_summary else 0, "📦"),
                ("Total Sales", f"${sum(s['totalSales'] for s in sales_summary):,.2f}" if sales_summary else "$0", "💰")
            ]
            
            for i, (label, value, icon) in enumerate(stats):
                card = ctk.CTkFrame(stats_frame, corner_radius=10)
                card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
                stats_frame.grid_columnconfigure(i, weight=1)
                
                ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=30)).pack(pady=(10, 0))
                ctk.CTkLabel(card, text=str(value), font=ctk.CTkFont(size=28, weight="bold")).pack()
                ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=14)).pack(pady=(0, 10))
            
            if recent_orders:
                orders_frame = ctk.CTkFrame(self.content_area)
                orders_frame.pack(fill="both", expand=True, pady=20)
                
                ctk.CTkLabel(orders_frame, text="📋 Recent Orders", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(0, 10))
                
                tree_frame = ctk.CTkFrame(orders_frame)
                tree_frame.pack(fill="both", expand=True)
                
                tree = ttk.Treeview(
                    tree_frame,
                    columns=("Order #", "Date", "Customer", "Items", "Total", "Status"),
                    show="headings",
                    height=8
                )
                
                scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
                tree.configure(yscrollcommand=scrollbar.set)
                
                headings = [("Order #", 80), ("Date", 120), ("Customer", 200), ("Items", 60), ("Total", 120), ("Status", 100)]
                for col, width in headings:
                    tree.heading(col, text=col)
                    tree.column(col, width=width)
                
                for order in recent_orders:
                    tree.insert("", "end", values=(
                        order['orderNumber'],
                        order['orderDate'],
                        order['customerName'],
                        order['itemCount'],
                        f"${order['total']:,.2f}",
                        order['status']
                    ))
                
                tree.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading dashboard: {str(e)}")
    
    # ============================================================
    # CUSTOMERS
    # ============================================================
    
    def load_customers(self):
        self.clear_content()
        self.header_label.configure(text="👥 Customers")
        
        search_frame = ctk.CTkFrame(self.content_area)
        search_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(search_frame, width=300)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_customers())
        
        ctk.CTkButton(search_frame, text="🔍 Search", command=self.search_customers).pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="🔄 Show All", command=self.load_customers).pack(side="left", padx=5)
        
        tree_frame = ctk.CTkFrame(self.content_area)
        tree_frame.pack(fill="both", expand=True, pady=10)
        
        self.customer_tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Name", "Contact", "City", "Country", "Credit Limit"),
            show="headings"
        )
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.customer_tree.yview)
        self.customer_tree.configure(yscrollcommand=scrollbar.set)
        
        headings = [("ID", 60), ("Name", 200), ("Contact", 150), ("City", 120), ("Country", 120), ("Credit Limit", 100)]
        for col, width in headings:
            self.customer_tree.heading(col, text=col)
            self.customer_tree.column(col, width=width)
        
        customers = self.db.get_customers()
        if customers:
            for customer in customers:
                self.customer_tree.insert("", "end", values=(
                    customer['customerNumber'],
                    customer['customerName'],
                    f"{customer['contactFirstName']} {customer['contactLastName']}",
                    customer['city'],
                    customer['country'],
                    f"${customer['creditLimit']:,.2f}" if customer['creditLimit'] else "$0.00"
                ))
        
        self.customer_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.customer_tree.bind('<Double-Button-1>', self.on_customer_click)
    
    def search_customers(self):
        search_term = self.search_entry.get().strip()
        if not search_term:
            self.load_customers()
            return
        
        self.clear_content()
        self.header_label.configure(text=f"🔍 Search: {search_term}")
        
        results = self.db.search_customers_db(search_term)
        
        tree_frame = ctk.CTkFrame(self.content_area)
        tree_frame.pack(fill="both", expand=True, pady=10)
        
        tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Name", "Contact", "City", "Country", "Credit Limit"),
            show="headings"
        )
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        headings = [("ID", 60), ("Name", 200), ("Contact", 150), ("City", 120), ("Country", 120), ("Credit Limit", 100)]
        for col, width in headings:
            tree.heading(col, text=col)
            tree.column(col, width=width)
        
        if results:
            for customer in results:
                tree.insert("", "end", values=(
                    customer['customerNumber'],
                    customer['customerName'],
                    f"{customer['contactFirstName']} {customer['contactLastName']}",
                    customer['city'],
                    customer['country'],
                    f"${customer['creditLimit']:,.2f}" if customer['creditLimit'] else "$0.00"
                ))
            
            ctk.CTkLabel(self.content_area, text=f"Found {len(results)} customers", font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(0, 10))
        else:
            ctk.CTkLabel(self.content_area, text="No customers found", font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(0, 10))
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        tree.bind('<Double-Button-1>', self.on_customer_click)
    
    def on_customer_click(self, event):
        tree = event.widget
        selection = tree.selection()
        if selection:
            values = tree.item(selection[0])['values']
            self.show_customer_details(values[0])
    
    def show_customer_details(self, customer_id):
        details = self.db.get_customer_details(customer_id)
        if not details:
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Customer Details")
        dialog.geometry("500x500")
        dialog.grab_set()
        
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(info_frame, text=details['customerName'], font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 20))
        
        info_fields = [
            ("Contact", f"{details['contactFirstName']} {details['contactLastName']}"),
            ("Phone", details['phone']),
            ("Address", f"{details['addressLine1']} {details.get('addressLine2', '')}".strip()),
            ("City", details['city']),
            ("Country", details['country']),
            ("Credit Limit", f"${details['creditLimit']:,.2f}" if details['creditLimit'] else "$0.00")
        ]
        
        for label, value in info_fields:
            frame = ctk.CTkFrame(info_frame)
            frame.pack(fill="x", pady=3)
            ctk.CTkLabel(frame, text=f"{label}:", width=120, anchor="e").pack(side="left", padx=5)
            ctk.CTkLabel(frame, text=str(value), anchor="w").pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(dialog, text="Close", command=dialog.destroy).pack(pady=20)
    
    # ============================================================
    # PRODUCTS
    # ============================================================
    
    def load_products(self):
        self.clear_content()
        self.header_label.configure(text="📦 Products")
        
        filter_frame = ctk.CTkFrame(self.content_area)
        filter_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(filter_frame, text="Category:").pack(side="left", padx=5)
        
        categories = self.db.get_product_categories()
        category_values = [cat['productLine'] for cat in categories] if categories else []
        
        self.category_var = ctk.StringVar(value="All Categories")
        ctk.CTkOptionMenu(
            filter_frame,
            values=["All Categories"] + category_values,
            variable=self.category_var,
            command=self.filter_products
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(filter_frame, text="🔄 Refresh", command=self.load_products).pack(side="left", padx=5)
        
        tree_frame = ctk.CTkFrame(self.content_area)
        tree_frame.pack(fill="both", expand=True, pady=10)
        
        self.product_tree = ttk.Treeview(
            tree_frame,
            columns=("Code", "Name", "Category", "Buy Price", "MSRP", "Stock"),
            show="headings"
        )
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        
        headings = [("Code", 100), ("Name", 250), ("Category", 120), ("Buy Price", 80), ("MSRP", 80), ("Stock", 60)]
        for col, width in headings:
            self.product_tree.heading(col, text=col)
            self.product_tree.column(col, width=width)
        
        products = self.db.execute_query("""
            SELECT productCode, productName, productLine, buyPrice, MSRP, quantityInStock
            FROM products
            LIMIT 50
        """)
        
        if products:
            for product in products:
                self.product_tree.insert("", "end", values=(
                    product['productCode'],
                    product['productName'],
                    product['productLine'],
                    f"${product['buyPrice']:,.2f}",
                    f"${product['MSRP']:,.2f}",
                    product['quantityInStock']
                ))
        
        self.product_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def filter_products(self, category):
        if category == "All Categories":
            self.load_products()
        else:
            self.clear_content()
            self.header_label.configure(text=f"📦 {category}")
            
            tree_frame = ctk.CTkFrame(self.content_area)
            tree_frame.pack(fill="both", expand=True, pady=10)
            
            self.product_tree = ttk.Treeview(
                tree_frame,
                columns=("Code", "Name", "Category", "Buy Price", "MSRP", "Stock"),
                show="headings"
            )
            
            scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.product_tree.yview)
            self.product_tree.configure(yscrollcommand=scrollbar.set)
            
            headings = [("Code", 100), ("Name", 250), ("Category", 120), ("Buy Price", 80), ("MSRP", 80), ("Stock", 60)]
            for col, width in headings:
                self.product_tree.heading(col, text=col)
                self.product_tree.column(col, width=width)
            
            products = self.db.get_products_by_category(category)
            if products:
                for product in products:
                    self.product_tree.insert("", "end", values=(
                        product['productCode'],
                        product['productName'],
                        product['productLine'],
                        f"${product['buyPrice']:,.2f}",
                        f"${product['MSRP']:,.2f}",
                        product['quantityInStock']
                    ))
            
            self.product_tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
    
    # ============================================================
    # ORDERS
    # ============================================================
    
    def load_orders(self):
        self.clear_content()
        self.header_label.configure(text="📝 Orders")
        
        orders_frame = ctk.CTkFrame(self.content_area)
        orders_frame.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(orders_frame, text="Recent Orders", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(0, 10))
        
        tree_frame = ctk.CTkFrame(orders_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.order_tree = ttk.Treeview(
            tree_frame,
            columns=("Order #", "Date", "Customer", "Items", "Total", "Status"),
            show="headings",
            height=15
        )
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.order_tree.yview)
        self.order_tree.configure(yscrollcommand=scrollbar.set)
        
        headings = [("Order #", 80), ("Date", 120), ("Customer", 200), ("Items", 60), ("Total", 120), ("Status", 100)]
        for col, width in headings:
            self.order_tree.heading(col, text=col)
            self.order_tree.column(col, width=width)
        
        orders = self.db.get_recent_orders(50)
        if orders:
            for order in orders:
                self.order_tree.insert("", "end", values=(
                    order['orderNumber'],
                    order['orderDate'],
                    order['customerName'],
                    order['itemCount'],
                    f"${order['total']:,.2f}",
                    order['status']
                ))
        
        self.order_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.order_tree.bind('<Double-Button-1>', self.on_order_click)
    
    def on_order_click(self, event):
        tree = event.widget
        selection = tree.selection()
        if selection:
            values = tree.item(selection[0])['values']
            self.show_order_details(values[0])
    
    def show_order_details(self, order_id):
        details = self.db.get_order_details(order_id)
        if not details:
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Order #{order_id}")
        dialog.geometry("700x500")
        dialog.grab_set()
        
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(info_frame, text=f"Order #{order_id}", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        
        tree_frame = ctk.CTkFrame(dialog)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        tree = ttk.Treeview(
            tree_frame,
            columns=("Product Code", "Product Name", "Quantity", "Price Each", "Line Total"),
            show="headings"
        )
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        headings = [("Product Code", 100), ("Product Name", 250), ("Quantity", 60), ("Price Each", 100), ("Line Total", 120)]
        for col, width in headings:
            tree.heading(col, text=col)
            tree.column(col, width=width)
        
        total = 0
        for item in details:
            tree.insert("", "end", values=(
                item['productCode'],
                item['productName'],
                item['quantityOrdered'],
                f"${item['priceEach']:,.2f}",
                f"${item['lineTotal']:,.2f}"
            ))
            total += item['lineTotal']
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ctk.CTkLabel(dialog, text=f"Order Total: ${total:,.2f}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkButton(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    # ============================================================
    # SALES SUMMARY
    # ============================================================
    
    def load_sales_summary(self):
        self.clear_content()
        self.header_label.configure(text="📈 Sales Summary")
        
        summary = self.db.get_sales_summary()
        if not summary:
            ctk.CTkLabel(self.content_area, text="No sales data available", font=ctk.CTkFont(size=16)).pack(pady=50)
            return
        
        summary_frame = ctk.CTkFrame(self.content_area)
        summary_frame.pack(fill="both", expand=True, pady=10)
        
        tree = ttk.Treeview(
            summary_frame,
            columns=("Product Line", "Orders", "Total Quantity", "Total Sales", "Avg Order Value"),
            show="headings"
        )
        
        scrollbar = ttk.Scrollbar(summary_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        headings = [("Product Line", 150), ("Orders", 80), ("Total Quantity", 100), ("Total Sales", 150), ("Avg Order Value", 120)]
        for col, width in headings:
            tree.heading(col, text=col)
            tree.column(col, width=width)
        
        total_sales = 0
        for item in summary:
            avg = item['totalSales'] / item['orderCount'] if item['orderCount'] > 0 else 0
            tree.insert("", "end", values=(
                item['productLine'],
                item['orderCount'],
                item['totalQuantity'],
                f"${item['totalSales']:,.2f}",
                f"${avg:,.2f}"
            ))
            total_sales += item['totalSales']
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        stats_frame = ctk.CTkFrame(self.content_area)
        stats_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(stats_frame, text=f"Total Sales: ${total_sales:,.2f}", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=20)
        ctk.CTkLabel(stats_frame, text=f"Product Lines: {len(summary)}", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=20)
    
    # ============================================================
    # EMPLOYEES
    # ============================================================
    
    def load_employees(self):
        self.clear_content()
        self.header_label.configure(text="👔 Employees")
        
        employees = self.db.get_employee_hierarchy()
        if not employees:
            ctk.CTkLabel(self.content_area, text="No employee data", font=ctk.CTkFont(size=16)).pack(pady=50)
            return
        
        tree_frame = ctk.CTkFrame(self.content_area)
        tree_frame.pack(fill="both", expand=True, pady=10)
        
        tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Name", "Job Title", "Reports To"),
            show="headings",
            height=20
        )
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        headings = [("ID", 80), ("Name", 200), ("Job Title", 200), ("Reports To", 200)]
        for col, width in headings:
            tree.heading(col, text=col)
            tree.column(col, width=width)
        
        for emp in employees:
            reports_to = f"{emp.get('managerFirstName', '')} {emp.get('managerLastName', '')}".strip()
            if not reports_to:
                reports_to = "CEO/President"
            
            tree.insert("", "end", values=(
                emp['employeeNumber'],
                f"{emp['firstName']} {emp['lastName']}",
                emp['jobTitle'],
                reports_to
            ))
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    # ============================================================
    # SEARCH
    # ============================================================
    
    def load_search(self):
        self.clear_content()
        self.header_label.configure(text="🔍 Global Search")
        
        search_frame = ctk.CTkFrame(self.content_area)
        search_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        self.global_search_entry = ctk.CTkEntry(search_frame, width=400)
        self.global_search_entry.pack(side="left", padx=5)
        self.global_search_entry.bind('<Return>', lambda e: self.global_search())
        
        ctk.CTkButton(search_frame, text="🔍 Search All", command=self.global_search).pack(side="left", padx=5)
        ctk.CTkLabel(search_frame, text="(Products, Customers, Orders)", font=ctk.CTkFont(size=12)).pack(side="left", padx=10)
        
        self.search_results_frame = ctk.CTkFrame(self.content_area)
        self.search_results_frame.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(self.search_results_frame, text="Enter a search term above", font=ctk.CTkFont(size=16)).pack(pady=50)
    
    def global_search(self):
        search_term = self.global_search_entry.get().strip()
        if not search_term:
            return
        
        self.clear_content()
        self.header_label.configure(text=f"🔍 Global Search: {search_term}")
        
        notebook = ttk.Notebook(self.content_area)
        notebook.pack(fill="both", expand=True, pady=10)
        
        # Products
        products_tab = ctk.CTkFrame(notebook)
        notebook.add(products_tab, text="Products")
        results = self.db.search_products(search_term)
        if results:
            tree = ttk.Treeview(products_tab, columns=("Code", "Name", "Category", "Price", "Stock"), show="headings", height=15)
            tree.pack(fill="both", expand=True)
            for col, width in [("Code", 100), ("Name", 250), ("Category", 120), ("Price", 80), ("Stock", 60)]:
                tree.heading(col, text=col)
                tree.column(col, width=width)
            for p in results:
                tree.insert("", "end", values=(p['productCode'], p['productName'], p['productLine'], f"${p['buyPrice']:.2f}", p['quantityInStock']))
        else:
            ctk.CTkLabel(products_tab, text="No products found").pack(pady=20)
        
        # Customers
        customers_tab = ctk.CTkFrame(notebook)
        notebook.add(customers_tab, text="Customers")
        results = self.db.search_customers_db(search_term)
        if results:
            tree = ttk.Treeview(customers_tab, columns=("ID", "Name", "Contact", "City", "Country"), show="headings", height=15)
            tree.pack(fill="both", expand=True)
            for col, width in [("ID", 60), ("Name", 200), ("Contact", 150), ("City", 120), ("Country", 120)]:
                tree.heading(col, text=col)
                tree.column(col, width=width)
            for c in results:
                tree.insert("", "end", values=(c['customerNumber'], c['customerName'], f"{c['contactFirstName']} {c['contactLastName']}", c['city'], c['country']))
        else:
            ctk.CTkLabel(customers_tab, text="No customers found").pack(pady=20)
        
        # Orders
        orders_tab = ctk.CTkFrame(notebook)
        notebook.add(orders_tab, text="Orders")
        query = """
            SELECT o.orderNumber, o.orderDate, o.status, c.customerName
            FROM orders o JOIN customers c ON o.customerNumber = c.customerNumber
            WHERE o.orderNumber LIKE %s OR c.customerName LIKE %s
            ORDER BY o.orderDate DESC LIMIT 30
        """
        search_pattern = f"%{search_term}%"
        results = self.db.execute_query(query, (search_pattern, search_pattern))
        if results:
            tree = ttk.Treeview(orders_tab, columns=("Order #", "Date", "Customer", "Status"), show="headings", height=15)
            tree.pack(fill="both", expand=True)
            for col, width in [("Order #", 80), ("Date", 120), ("Customer", 250), ("Status", 100)]:
                tree.heading(col, text=col)
                tree.column(col, width=width)
            for o in results:
                tree.insert("", "end", values=(o['orderNumber'], o['orderDate'], o['customerName'], o['status']))
        else:
            ctk.CTkLabel(orders_tab, text="No orders found").pack(pady=20)
    
    # ============================================================
    # PREDEFINED Q&A
    # ============================================================
    
    def load_qa(self):
        self.clear_content()
        self.header_label.configure(text="❓ Predefined Q&A - Database Insights")
        
        controls_frame = ctk.CTkFrame(self.content_area)
        controls_frame.pack(fill="x", pady=10)
        
        left_frame = ctk.CTkFrame(controls_frame)
        left_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(left_frame, text="Select a Question:").pack(side="left", padx=5)
        
        questions = [
            ("🏆 Top Customers by Spending", "top_customers"),
            ("📦 Best Selling Products", "best_selling_products"),
            ("🌍 Sales by Country", "sales_by_country"),
            ("👔 Employee Performance", "employee_performance"),
            ("📈 Monthly Sales Trend", "monthly_sales"),
            ("📊 Product Categories Summary", "product_categories_summary"),
            ("📋 Order Status Summary", "order_status_summary")
        ]
        
        self.qa_var = ctk.StringVar(value=questions[0][0])
        q_menu = ctk.CTkOptionMenu(
            left_frame,
            values=[q[0] for q in questions],
            variable=self.qa_var,
            width=300
        )
        q_menu.pack(side="left", padx=5)
        
        ctk.CTkButton(left_frame, text="▶ Run Query", command=lambda: self.run_qa_query(self.qa_var.get()), height=35).pack(side="left", padx=5)
        
        right_frame = ctk.CTkFrame(controls_frame)
        right_frame.pack(side="right")
        
        self.qa_info_label = ctk.CTkLabel(right_frame, text="Ready", font=ctk.CTkFont(size=12))
        self.qa_info_label.pack(side="right", padx=10)
        
        self.qa_results_frame = ctk.CTkFrame(self.content_area)
        self.qa_results_frame.pack(fill="both", expand=True, pady=10)
        
        self.qa_question_map = {q[0]: q[1] for q in questions}
        self.run_qa_query(questions[0][0])
    
    def run_qa_query(self, question_text):
        question_key = self.qa_question_map.get(question_text, "top_customers")
        
        for widget in self.qa_results_frame.winfo_children():
            widget.destroy()
        
        results = self.db.get_qa_answers(question_key)
        
        if not results:
            ctk.CTkLabel(self.qa_results_frame, text="No results found", font=ctk.CTkFont(size=14)).pack(pady=20)
            self.qa_info_label.configure(text="No results found")
            return
        
        columns = list(results[0].keys())
        
        tree_frame = ctk.CTkFrame(self.qa_results_frame)
        tree_frame.pack(fill="both", expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        for col in columns:
            display_name = ' '.join(col.split('_')).title()
            tree.heading(col, text=display_name)
            width = min(200, max(80, len(display_name) * 12))
            tree.column(col, width=width)
        
        for row in results:
            values = []
            for col in columns:
                val = row[col]
                if isinstance(val, float):
                    val = f"${val:,.2f}"
                elif isinstance(val, int) and 'count' not in col.lower() and 'number' not in col.lower():
                    val = f"{val:,}"
                elif val is None:
                    val = "N/A"
                values.append(val)
            tree.insert("", "end", values=values)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.qa_info_label.configure(text=f"✅ {len(results)} rows found")
    
    # ============================================================
    # AI Q&A SECTION - WITH TABBED RESULTS
    # ============================================================
    
    def load_ai_qa(self):
        self.clear_content()
        self.header_label.configure(text="🤖 AI Ask Question - Powered by OpenRouter")
        
        # Info frame - compact
        info_frame = ctk.CTkFrame(self.content_area)
        info_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(info_frame, text="🤖 Ask any question in natural language and AI will generate the SQL query!", 
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=2)
        
        if not self.ai.initialized:
            ctk.CTkLabel(info_frame, text=f"⚠️ AI error: {self.ai.last_error}", 
                         font=ctk.CTkFont(size=13), text_color="red").pack(anchor="w", pady=2)
        else:
            ctk.CTkLabel(info_frame, text=f"✅ Using model: {self.ai.model}", 
                         font=ctk.CTkFont(size=12), text_color="lightgreen").pack(anchor="w", pady=2)
        
        ctk.CTkLabel(info_frame, text="Examples: 'Show me top 10 customers', 'Best selling products', 'Sales by country'", 
                     font=ctk.CTkFont(size=12)).pack(anchor="w", pady=2)
        
        # Question input - compact
        input_frame = ctk.CTkFrame(self.content_area)
        input_frame.pack(fill="x", pady=8)
        
        ctk.CTkLabel(input_frame, text="Your Question:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=5)
        self.ai_question_entry = ctk.CTkEntry(input_frame, width=500, height=38, font=ctk.CTkFont(size=14))
        self.ai_question_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.ai_question_entry.bind('<Return>', lambda e: self.ask_ai_question())
        
        ctk.CTkButton(input_frame, text="🤖 Ask AI", command=self.ask_ai_question, height=38, 
                      font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=3)
        ctk.CTkButton(input_frame, text="❓ Help", command=self.show_ai_help, height=38).pack(side="left", padx=3)
        ctk.CTkButton(input_frame, text="🗑️ Clear", command=self.clear_ai_qa, height=38).pack(side="left", padx=3)
        
        # Results area - with tabbed view
        self.ai_results_frame = ctk.CTkFrame(self.content_area)
        self.ai_results_frame.pack(fill="both", expand=True, pady=5)
        
        self.show_ai_welcome()
    
    def show_ai_welcome(self):
        for widget in self.ai_results_frame.winfo_children():
            widget.destroy()
        
        welcome_frame = ctk.CTkFrame(self.ai_results_frame)
        welcome_frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(welcome_frame, text="🤖 Ask AI Anything About the Database!", 
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(40, 15))
        ctk.CTkLabel(welcome_frame, text="AI will understand your question and generate the SQL query automatically.", 
                     font=ctk.CTkFont(size=15)).pack(pady=5)
        ctk.CTkLabel(welcome_frame, text="Try asking:", font=ctk.CTkFont(size=15)).pack(pady=15)
        
        examples = [
            "📌 'Show me top 10 customers by spending'",
            "📌 'Which products are the best sellers?'",
            "📌 'What is the sales performance by country?'",
            "📌 'Who are the top performing employees?'",
            "📌 'Show me monthly sales trends'"
        ]
        
        for example in examples:
            ctk.CTkLabel(welcome_frame, text=example, font=ctk.CTkFont(size=13), text_color="lightblue").pack(pady=2)
        
        if self.ai.initialized:
            ctk.CTkLabel(welcome_frame, text=f"\n✅ AI is ready! Using model: {self.ai.model}", 
                         font=ctk.CTkFont(size=14, weight="bold"), text_color="lightgreen").pack(pady=15)
        else:
            ctk.CTkLabel(welcome_frame, text=f"\n❌ AI error: {self.ai.last_error}", 
                         font=ctk.CTkFont(size=14, weight="bold"), text_color="red").pack(pady=15)
    
    def clear_ai_qa(self):
        self.ai_question_entry.delete(0, "end")
        self.show_ai_welcome()
    
    def show_ai_help(self):
        help_text = """
        🤖 AI HELP (OpenRouter)

        You can ask any question about the database in natural language.
        The AI will understand and generate the appropriate SQL query.

        EXAMPLES:

        📊 CUSTOMERS
        • "Show me top 10 customers by spending"
        • "Customers from France"
        • "List all customers"

        📦 PRODUCTS
        • "Best selling products"
        • "Products in the Classic Cars category"
        • "Products priced over $100"

        📝 ORDERS
        • "Recent orders"
        • "Orders by status"
        • "Monthly sales trend"

        👔 EMPLOYEES
        • "Employee performance"
        • "Top sales representatives"

        🌍 GENERAL
        • "Sales by country"
        • "Total revenue"
        • "Most popular product categories"

        💡 TIPS:
        • Be specific for better results
        • Use "show me" or "list" for display queries
        """
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("AI Help")
        dialog.geometry("500x500")
        dialog.grab_set()
        
        text_widget = scrolledtext.ScrolledText(
            dialog,
            wrap="word",
            font=("Consolas", 12),
            bg="#2b2b2b",
            fg="#d4d4d4",
            height=25
        )
        text_widget.pack(fill="both", expand=True, padx=20, pady=20)
        text_widget.insert("1.0", help_text)
        text_widget.config(state="disabled")
        
        ctk.CTkButton(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def ask_ai_question(self):
        question = self.ai_question_entry.get().strip()
        if not question:
            messagebox.showinfo("Info", "Please enter a question")
            return
        
        if not self.ai.initialized:
            messagebox.showerror(
                "AI Not Available",
                f"AI is not initialized.\n\nError: {self.ai.last_error}\n\n"
                "Please check your internet connection."
            )
            return
        
        for widget in self.ai_results_frame.winfo_children():
            widget.destroy()
        
        status_label = ctk.CTkLabel(self.ai_results_frame, text=f"🤔 Processing: '{question}'", font=ctk.CTkFont(size=14))
        status_label.pack(pady=8)
        
        loading_label = ctk.CTkLabel(self.ai_results_frame, text=f"⏳ AI is generating SQL query...", font=ctk.CTkFont(size=14))
        loading_label.pack(pady=5)
        
        def process_question():
            try:
                sql_query, message = self.ai.generate_sql(question, self.db)
                
                if sql_query is None:
                    self.ai_results_frame.after(0, lambda: self.show_ai_error(message))
                    return
                
                results = self.db.execute_query(sql_query)
                
                if results is None:
                    self.ai_results_frame.after(0, lambda: self.show_ai_error("Query execution failed. Please try rephrasing."))
                    return
                
                if not results:
                    self.ai_results_frame.after(0, lambda: self.show_ai_no_results())
                    return
                
                insight = self.ai.generate_insight(question, results, sql_query)
                self.ai_results_frame.after(0, lambda: self.show_ai_results(question, sql_query, results, insight))
                
            except Exception as e:
                self.ai_results_frame.after(0, lambda: self.show_ai_error(f"Error: {str(e)}"))
        
        thread = threading.Thread(target=process_question)
        thread.daemon = True
        thread.start()
    
    def show_ai_error(self, message):
        for widget in self.ai_results_frame.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(self.ai_results_frame, text="❌ Error", font=ctk.CTkFont(size=18, weight="bold"), text_color="red").pack(pady=15)
        
        error_text = scrolledtext.ScrolledText(
            self.ai_results_frame,
            height=3,
            font=("Consolas", 12),
            bg="#2b2b2b",
            fg="#ff6b6b"
        )
        error_text.pack(fill="x", padx=15, pady=8)
        error_text.insert("1.0", message)
        error_text.config(state="disabled")
        
        ctk.CTkButton(self.ai_results_frame, text="🔄 Try Again", command=self.load_ai_qa).pack(pady=15)
    
    def show_ai_no_results(self):
        for widget in self.ai_results_frame.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(self.ai_results_frame, text="ℹ️ No Results Found", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        ctk.CTkLabel(self.ai_results_frame, text="Your question was understood, but no data matched the query.", 
                     font=ctk.CTkFont(size=14)).pack(pady=8)
        ctk.CTkButton(self.ai_results_frame, text="💬 Ask Another Question", command=self.load_ai_qa).pack(pady=15)
    
    def show_ai_results(self, question, sql_query, results, insight):
        for widget in self.ai_results_frame.winfo_children():
            widget.destroy()
        
        # Create a notebook/tab view for better organization
        notebook = ttk.Notebook(self.ai_results_frame)
        notebook.pack(fill="both", expand=True, padx=2, pady=2)
        
        # ============================================================
        # TAB 1: INSIGHT AND SQL
        # ============================================================
        insight_tab = ctk.CTkFrame(notebook)
        notebook.add(insight_tab, text="📊 Insight & SQL")
        
        # Question
        question_label = ctk.CTkLabel(
            insight_tab, 
            text=f"🤖 Question: {question}", 
            font=ctk.CTkFont(size=15, weight="bold"), 
            text_color="lightgreen",
            wraplength=1000
        )
        question_label.pack(anchor="w", pady=5, padx=10, fill="x")
        
        # Insight
        if insight:
            ctk.CTkLabel(insight_tab, text="💡 Insight:", font=ctk.CTkFont(size=14, weight="bold"), 
                         text_color="lightblue").pack(anchor="w", padx=10, pady=(10, 2))
            
            insight_text = scrolledtext.ScrolledText(
                insight_tab,
                height=5,
                font=("Consolas", 13),
                bg="#1e3a5f",
                fg="#ffffff",
                wrap="word"
            )
            insight_text.pack(fill="x", padx=10, pady=5)
            insight_text.insert("1.0", insight)
            insight_text.config(state="disabled")
        
        # SQL Query
        ctk.CTkLabel(insight_tab, text="🔍 Generated SQL:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 2))
        
        sql_text = scrolledtext.ScrolledText(
            insight_tab,
            height=4,
            font=("Consolas", 12),
            bg="#1e1e1e",
            fg="#d4d4d4",
            wrap="word"
        )
        sql_text.pack(fill="x", padx=10, pady=5)
        sql_text.insert("1.0", sql_query)
        sql_text.config(state="disabled")
        
        # Row count
        ctk.CTkLabel(
            insight_tab, 
            text=f"📊 {len(results)} rows found", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="lightgreen"
        ).pack(anchor="w", padx=10, pady=5)
        
        # Copy button
        ctk.CTkButton(
            insight_tab, 
            text="📋 Copy SQL", 
            command=lambda: self.copy_to_clipboard(sql_query),
            height=32
        ).pack(anchor="w", padx=10, pady=5)
        
        # ============================================================
        # TAB 2: RESULTS TABLE - FULL VIEW
        # ============================================================
        results_tab = ctk.CTkFrame(notebook)
        notebook.add(results_tab, text="📋 Results Table")
        
        # Results table with scrollbars - FULL VIEW
        tree_container = ctk.CTkFrame(results_tab)
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Get columns
        columns = list(results[0].keys())
        
        # Create treeview
        tree_frame = ctk.CTkFrame(tree_container)
        tree_frame.pack(fill="both", expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=h_scrollbar.set)
        
        # Configure columns with better widths
        for col in columns:
            display_name = ' '.join(col.split('_')).title()
            tree.heading(col, text=display_name)
            max_len = len(display_name) * 12
            for row in results[:10]:
                val = str(row[col]) if row[col] is not None else "N/A"
                max_len = max(max_len, len(str(val)) * 8)
            tree.column(col, width=min(max_len + 20, 300))
        
        # Insert data
        for row in results:
            values = []
            for col in columns:
                val = row[col]
                if isinstance(val, float):
                    val = f"${val:,.2f}"
                elif isinstance(val, int) and 'count' not in col.lower() and 'number' not in col.lower():
                    val = f"{val:,}"
                elif val is None:
                    val = "N/A"
                values.append(str(val))
            tree.insert("", "end", values=values)
        
        # Pack
        tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Row count in results tab
        ctk.CTkLabel(
            results_tab, 
            text=f"📊 Total: {len(results)} rows", 
            font=ctk.CTkFont(size=13),
            text_color="lightgreen"
        ).pack(anchor="w", padx=10, pady=5)
        
        # ============================================================
        # BOTTOM BUTTONS
        # ============================================================
        button_frame = ctk.CTkFrame(self.ai_results_frame)
        button_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(button_frame, text="💬 Ask Another Question", command=self.load_ai_qa, 
                      height=35, font=ctk.CTkFont(size=13)).pack(side="left", padx=5)
    
    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Success", "SQL query copied to clipboard!")


# ============================================================
# RUN THE APPLICATION
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting ClassicModels Application with OpenRouter AI")
    print("=" * 60)
    print("\n📌 Make sure XAMPP/WAMP is running")
    print("📌 Database 'classicmodels' should exist in phpMyAdmin")
    print(f"📌 Using AI model: {AI_MODEL}")
    print("📌 API Key: ✅ Set")
    print("\n" + "=" * 60)
    
    app = ClassicModelsApp()
    app.mainloop()