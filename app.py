from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from functools import wraps
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Secure configuration
app.secret_key = os.getenv("SECRET_KEY")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    return conn
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
       password=os.getenv("DB_PASSWORD")
        database="hostel_management"
    )
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid username or password"
    return render_template('login.html', error=error)

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM rooms")
    total_rooms = cursor.fetchone()['total']

    cursor.execute("SELECT SUM(capacity) AS cap, SUM(occupied) AS occ FROM rooms")
    room_data = cursor.fetchone()
    total_capacity = room_data['cap'] or 0
    total_occupied = room_data['occ'] or 0
    available_slots = total_capacity - total_occupied

    cursor.execute("SELECT COUNT(*) AS total FROM fees WHERE status='Paid'")
    paid_fees = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM fees WHERE status='Unpaid'")
    unpaid_fees = cursor.fetchone()['total']

    cursor.execute("SELECT SUM(amount) AS total FROM fees WHERE status='Paid'")
    total_collected = cursor.fetchone()['total'] or 0

    cursor.close()
    conn.close()

    return render_template('dashboard.html',
        total_students=total_students,
        total_rooms=total_rooms,
        available_slots=available_slots,
        paid_fees=paid_fees,
        unpaid_fees=unpaid_fees,
        total_collected=total_collected
    )

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add_student', methods=['POST'])
def add_student():
    full_name = request.form['full_name']
    father_name = request.form['father_name']
    cnic = request.form['cnic']
    phone = request.form['phone']
    address = request.form['address']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO students (full_name, father_name, cnic, phone, address) VALUES (%s, %s, %s, %s, %s)",
        (full_name, father_name, cnic, phone, address)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return "Student added successfully! <a href='/'>Go back</a>"

@app.route('/add_room', methods=['GET', 'POST'])
@login_required
def add_room():
    if request.method == 'POST':
        room_number = request.form['room_number']
        capacity = request.form['capacity']
        room_type = request.form['room_type']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rooms (room_number, capacity, room_type) VALUES (%s, %s, %s)",
            (room_number, capacity, room_type)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_rooms'))

    return render_template('add_room.html')

@app.route('/rooms')
@login_required
def view_rooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM rooms ORDER BY room_id ASC")
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('rooms.html', rooms=rooms)

@app.route('/allot_room', methods=['GET', 'POST'])
@login_required
def allot_room():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form['student_id']
        room_id = request.form['room_id']

        cursor.execute("UPDATE students SET room_id = %s WHERE student_id = %s", (room_id, student_id))
        cursor.execute("UPDATE rooms SET occupied = occupied + 1 WHERE room_id = %s", (room_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_rooms'))

    cursor.execute("SELECT * FROM students WHERE room_id IS NULL")
    students = cursor.fetchall()

    cursor.execute("SELECT * FROM rooms WHERE occupied < capacity")
    rooms = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('allot_room.html', students=students, rooms=rooms)

@app.route('/add_fee', methods=['GET', 'POST'])
@login_required
def add_fee():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form['student_id']
        amount = request.form['amount']
        month = request.form['month']

        cursor.execute(
            "INSERT INTO fees (student_id, amount, month, status) VALUES (%s, %s, %s, 'Unpaid')",
            (student_id, amount, month)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_fees'))

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('add_fee.html', students=students)

@app.route('/fees')
@login_required
def view_fees():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT fees.fee_id, fees.amount, fees.month, fees.status, fees.paid_date,
               students.full_name
        FROM fees
        JOIN students ON fees.student_id = students.student_id
        ORDER BY fees.fee_id DESC
    """)
    fees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('fees.html', fees=fees)

@app.route('/mark_paid/<int:fee_id>')
@login_required
def mark_paid(fee_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE fees SET status = 'Paid', paid_date = CURDATE() WHERE fee_id = %s",
        (fee_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('view_fees'))

@app.route('/students')
@login_required
def view_students():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students ORDER BY student_id DESC")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('students.html', students=students)

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        full_name = request.form['full_name']
        father_name = request.form['father_name']
        cnic = request.form['cnic']
        phone = request.form['phone']
        address = request.form['address']

        cursor.execute("""
            UPDATE students SET full_name=%s, father_name=%s, cnic=%s, phone=%s, address=%s
            WHERE student_id=%s
        """, (full_name, father_name, cnic, phone, address, student_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_students'))

    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('edit_student.html', student=student)

@app.route('/delete_student/<int:student_id>')
@login_required
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fees WHERE student_id = %s", (student_id,))
    cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('view_students'))

@app.route('/delete_room/<int:room_id>')
@login_required
def delete_room(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET room_id = NULL WHERE room_id = %s", (room_id,))
    cursor.execute("DELETE FROM rooms WHERE room_id = %s", (room_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('view_rooms'))

if __name__ == '__main__':
    app.run(debug=True)
