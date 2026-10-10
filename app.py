from flask import Flask, request, redirect, session, render_template_string
import sqlite3
import os
from secrets import token_hex
import urllib.parse
from datetime import datetime
from werkzeug.utils import secure_filename
app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY") or token_hex(32)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bajrangi.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "12345")
WHATSAPP_NUMBER = "919415272732"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            address TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'New',
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            subtotal REAL NOT NULL
        )
    """)

    # Purane database ke liye compatibility
    columns = conn.execute("PRAGMA table_info(orders)").fetchall()
    column_names = [row["name"] for row in columns]

    if "items" not in column_names:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN items TEXT DEFAULT ''"
        )

    conn.commit()
    conn.close()


init_db()


# =========================================================
# HELPERS
# =========================================================

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def is_admin():
    return session.get("admin_logged_in") is True


# =========================================================
# STYLE
# =========================================================

STYLE = """
<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f5f6f8;
    color: #222;
}

a {
    text-decoration: none;
}

.navbar {
    background: #111827;
    color: white;
    padding: 15px 5%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
}

.logo {
    font-size: 23px;
    font-weight: bold;
}

.nav-links {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.nav-links a {
    color: white;
    padding: 9px 13px;
    border-radius: 7px;
}

.nav-links a:hover {
    background: #374151;
}

.container {
    width: 92%;
    max-width: 1200px;
    margin: 25px auto;
}

.hero {
    background: linear-gradient(135deg, #111827, #374151);
    color: white;
    padding: 40px;
    border-radius: 18px;
    margin-bottom: 25px;
}

.hero h1 {
    margin-top: 0;
    font-size: 36px;
}

.products {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
}

.card {
    background: white;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 5px 20px rgba(0,0,0,0.08);
    padding-bottom: 18px;
}

.product-image {
    width: 100%;
    height: 230px;
    object-fit: contain;
    background: white;
    padding: 12px;
}

.no-image {
    height: 230px;
    display: flex;
    justify-content: center;
    align-items: center;
    background: #eee;
    color: #777;
}

.card-content {
    padding: 15px;
}

.card h3 {
    margin: 0 0 10px;
}

.price {
    font-size: 22px;
    font-weight: bold;
    margin: 10px 0;
}

.btn {
    display: inline-block;
    border: none;
    background: #111827;
    color: white;
    padding: 10px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 15px;
}

.btn:hover {
    opacity: 0.9;
}

.btn-green {
    background: #16a34a;
}

.btn-red {
    background: #dc2626;
}

.btn-blue {
    background: #2563eb;
}

.form-box {
    background: white;
    max-width: 650px;
    margin: 25px auto;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.08);
}

input,
textarea,
select {
    width: 100%;
    padding: 12px;
    margin: 7px 0 16px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 15px;
}

textarea {
    min-height: 100px;
    resize: vertical;
}

label {
    font-weight: bold;
}

.cart-item {
    background: white;
    padding: 15px;
    border-radius: 12px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    flex-wrap: wrap;
}

.qty {
    display: flex;
    align-items: center;
    gap: 8px;
}

.qty a {
    background: #111827;
    color: white;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    display: flex;
    justify-content: center;
    align-items: center;
}

.total-box {
    background: white;
    padding: 20px;
    border-radius: 12px;
    margin-top: 20px;
    font-size: 22px;
    font-weight: bold;
}

.admin-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 18px;
    margin-bottom: 25px;
}

.admin-box {
    background: white;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.07);
}

table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 12px;
    overflow: hidden;
}

th,
td {
    padding: 12px;
    border-bottom: 1px solid #eee;
    text-align: left;
    vertical-align: top;
}

th {
    background: #111827;
    color: white;
}

.small-img {
    width: 75px;
    height: 75px;
    object-fit: contain;
}

.order-box {
    background: white;
    padding: 20px;
    margin-bottom: 18px;
    border-radius: 14px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.06);
}

.success {
    background: #dcfce7;
    color: #166534;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 15px;
}

.error {
    background: #fee2e2;
    color: #991b1b;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 15px;
}

.footer {
    margin-top: 50px;
    background: #111827;
    color: white;
    text-align: center;
    padding: 25px;
}

@media(max-width: 600px) {

    .hero {
        padding: 25px;
    }

    .hero h1 {
        font-size: 28px;
    }

    .cart-item {
        display: block;
    }

    table {
        font-size: 13px;
    }

    th,
    td {
        padding: 8px;
    }
}

