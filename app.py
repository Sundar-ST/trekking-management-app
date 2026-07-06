from copy import error
from flask import Flask, render_template, request, redirect, url_for, session
from models import get_db_connection, init_db
import sqlite3
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-later'

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        role=request.form['role']
        email=request.form['email']
        password=request.form['password']

        conn=get_db_connection()

        if role=='admin':
            account=conn.execute(
                'select * from admin where username=?',
                (email,)
            ).fetchone()
        elif role=='staff':
            account=conn.execute(
                'select * from staff where email=?',
                (email,)
            ).fetchone()
        elif role=='user':
            account=conn.execute(
                'select * from user where email =?',
                (email,)
            ).fetchone()

        conn.close()

        if account is None or not check_password_hash(account['password'], password) :
            return render_template('login.html', error='Invalid credentials')

        if role=='staff' and account['status']=='Pending':
            return render_template('login.html',error='Your account is not yet approved by admin')

        if role=='staff' and account['status']=='Blacklisted':
            return render_template('login.html',error='Your account has been blacklisted')

        if role == 'user' and account['status'] == 'Blacklisted':
            return render_template('login.html', error='Your account has been blacklisted')

        session['role']=role
        session['id']=account[f'{role}_id']
        session['name']=account['username'] if role =='admin' else account['name']

        return redirect(url_for(f'{role}_dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role')!='admin':
        return redirect(url_for('login'))
    #return f"Welcome Admin {session['name']}! (dashboard coming next)"
    
    search = request.args.get('search', '')

    conn=get_db_connection()

    #stats for top of dashboard
    trek_count=conn.execute('select count(*) from trek').fetchone()[0]
    user_count=conn.execute('select count(*) from user').fetchone()[0]
    staff_count=conn.execute('select count(*) from staff').fetchone()[0]
    booking_count=conn.execute('select count(*) from booking').fetchone()[0]
    
    if search:
        all_staff = conn.execute(
            "SELECT * FROM staff WHERE name LIKE ? OR email LIKE ? ",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        all_staff=conn.execute('select * from staff').fetchall()

    conn.close()

    return render_template('admin_dashboard.html',
        trek_count=trek_count,
        user_count=user_count,
        staff_count=staff_count,
        booking_count=booking_count,
        all_staff=all_staff,
        search=search
    )


@app.route('/admin/staff/<int:staff_id>/approve',methods=['POST'])
def approve_staff(staff_id):
    if session.get('role')!='admin':
        return redirect(url_for('login'))

    conn=get_db_connection()
    conn.execute("update staff set status='Approved' where staff_id=?",(staff_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/staff/<int:staff_id>/blacklist',methods=["POST"])
def blacklist_staff(staff_id):
    if session.get('role')!='admin':
        return redirect(url_for('login'))

    conn=get_db_connection()
    conn.execute("update staff set status='Blacklisted' where staff_id=?",(staff_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))
    

@app.route('/admin/treks')
def manage_treks():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    search = request.args.get('search', '')

    conn = get_db_connection()

    base_query = '''
        SELECT trek.*, staff.name AS staff_name
        FROM trek
        LEFT JOIN staff ON trek.assigned_staff_id = staff.staff_id
    '''

    if search:
        treks = conn.execute(
            base_query + ' WHERE trek.name LIKE ? OR trek.location LIKE ?',
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        treks = conn.execute(base_query).fetchall()

    conn.close()

    return render_template('manage_treks.html', treks=treks, search=search)


@app.route('/admin/treks/add', methods=['GET','POST'])
def add_trek():
    if session.get('role')!='admin':
        return redirect(url_for('login'))

    if request.method=='POST':
        name=request.form['name']
        location=request.form['location']
        difficulty=request.form['difficulty']
        duration_days=request.form['duration_days']
        available_slots=request.form['available_slots']
        start_date=request.form['start_date']
        end_date=request.form['end_date']

        conn=get_db_connection()
        conn.execute('''
            insert into trek (name,location,difficulty,duration_days,available_slots,status,start_date,end_date)
            values (?,?,?,?,?,?,?,?)''',
            (name,location,difficulty,duration_days,available_slots,'Pending',start_date,end_date))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_treks'))

    return render_template('add_trek.html')


@app.route('/admin/treks/<int:trek_id>/assign', methods=['GET', 'POST'])
def assign_staff(trek_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        staff_id = request.form['staff_id']
        status = request.form['status']

        conn.execute(
            'UPDATE trek SET assigned_staff_id = ?, status = ? WHERE trek_id = ?',
            (staff_id, status, trek_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('manage_treks'))

    trek = conn.execute('SELECT * FROM trek WHERE trek_id = ?', (trek_id,)).fetchone()
    approved_staff = conn.execute(
        "SELECT * FROM staff WHERE status = 'Approved'"
    ).fetchall()
    conn.close()

    return render_template('assign_staff.html', trek=trek, approved_staff=approved_staff)


@app.route('/admin/users')
def manage_users():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    search = request.args.get('search', '')

    conn = get_db_connection()

    if search:
        all_users = conn.execute(
            "SELECT * FROM user WHERE name LIKE ? OR email LIKE ?",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        all_users = conn.execute('SELECT * FROM user').fetchall()

    conn.close()

    return render_template('manage_users.html', all_users=all_users, search=search)


@app.route('/admin/users/<int:user_id>/blacklist', methods=['POST'])
def blacklist_user(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("UPDATE user SET status = 'Blacklisted' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('manage_users'))


@app.route('/admin/users/<int:user_id>/activate', methods=['POST'])
def activate_user(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("UPDATE user SET status = 'Active' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('manage_users'))


@app.route('/staff/dashboard')
def staff_dashboard():
    if session.get('role') != 'staff':
        return redirect(url_for('login'))

    conn = get_db_connection()

    staff_id = session['id']

    assigned_treks = conn.execute(
        'SELECT * FROM trek WHERE assigned_staff_id = ?',
        (staff_id,)
    ).fetchall()

    # For each trek, also count how many users have booked it
    treks_with_counts = []
    for trek in assigned_treks:
        booking_count = conn.execute(
            "SELECT COUNT(*) FROM booking WHERE trek_id = ? AND status = 'Booked'",
            (trek['trek_id'],)
        ).fetchone()[0]
        treks_with_counts.append({
            'trek': trek,
            'booking_count': booking_count
        })

    conn.close()

    return render_template('staff_dashboard.html', treks_with_counts=treks_with_counts)


@app.route('/staff/treks/<int:trek_id>/manage', methods=['GET', 'POST'])
def manage_trek(trek_id):
    if session.get('role') != 'staff':
        return redirect(url_for('login'))

    conn = get_db_connection()

    trek = conn.execute(
        'SELECT * FROM trek WHERE trek_id = ? AND assigned_staff_id = ?',
        (trek_id, session['id'])
    ).fetchone()

    if trek is None:
        conn.close()
        return redirect(url_for('staff_dashboard'))

    if request.method == 'POST':
        available_slots = request.form['available_slots']
        status = request.form['status']

        conn.execute(
            'UPDATE trek SET available_slots = ?, status = ? WHERE trek_id = ?',
            (available_slots, status, trek_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('staff_dashboard'))

    participants = conn.execute(
        '''SELECT user.name, user.email, booking.status, booking.booking_date
           FROM booking
           JOIN user ON booking.user_id = user.user_id
           WHERE booking.trek_id = ?''',
        (trek_id,)
    ).fetchall()

    conn.close()

    return render_template('manage_trek.html', trek=trek, participants=participants)

@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    difficulty = request.args.get('difficulty', '')

    conn = get_db_connection()

    query = "SELECT * FROM trek WHERE status = 'Open' AND available_slots > 0"
    params = []

    if search:
        query += " AND (name LIKE ? OR location LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)

    open_treks = conn.execute(query, params).fetchall()

    my_bookings = conn.execute(
        "SELECT trek_id FROM booking WHERE user_id = ? AND status = 'Booked'",
        (session['id'],)
    ).fetchall()
    booked_trek_ids = [b['trek_id'] for b in my_bookings]

    conn.close()

    return render_template(
        'user_dashboard.html',
        open_treks=open_treks,
        booked_trek_ids=booked_trek_ids,
        search=search,
        difficulty=difficulty
    )


@app.route('/user/book/<int:trek_id>', methods=['POST'])
def book_trek(trek_id):
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    conn = get_db_connection()

    trek = conn.execute(
        "SELECT * FROM trek WHERE trek_id = ? AND status = 'Open'",
        (trek_id,)
    ).fetchone()

    if trek is None or trek['available_slots'] <= 0:
        conn.close()
        return redirect(url_for('user_dashboard'))

    # Prevent the same user from booking the same trek twice
    existing = conn.execute(
        "SELECT * FROM booking WHERE user_id = ? AND trek_id = ? AND status = 'Booked'",
        (session['id'], trek_id)
    ).fetchone()

    if existing is not None:
        conn.close()
        return redirect(url_for('user_dashboard'))

    conn.execute(
        'INSERT INTO booking (user_id, trek_id, booking_date, status) VALUES (?, ?, ?, ?)',
        (session['id'], trek_id, date.today().isoformat(), 'Booked')
    )
    conn.execute(
        'UPDATE trek SET available_slots = available_slots - 1 WHERE trek_id = ?',
        (trek_id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('user_dashboard'))


@app.route('/user/bookings')
def my_bookings():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    conn = get_db_connection()
    bookings = conn.execute(
        '''SELECT booking.booking_id, booking.booking_date, booking.status,
                  trek.name AS trek_name, trek.location, trek.start_date, trek.end_date
           FROM booking
           JOIN trek ON booking.trek_id = trek.trek_id
           WHERE booking.user_id = ?
           ORDER BY booking.booking_date DESC''',
        (session['id'],)
    ).fetchall()
    conn.close()

    return render_template('my_bookings.html', bookings=bookings)


@app.route('/user/bookings/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Make sure this booking actually belongs to this user
    booking = conn.execute(
        "SELECT * FROM booking WHERE booking_id = ? AND user_id = ? AND status = 'Booked'",
        (booking_id, session['id'])
    ).fetchone()

    if booking is not None:
        conn.execute(
            "UPDATE booking SET status = 'Cancelled' WHERE booking_id = ?",
            (booking_id,)
        )
        conn.execute(
            'UPDATE trek SET available_slots = available_slots + 1 WHERE trek_id = ?',
            (booking['trek_id'],)
        )
        conn.commit()

    conn.close()
    return redirect(url_for('my_bookings'))



def get_current_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM user WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return user

@app.route('/user/profile', methods=['GET', 'POST'])
def edit_profile():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        password = request.form['password']

        if password:
            conn.execute(
                'UPDATE user SET name = ?, contact = ?, password = ? WHERE user_id = ?',
                (name, contact, generate_password_hash(password), session['id'])
            )
        else:
            conn.execute(
                'UPDATE user SET name = ?, contact = ? WHERE user_id = ?',
                (name, contact, session['id'])
            )
        conn.commit()

        session['name'] = name  # keep navbar/session in sync with the new name

        conn.close()
        return render_template('edit_profile.html', user=get_current_user(session['id']), message='Profile updated successfully')

    user = conn.execute('SELECT * FROM user WHERE user_id = ?', (session['id'],)).fetchone()
    conn.close()

    return render_template('edit_profile.html', user=user)




@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        role=request.form['role']
        name=request.form['name']
        email=request.form['email']
        password = generate_password_hash(request.form['password'])
        contact=request.form['contact']

        conn=get_db_connection()

        try:
            if role=='staff':
                conn.execute(
                    'insert into staff(name,email,password,contact,status) values(?,?,?,?,?)',
                    (name,email,password,contact,'Pending')
                )
            elif role=='user':
                conn.execute(
                    'insert into user(name,email,password,contact,status) values(?,?,?,?,?)',
                    (name,email,password,contact,'Active')
                )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html',error='Email already exists')

        conn.close()

        if role=='staff':
            return render_template('login.html', error='Staff registration pending for approval')
        elif role == 'user':
            return render_template('login.html', error='User registration successful')
        return render_template('login.html')
    
    return render_template('register.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)