from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from mysql.connector import Error
import random

app = Flask(__name__)
app.secret_key = '41f4cfa3623d79af0b306d17f321d482'  # Replace with a secure key


# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'InventoryManagementDB',
    'user': 'root',
    'password': 'Darshan@2003'
}

# --- Helper Function ---
def get_db_connection():
    """Establish a database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Database Error: {e}")
        return None

# --- Routes ---
# 1. Login Route
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection = get_db_connection()
        if connection:
            if username == 'admin' and password == 'admin123':
                        session['role'] = 'admin'
                        return redirect(url_for('admin'))

            try:
                cursor = connection.cursor(dictionary=True)

                # Check if the user exists and validate the password
                cursor.execute("SELECT username, password FROM users WHERE username = %s AND password = %s", (username, password))
                user = cursor.fetchone()

                if user:
                    # Admin Login
                    
                    # User Login
                    session['username'] = username
                    session['role'] = 'user'
                    return redirect(url_for('users'))
                else:
                    # Invalid username or password
                    return render_template('login.html', error="Invalid username or password")

            except Exception as e:
                print(f"Error: {e}")
                return render_template('login.html', error="An error occurred. Please try again.")
            finally:
                cursor.close()
                connection.close()

        return render_template('login.html', error="Database connection error")

    return render_template('login.html')


# Registration Route with OTP Verification
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        mobile = request.form['mobile']

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    return render_template('register.html', error="Username already exists")
                
                cursor.execute("INSERT INTO users (username, password, email, mobile) VALUES (%s, %s, %s, %s)",
                               (username, password, email, mobile))
                connection.commit()
                return redirect(url_for('login'))
            finally:
                cursor.close()
                connection.close()
        else:
            return render_template('register.html', error="Database connection failed.")

    return render_template('register.html')

# 2. Admin Route - Admin Dashboard (Add, Remove, and Restock items)
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    connection = get_db_connection()
    items = []
    orders = []

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            if request.method == 'POST':
                action = request.form.get('action')

                if action == 'add':
                    # Add new item
                    name = request.form['name']
                    price = float(request.form['price'])
                    quantity = int(request.form['quantity'])
                    category = request.form['category']  # Get the category
                    image_url = request.form['image_url']
                    cursor.execute(
                        "INSERT INTO items (name, price, quantity, category, image_url) VALUES (%s, %s, %s, %s, %s)",
                        (name, price, quantity, category, image_url)
                    )
                    connection.commit()

                elif action == 'delete':
                    # Delete item
                    item_id = int(request.form['item_id'])
                    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
                    connection.commit()

                elif action == 'restock':
                    # Restock an item
                    item_id = int(request.form['item_id'])
                    restock_quantity = int(request.form['quantity'])
                    cursor.execute(
                        "UPDATE items SET quantity = quantity + %s WHERE id = %s",
                        (restock_quantity, item_id)
                    )
                    connection.commit()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            cursor.close()
            connection.close()

    return render_template('admin.html', items=items, orders=orders)

  # Renders the admin panel

# Separate Route for Listing Items
@app.route('/admin/items', methods=['GET'])
def admin_list_items():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    connection = get_db_connection()
    items = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, name, price, quantity, image_url FROM items")
            items = cursor.fetchall()
        finally:
            cursor.close()
            connection.close()

    return render_template('list_items.html', items=items)  # Pass the items list to template
@app.route('/admin/orders')
def admin_orders():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    connection = get_db_connection()
    orders = []
    total_value = 0  # Initialize total value

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Fetch orders grouped by order_date and user_id, including item details
            query = """
                SELECT o.user_id, o.order_date, SUM(o.total_price) AS total_price,
                       GROUP_CONCAT(CONCAT(i.name, ' (ID:', o.item_id, ', Qty:', o.quantity, ')') SEPARATOR ', ') AS ordered_items
                FROM orders o
                JOIN items i ON o.item_id = i.id
                GROUP BY o.user_id, o.order_date
                ORDER BY o.order_date DESC
            """
            cursor.execute(query)
            orders = cursor.fetchall()

            # Calculate the total value of all orders
            total_value_query = "SELECT SUM(total_price) AS total_value FROM orders"
            cursor.execute(total_value_query)
            total_value_result = cursor.fetchone()
            if total_value_result and total_value_result['total_value']:
                total_value = total_value_result['total_value']

        except Exception as e:
            print(f"Error fetching orders: {e}")
        finally:
            cursor.close()
            connection.close()

    return render_template('admin_oders.html', orders=orders, total_value=total_value)
@app.route('/admin/suggestions', methods=['GET', 'POST'])
def admin_suggestions():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    connection = get_db_connection()
    most_ordered = []
    least_ordered = []
    not_ordered = []

    if request.method == 'POST':
        # Handle restock form submission
        item_id = request.form.get('item_id')
        quantity = request.form.get('quantity')

        if item_id and quantity:
            try:
                cursor = connection.cursor()
                # Update the item stock
                cursor.execute(
                    "UPDATE items SET quantity = quantity + %s WHERE id = %s",
                    (quantity, item_id)
                )
                connection.commit()
            except Exception as e:
                print(f"Error restocking item: {e}")

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Fetch most ordered and least ordered items
            query = """
                SELECT i.id AS item_id, i.name, i.category, i.quantity AS current_stock,
                       IFNULL(SUM(o.quantity), 0) AS total_ordered
                FROM items i
                LEFT JOIN orders o ON i.id = o.item_id
                GROUP BY i.id
                ORDER BY total_ordered DESC
            """
            cursor.execute(query)
            all_items = cursor.fetchall()

            # Separate most ordered and least ordered
            most_ordered = all_items[:5]  # Top 5 most ordered items
            least_ordered = all_items[-5:]  # Bottom 5 least ordered items

            # Fetch items that are not ordered
            not_ordered_query = """
                SELECT id AS item_id, name, category, quantity AS current_stock
                FROM items
                WHERE id NOT IN (SELECT DISTINCT item_id FROM orders WHERE item_id IS NOT NULL)
            """
            cursor.execute(not_ordered_query)
            not_ordered = cursor.fetchall()

            # Debugging print
            print("Not Ordered Items:", not_ordered)

        except Exception as e:
            print(f"Error fetching suggestions: {e}")
        finally:
            cursor.close()
            connection.close()

    return render_template(
        'admin_suggestions.html',
        most_ordered=most_ordered,
        least_ordered=least_ordered,
        not_ordered=not_ordered
    )

# 3. User Route - Display Products
@app.route('/users')
def users():
    if 'role' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    items = []  # Product items
    orders = []  # User orders
    user_data = {"username": "Guest", "email": "-", "mobile": "-"}  # Default user data

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Fetch user details using username stored in session
            username = session.get('username')  # Assuming 'username' is stored in session
            if username:
                cursor.execute("SELECT username, email, mobile FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user:
                    user_data = {
                        "username": user['username'],
                        "email": user['email'],
                        "mobile": user['mobile']
                    }

                # Fetch user's orders
                cursor.execute("""
                   SELECT o.order_date, 
           SUM(o.total_price) AS total_price, 
           GROUP_CONCAT(CONCAT(i.name, ' (', o.quantity, ')') SEPARATOR ', ') AS ordered_items
    FROM orders o
    JOIN items i ON o.item_id = i.id
    WHERE o.user_id = %s
    GROUP BY o.order_date
    ORDER BY o.order_date DESC