</style>
"""


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    conn = get_db()

    products = conn.execute(
        "SELECT * FROM products ORDER BY id DESC"
    ).fetchall()

    conn.close()

    cart = session.get("cart", {})
    cart_count = sum(cart.values())

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<title>Bajrangi Enterprises</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ style|safe }}
</head>

<body>

<div class="navbar">

<div class="logo">
Bajrangi Enterprises
</div>

<div class="nav-links">
<a href="/">Home</a>
<a href="/cart">Cart ({{ cart_count }})</a>
<a href="/admin">Admin</a>
</div>

</div>

<div class="container">

<div class="hero">

<h1>Bajrangi Enterprises</h1>

<p>Quality Kitchen Products at Best Prices</p>

</div>

<h2>Our Products</h2>

{% if products %}

<div class="products">

{% for product in products %}

<div class="card">

{% if product["image"] %}

<img
class="product-image"
src="{{ url_for('static', filename='uploads/' + product['image']) }}"
>

{% else %}

<div class="no-image">
No Image
</div>

{% endif %}

<div class="card-content">

<h3>{{ product["name"] }}</h3>

<div class="price">
Rs.{{ "%.0f"|format(product["price"]) }}
</div>

<a
class="btn btn-green"
href="/add_to_cart/{{ product['id'] }}"
>
Add to Cart
</a>

</div>

</div>

{% endfor %}

</div>

{% else %}

<div class="form-box">

<h3>No products added yet.</h3>

<p>Admin panel se products add karein.</p>

</div>

{% endif %}

</div>

<div class="footer">
Copyright Bajrangi Enterprises
</div>

</body>
</html>
""",
        products=products,
        cart_count=cart_count,
        style=STYLE
    )


# =========================================================
# CART FUNCTIONS
# =========================================================

@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):

    cart = session.get("cart", {})
    key = str(product_id)

    cart[key] = cart.get(key, 0) + 1

    session["cart"] = cart
    session.modified = True

    return redirect("/cart")


@app.route("/cart/increase/<int:product_id>")
def increase_cart(product_id):

    cart = session.get("cart", {})
    key = str(product_id)

    cart[key] = cart.get(key, 0) + 1

    session["cart"] = cart
    session.modified = True

    return redirect("/cart")


@app.route("/cart/decrease/<int:product_id>")
def decrease_cart(product_id):

    cart = session.get("cart", {})
    key = str(product_id)

    if key in cart:

        cart[key] -= 1

        if cart[key] <= 0:
            del cart[key]

    session["cart"] = cart
    session.modified = True

    return redirect("/cart")


@app.route("/cart/remove/<int:product_id>")
def remove_cart(product_id):

    cart = session.get("cart", {})
    key = str(product_id)

    if key in cart:
        del cart[key]

    session["cart"] = cart
    session.modified = True

    return redirect("/cart")


# =========================================================
# CART PAGE
# =========================================================

@app.route("/cart")
def cart_page():

    cart = session.get("cart", {})

    items = []
    total = 0

    conn = get_db()

    for product_id, quantity in cart.items():

        product = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product:

            subtotal = product["price"] * quantity

            items.append({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "quantity": quantity,
                "subtotal": subtotal
            })

            total += subtotal

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<title>Cart</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ style|safe }}
</head>

<body>

<div class="navbar">

<div class="logo">
Bajrangi Enterprises
</div>

<div class="nav-links">
<a href="/">Home</a>
<a href="/cart">Cart</a>
</div>

</div>

<div class="container">

<h1>Your Cart</h1>

{% if items %}

{% for item in items %}

<div class="cart-item">

<div>

<h3>{{ item["name"] }}</h3>

<p>Rs.{{ "%.0f"|format(item["price"]) }} each</p>

</div>

<div class="qty">

<a href="/cart/decrease/{{ item['id'] }}">
-
</a>

<strong>
{{ item["quantity"] }}
</strong>

<a href="/cart/increase/{{ item['id'] }}">
+
</a>

</div>

<strong>
Rs.{{ "%.0f"|format(item["subtotal"]) }}
</strong>

<a
class="btn btn-red"
href="/cart/remove/{{ item['id'] }}"
>
Remove
</a>

</div>

