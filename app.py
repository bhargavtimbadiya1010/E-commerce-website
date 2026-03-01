import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import os
from werkzeug.utils import secure_filename



def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("ecommerce.db")

def setup_db():
    conn = get_db()
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # Products table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        image TEXT
    )
    """)

    # Cart table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """)

    # Sample products
    cur.execute("INSERT OR IGNORE INTO products (id, name, price, image) VALUES (1, 'Laptop', 50000, 'laptop.jpg')")
    cur.execute("INSERT OR IGNORE INTO products (id, name, price, image) VALUES (2, 'Smartphone', 20000, 'smartphone.jpg')")
    cur.execute("INSERT OR IGNORE INTO products (id, name, price, image) VALUES (3, 'Headphones', 1500, 'headphones.jpg')")
    cur.execute("INSERT OR IGNORE INTO products (id, name, price, image) VALUES (4, 'Smartwatch', 3000, 'smartwatch.jpg')")

    conn.commit()
    conn.close()


# ---------------- FLASK APP ----------------
app = Flask(__name__)
app.secret_key = "secret123"  # session management

# Call DB setup once
setup_db()


# configure upload folder
UPLOAD_FOLDER = "static/images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect(url_for("products"))
        else:
            flash("Invalid credentials")
    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for("login"))
        except:
            flash("Username already exists")
        conn.close()
    return render_template("register.html")


# ---------------- PRODUCTS ----------------
@app.route("/products")
def products():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    items = cur.fetchall()
    conn.close()
    return render_template("products.html", items=items)


# ---------------- ADD TO CART ----------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO cart (user_id, product_id) VALUES (?, ?)", (session["user_id"], product_id))
    conn.commit()
    conn.close()
    flash("Product added to cart!")
    return redirect(url_for("products"))


# ---------------- VIEW CART ----------------
@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT products.name, products.price, products.image
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=?
    """, (session["user_id"],))
    items = cur.fetchall()
    conn.close()

    total = sum([item[1] for item in items])
    return render_template("cart.html", items=items, total=total)


# ---------------- CHECKOUT ----------------
@app.route("/checkout")
def checkout():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM cart WHERE user_id=?", (session["user_id"],))
    conn.commit()
    conn.close()
    flash("🎉 Order placed successfully!")
    return redirect(url_for("products"))

# ---------------- ADMIN: ADD PRODUCT ----------------
@app.route("/admin/add_product", methods=["GET", "POST"])
def add_product():
    # ✅ Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # ✅ Check only admin can add
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id=?", (session["user_id"],))
    username = cur.fetchone()[0]
    conn.close()

    if username != "admin":
        flash("🚫 Only admin can add products!")
        return redirect(url_for("products"))

    # ✅ Handle Form Submit
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        file = request.files["image"]

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)   # save uploaded file into static/images

            # save into database
            conn = get_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO products (name, price, image) VALUES (?, ?, ?)",
                        (name, price, filename))
            conn.commit()
            conn.close()

            flash("✅ Product added successfully!")
            return redirect(url_for("products"))
        else:
            flash("❌ Invalid file format. Allowed: jpg, jpeg, png, gif")

    return render_template("admin_add.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