""", (username,))
                orders = cursor.fetchall()

            # Fetch product items
            cursor.execute("SELECT id, name, category, price, quantity, image_url FROM items")
            items = cursor.fetchall()

        except Exception as e:
            print(f"Error: {e}")
        finally:
            cursor.close()
            connection.close()

    return render_template('user.html', items=items, orders=orders, user=user_data)



# 4. Add to Cart API
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if session.get('role') != 'user':
        return jsonify({'message': 'Unauthorized'}), 401
    
    data = request.json
    item_id = int(data['id'])
    action = data['action']  # "increase" or "decrease"
    username = session['username']

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Fetch item details
            cursor.execute("SELECT quantity, price, name FROM items WHERE id = %s", (item_id,))
            item = cursor.fetchone()

            if not item:
                return jsonify({'message': 'Item not found'}), 404

            # Check if item already exists in the user's cart
            cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND item_id = %s", (username, item_id))
            cart_item = cursor.fetchone()

            if action == 'increase':
                if cart_item:
                    new_quantity = cart_item['quantity'] + 1
                    cursor.execute("UPDATE cart SET quantity = %s WHERE user_id = %s AND item_id = %s",
                                   (new_quantity, username, item_id))
                else:
                    cursor.execute("INSERT INTO cart (user_id, item_id, quantity) VALUES (%s, %s, %s)",
                                   (username, item_id, 1))

            elif action == 'decrease' and cart_item:
                new_quantity = cart_item['quantity'] - 1
                if new_quantity > 0:
                    cursor.execute("UPDATE cart SET quantity = %s WHERE user_id = %s AND item_id = %s",
                                   (new_quantity, username, item_id))
                else:
                    cursor.execute("DELETE FROM cart WHERE user_id = %s AND item_id = %s", (username, item_id))

            connection.commit()
           # return jsonify({'message': 'Cart updated successfully'})
        finally:
            cursor.close()
            connection.close()

    return jsonify({'message': 'Database error'}), 500

from datetime import datetime

@app.route('/checkout', methods=['POST'])
def checkout():
    print("Processing Checkout...")
    print("Session data:", session)

    username = session.get('username')  # Fetch username from session

    if not username:
        print("User is not logged in.")
        return redirect(url_for('login'))

    connection = get_db_connection()

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Fetch all cart items for the user, including image URLs
            cursor.execute(""" 
                SELECT c.item_id, c.quantity, i.name, i.price, i.image_url 
                FROM cart c 
                JOIN items i ON c.item_id = i.id
                WHERE c.user_id = %s
            """, (username,))
            cart_items = cursor.fetchall()

            if not cart_items:
                print("Cart is empty.")
                return jsonify({'message': 'Cart is empty, cannot checkout'}), 400

            print("Cart Items: ", cart_items)

            # Process each cart item
            for item in cart_items:
                item_id = item['item_id']
                quantity = item['quantity']
                price = item['price']

                print(f"Processing item {item_id} with quantity {quantity}.")

                # Update stock
                cursor.execute(
                    "UPDATE items SET quantity = quantity - %s WHERE id = %s AND quantity >= %s",
                    (quantity, item_id, quantity)
                )
                if cursor.rowcount == 0:
                    print(f"Insufficient stock for item {item_id}.")
                    connection.rollback()
                    return jsonify({'message': f"Insufficient stock for item {item_id}"}), 400

                # Add to orders table using `username` for user_id
                order_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("""
                    INSERT INTO orders (user_id, item_id, quantity, price, order_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (username, item_id, quantity, price, order_date))

            # Clear the cart
            cursor.execute("DELETE FROM cart WHERE user_id = %s", (username,))
            connection.commit()

            # Calculate total price for the success page
            total_price = sum(item['quantity'] * item['price'] for item in cart_items)

            print("Checkout completed successfully.")
            return render_template('success.html', cart=cart_items, total=total_price, username=username)

        except Exception as e:
            print(f"Error during checkout: {e}")
            connection.rollback()
            return jsonify({'message': 'Error during checkout'}), 500

        finally:
            cursor.close()
            connection.close()

    print("Database connection error.")
    return jsonify({'message': 'Database error during checkout'}), 500