{% endfor %}

<div class="total-box">
Total: Rs.{{ "%.0f"|format(total) }}
</div>

<br>

<a
class="btn btn-green"
href="/checkout"
>
Proceed to Checkout
</a>

{% else %}

<div class="form-box">

<h2>Your cart is empty.</h2>

<a class="btn" href="/">
Continue Shopping
</a>

</div>

{% endif %}

</div>

</body>
</html>
""",
        items=items,
        total=total,
        style=STYLE
    )


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    cart = session.get("cart", {})

    if not cart:
        return redirect("/cart")

    conn = get_db()

    items = []
    total = 0

    for product_id, quantity in cart.items():

        product = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product:

            subtotal = product["price"] * quantity

            items.append({
                "name": product["name"],
                "price": product["price"],
                "quantity": quantity,
                "subtotal": subtotal
            })

            total += subtotal

    conn.close()

    # -----------------------------------------------------
    # PLACE ORDER
    # -----------------------------------------------------

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        address = request.form.get("address", "").strip()

        if not name or not mobile or not address:

            return """
            <h2>Please fill all details.</h2>
            <a href="/checkout">Back</a>
            """

        if not mobile.isdigit() or len(mobile) != 10:

            return """
            <h2>Mobile number must be 10 digits.</h2>
            <a href="/checkout">Back</a>
            """

        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # Purane database ke items column ke liye
        items_text = ""

        for item in items:

            items_text += (
                item["name"]
                + " x "
                + str(item["quantity"])
                + " = Rs."
                + str(int(item["subtotal"]))
                + "\n"
            )

        conn = get_db()

        cursor = conn.execute(
            """
            INSERT INTO orders
            (
                customer_name,
                mobile,
                address,
                total,
                status,
                created_at,
                items
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                mobile,
                address,
                total,
                "New",
                now,
                items_text
            )
        )

        order_id = cursor.lastrowid

        for item in items:

            conn.execute(
                """
                INSERT INTO order_items
                (
                    order_id,
                    product_name,
                    price,
                    quantity,
                    subtotal
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["name"],
                    item["price"],
                    item["quantity"],
                    item["subtotal"]
                )
            )

        conn.commit()
        conn.close()

        # =================================================
        # WHATSAPP MESSAGE - ASCII ONLY
        # =================================================

        message = (
            "NEW ORDER - BAJRANGI ENTERPRISES\n"
            "\n"
            "Order ID: #" + str(order_id) + "\n"
            "Customer: " + name + "\n"
            "Mobile: " + mobile + "\n"
            "Address: " + address + "\n"
            "\n"
            "PRODUCTS\n"
        )

        for item in items:

            message += (
                "- "
                + item["name"]
                + " x "
                + str(item["quantity"])
                + " = Rs."
                + str(int(item["subtotal"]))
                + "\n"
            )

        message += (
            "\n"
            "TOTAL: Rs."
            + str(int(total))
            + "\n"
            "\n"
            "Thank you for your order!"
        )

        whatsapp_url = (
            "https://wa.me/"
            + WHATSAPP_NUMBER
            + "?text="
            + urllib.parse.quote(message)
        )

        session["cart"] = {}
        session.modified = True

        return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<title>Order Placed</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ style|safe }}
</head>

<body>

<div class="navbar">

<div class="logo">
Bajrangi Enterprises
</div>

</div>

<div class="container">

<div class="form-box">

<div class="success">

<h2>
Order Successfully Placed!
</h2>

<p>
Order ID:
<strong>
#{{ order_id }}
</strong>
</p>

</div>

<p>
Order details WhatsApp par bhejne ke liye button dabayein.
</p>

<a
class="btn btn-green"
href="{{ whatsapp_url }}"
target="_blank"
>
Send Order on WhatsApp
</a>

<br>
<br>

<a
class="btn"
href="/"
>
Continue Shopping
</a>

</div>

</div>

</body>
</html>
""",
            order_id=order_id,
            whatsapp_url=whatsapp_url,
            style=STYLE
        )

    # =====================================================
    # CHECKOUT FORM
    # =====================================================

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<title>Checkout</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ style|safe }}
</head>

<body>

<div class="navbar">

<div class="logo">
Bajrangi Enterprises
</div>

<div class="nav-links">
<a href="/">Home</a>
<a href="/cart">Cart</a>
</div>

</div>

<div class="container">

<div class="form-box">

<h1>Checkout</h1>

<h3>
Total Amount:
Rs.{{ "%.0f"|format(total) }}
</h3>

<form method="POST">

<label>
Customer Name
</label>

<input
type="text"
name="name"
placeholder="Enter your name"
required
>

<label>
Mobile Number
</label>

<input
type="text"
name="mobile"
placeholder="10 digit mobile number"
maxlength="10"
required
>

<label>
Address
</label>

<textarea
name="address"
placeholder="Enter complete address"
required
></textarea>

<button
class="btn btn-green"
type="submit"
>
Place Order
</button>

</form>

</div>

</div>

</body>
</html>
""",
        total=total,
        style=STYLE
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    error = ""

    if request.method == "POST":

        password = request.form.get("password", "")

        if password == ADMIN_PASSWORD:

            session["admin_logged_in"] = True

            return redirect("/admin")

        error = "Wrong password."

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<title>Admin Login</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ style|safe }}
</head>

<body>

<div class="navbar">

<div class="logo">
Bajrangi Enterprises
</div>

</div>

<div class="container">

<div class="form-box">

<h1>Admin Login</h1>

{% if error %}

<div class="error">
{{ error }}
</div>

{% endif %}

<form method="POST">

<label>
Password
</label>

<input
type="password"
name="password"
placeholder="Admin Password"
required
>

<button
class="btn"
type="submit"
>
Login
</button>

</form>

</div>

</div>

</body>
</html>
""",
        error=error,
        style=STYLE
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    if not is_admin():
        return redirect("/admin/login")

    conn = get_db()

    products = conn.execute(
        "SELECT * FROM products ORDER BY id DESC"
    ).fetchall()

    orders_count = conn.execute(
        "SELECT COUNT(*) AS total FROM orders"
    ).fetchone()["total"]

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<title>Admin</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ style|safe }}
</head>

<body>

<div class="navbar">

<div class="logo">
Bajrangi Enterprises Admin
</div>

<div class="nav-links">

<a href="/">
Website
</a>

<a href="/admin/orders">
Orders ({{ orders_count }})
</a>

<a href="/admin/logout">
Logout
</a>

</div>

</div>

<div class="container">

<div class="admin-grid">

<div class="admin-box">

<h2>
{{ products|length }}
</h2>

<p>
Total Products
</p>

</div>

<div class="admin-box">

<h2>
{{ orders_count }}
</h2>

<p>
Total Orders
</p>

</div>

</div>

<h1>
Products
</h1>

<a
class="btn btn-green"
href="/admin/add"
>
+ Add New Product
</a>

<br>
<br>

<table>

<tr>

<th>
Image
</th>

<th>
Product
</th>

<th>
Price
</th>

<th>
Action
</th>

</tr>

{% for product in products %}

<tr>

<td>

{% if product["image"] %}

<img
class="small-img"
src="{{ url_for('static', filename='uploads/' + product['image']) }}"
>

{% else %}

No Image

{% endif %}

</td>

<td>
{{ product["name"] }}
</td>

<td>
Rs.{{ "%.0f"|format(product["price"]) }}
</td>

<td>

<a
class="btn btn-blue"
href="/admin/edit/{{ product['id'] }}"
>
Edit
</a>

<a
class="btn btn-red"
href="/admin/delete/{{ product['id'] }}"
onclick="return confirm('Delete this product?')"
>
Delete
</a>

</td>

</tr>

{% endfor %}

</table>

</div>