# 5. Cart Route

@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if 'role' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    username = session['username']
    cart_items = []
    total = 0
    stock_error = False  # Flag to track insufficient stock

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            # Handle quantity update if this is a POST request
            if request.method == 'POST':
                data = request.form
                item_id = data.get('item_id')
                action = data.get('action')

                # Validate inputs
                if not action or not item_id:
                    print("Error: Missing action or item ID.")  # Log the error
                    return redirect(url_for('cart'))  # Redirect back to the cart

                try:
                    item_id = int(item_id)
                except ValueError:
                    print("Error: Invalid item ID.")  # Log the error
                    return redirect(url_for('cart'))

                if action not in ['increase', 'decrease']:
                    print("Error: Invalid action.")  # Log the error
                    return redirect(url_for('cart'))

                # Fetch item details
                cursor.execute("SELECT quantity AS stock, price FROM items WHERE id = %s", (item_id,))
                item = cursor.fetchone()

                if not item:
                    print("Error: Item not found.")  # Log the error
                    return redirect(url_for('cart'))

                # Fetch cart details for the user
                cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND item_id = %s", (username, item_id))
                cart_item = cursor.fetchone()

                if action == 'increase':
                    if cart_item:
                        if cart_item['quantity'] < item['stock']:
                            new_quantity = cart_item['quantity'] + 1
                            cursor.execute("UPDATE cart SET quantity = %s WHERE user_id = %s AND item_id = %s",
                                           (new_quantity, username, item_id))
                        else:
                            print("Error: Not enough stock available.")  # Log the error
                    else:
                        cursor.execute("INSERT INTO cart (user_id, item_id, quantity) VALUES (%s, %s, %s)",
                                       (username, item_id, 1))

                elif action == 'decrease' and cart_item:
                    new_quantity = cart_item['quantity'] - 1
                    if new_quantity > 0:
                        cursor.execute("UPDATE cart SET quantity = %s WHERE user_id = %s AND item_id = %s",
                                       (new_quantity, username, item_id))
                    else:
                        cursor.execute("DELETE FROM cart WHERE user_id = %s AND item_id = %s", (username, item_id))

                connection.commit()

            # Fetch updated cart details
            cursor.execute("""
                SELECT c.item_id, i.name, i.quantity AS stock, i.image_url, i.price, c.quantity AS cart_quantity 
                FROM cart c
                JOIN items i ON c.item_id = i.id
                WHERE c.user_id = %s
            """, (username,))
            cart_items = cursor.fetchall()

            # Check stock availability and calculate the total price
            for item in cart_items:
                if item['cart_quantity'] > item['stock']:
                    item['stock_error'] = True
                    stock_error = True
                else:
                    item['stock_error'] = False
                total += item['price'] * item['cart_quantity']

        finally:
            cursor.close()
            connection.close()

    return render_template('kart.html', cart=cart_items, total=total, stock_error=stock_error)


# 6. Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Run Application ---
if __name__ == '__main__':
    app.run(debug=True)