</body>
</html>
""",
        products=products,
        orders_count=orders_count,
        style=STYLE
    )


# =========================================================
# ADD PRODUCT
# =========================================================

@app.route("/admin/add", methods=["GET", "POST"])
def admin_add():

    if not is_admin():
        return redirect("/admin/login")

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()

        if not name or not price:
            return "Product name and price required."

        try:
            price = float(price)
        except:
            return "Invalid price."

        image_filename = None
        image = request.files.get("image")

        if image and image.filename:

            if not allowed_file(image.filename):
                return "Invalid image format."

            filename = secure_filename(image.filename)

            base, ext = os.path.splitext(filename)

            timestamp = datetime.now().strftime(
                "%Y%m%d%H%M%S"
            )

            image_filename = (
                base + "_" + timestamp + ext
            )

            image.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    image_filename
                )
            )

        conn = get_db()

        conn.execute(
            """
            INSERT INTO products
            (name, price, image)
            VALUES (?, ?, ?)
            """,
            (
                name,
                price,
                image_filename
            )
        )

        conn.commit()
        conn.close()

        return redirect("/admin")

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<title>Add Product</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ style|safe }}
</head>

<body>

<div class="navbar">

<div class="logo">
Bajrangi Enterprises
</div>

</div>

<div class="container">

<div class="form-box">

<h1>
Add Product
</h1>

<form
method="POST"
enctype="multipart/form-data"
>

<label>
Product Name
</label>

<input
type="text"
name="name"
placeholder="Example: Hawkins Classic 3 Liter"
required
>

<label>
Price / MRP
</label>

<input
type="number"
name="price"
placeholder="1675"
required
>

<label>
Product Image
</label>

<input
type="file"
name="image"
accept=".png,.jpg,.jpeg,.webp"
>

<button
class="btn btn-green"
type="submit"
>
Add Product
</button>

<a
class="btn"
href="/admin"
>
Back
</a>

</form>

</div>

</div>

</body>
</html>
""",
        style=STYLE
    )


# =========================================================
# EDIT PRODUCT
# =========================================================

@app.route("/admin/edit/<int:product_id>", methods=["GET", "POST"])
def admin_edit(product_id):

    if not is_admin():
        return redirect("/admin/login")

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if not product:

        conn.close()

        return "Product not found."

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()

        try:
            price = float(price)
        except:

            conn.close()

            return "Invalid price."

        image_filename = product["image"]

        image = request.files.get("image")

        if image and image.filename:

            if not allowed_file(image.filename):

                conn.close()

                return "Invalid image format."

            filename = secure_filename(image.filename)

            base, ext = os.path.splitext(filename)

            timestamp = datetime.now().strftime(
                "%Y%m%d%H%M%S"
            )

            image_filename = (
                base + "_" + timestamp + ext
            )

            image.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    image_filename
                )
            )

        conn.execute(
            """
            UPDATE products
            SET name = ?, price = ?, image = ?
            WHERE id = ?
            """,
            (
                name,
                price,
                image_filename,
                product_id
            )
        )

        conn.commit()
        conn.close()

        return redirect("/admin")

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<title>Edit Product</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ style|safe }}
</head>

<body>

<div class="navbar">

<div class="logo">
Bajrangi Enterprises
</div>

</div>

<div class="container">

<div class="form-box">

<h1>
Edit Product
</h1>

<form
method="POST"
enctype="multipart/form-data"
>

<label>
Product Name
</label>

<input
type="text"
name="name"
value="{{ product['name'] }}"
required
>

<label>
Price / MRP
</label>

<input
type="number"
name="price"
value="{{ product['price'] }}"
required
>

{% if product["image"] %}

<p>
Current Image:
</p>

<img
class="small-img"
src="{{ url_for('static', filename='uploads/' + product['image']) }}"
>

<br>
<br>

{% endif %}

<label>
Change Image
</label>

<input
type="file"
name="image"
accept=".png,.jpg,.jpeg,.webp"
>

<button
class="btn btn-green"
type="submit"
>
Save Changes
</button>

<a
class="btn"
href="/admin"
>
Back
</a>

</form>

</div>

</div>

</body>
</html>
""",
        product=product,
        style=STYLE
    )


# =========================================================
# DELETE PRODUCT
# =========================================================

@app.route("/admin/delete/<int:product_id>")
def admin_delete(product_id):

    if not is_admin():
        return redirect("/admin/login")

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product:

        if product["image"]:

            path = os.path.join(
                UPLOAD_FOLDER,
                product["image"]
            )

            if os.path.exists(path):

                try:
                    os.remove(path)
                except:
                    pass

        conn.execute(
            "DELETE FROM products WHERE id = ?",
            (product_id,)
        )

        conn.commit()

    conn.close()

    return redirect("/admin")


# =========================================================
# ORDERS
# =========================================================

@app.route("/admin/orders")
def admin_orders():

    if not is_admin():
        return redirect("/admin/login")

    conn = get_db()

    orders = conn.execute(
        "SELECT * FROM orders ORDER BY id DESC"
    ).fetchall()

    order_data = []

    for order in orders:

        items = conn.execute(
            """
            SELECT *
            FROM order_items
            WHERE order_id = ?
            """,
            (order["id"],)
        ).fetchall()

        order_data.append({
            "order": order,
            "items": items
        })

    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html>

<head>
<title>Orders</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ style|safe }}
</head>

<body>

<div class="navbar">

<div class="logo">
Bajrangi Enterprises Admin
</div>

<div class="nav-links">

<a href="/admin">
Products
</a>

<a href="/">
Website
</a>

<a href="/admin/logout">
Logout
</a>

</div>

</div>

<div class="container">

<h1>
Customer Orders
</h1>

{% if order_data %}

{% for data in order_data %}

<div class="order-box">

<h2>
Order #{{ data["order"]["id"] }}
</h2>

<p>
<strong>Date:</strong>
{{ data["order"]["created_at"] }}
</p>

<p>
<strong>Customer:</strong>
{{ data["order"]["customer_name"] }}
</p>

<p>
<strong>Mobile:</strong>
{{ data["order"]["mobile"] }}
</p>

<p>
<strong>Address:</strong>
<br>
{{ data["order"]["address"] }}
</p>

<h3>
Products
</h3>

<ul>

{% for item in data["items"] %}

<li>

{{ item["product_name"] }}

x {{ item["quantity"] }}

=

Rs.{{ "%.0f"|format(item["subtotal"]) }}

</li>

{% endfor %}

</ul>

<h2>
Total:
Rs.{{ "%.0f"|format(data["order"]["total"]) }}
</h2>

<p>

<strong>
Status:
</strong>

{{ data["order"]["status"] }}

</p>

<form
method="POST"
action="/admin/order-status/{{ data['order']['id'] }}"
>

<label>
Change Status
</label>

<select name="status">

<option
value="New"
{% if data["order"]["status"] == "New" %}
selected
{% endif %}
>
New
</option>

<option
value="Confirmed"
{% if data["order"]["status"] == "Confirmed" %}
selected
{% endif %}
>
Confirmed
</option>

<option
value="Delivered"
{% if data["order"]["status"] == "Delivered" %}
selected
{% endif %}
>
Delivered
</option>

<option
value="Cancelled"
{% if data["order"]["status"] == "Cancelled" %}
selected
{% endif %}
>
Cancelled
</option>

</select>

<button
class="btn btn-blue"
type="submit"
>
Update Status
</button>

</form>

<br>

<a
class="btn btn-red"
href="/admin/order-delete/{{ data['order']['id'] }}"
onclick="return confirm('Delete this order?')"
>
Delete Order
</a>

</div>

{% endfor %}

{% else %}

<div class="form-box">

<h2>
No orders yet.
</h2>

</div>

{% endif %}

</div>

</body>
</html>
""",
        order_data=order_data,
        style=STYLE
    )


# =========================================================
# UPDATE ORDER STATUS
# =========================================================

@app.route(
    "/admin/order-status/<int:order_id>",
    methods=["POST"]
)
def update_order_status(order_id):

    if not is_admin():
        return redirect("/admin/login")

    status = request.form.get("status", "New")

    allowed = {
        "New",
        "Confirmed",
        "Delivered",
        "Cancelled"
    }

    if status not in allowed:
        status = "New"

    conn = get_db()

    conn.execute(
        """
        UPDATE orders
        SET status = ?
        WHERE id = ?
        """,
        (
            status,
            order_id
        )
    )

    conn.commit()
    conn.close()

    return redirect("/admin/orders")


# =========================================================
# DELETE ORDER
# =========================================================

@app.route("/admin/order-delete/<int:order_id>")
def delete_order(order_id):

    if not is_admin():
        return redirect("/admin/login")

    conn = get_db()

    conn.execute(
        """
        DELETE FROM order_items
        WHERE order_id = ?
        """,
        (order_id,)
    )

    conn.execute(
        """
        DELETE FROM orders
        WHERE id = ?
        """,
        (order_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin/orders")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect("/admin/login")


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    print("")
    print("==========================================")
    print("     BAJRANGI ENTERPRISES WEBSITE")
    print("==========================================")
    print("")
    print("Website : http://127.0.0.1:5000/")
    print("Admin   : http://127.0.0.1:5000/admin")
    print("Password: 12345")
    print("WhatsApp: 9415272732")
    print("")
    print("Server is running...")
    print("")

    app.run(debug=True)